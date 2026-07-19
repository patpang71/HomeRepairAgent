import base64
import json
import logging
import os

import boto3
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

from llm import get_llm
from mcp_client import call_mcp_tool
from state import AgentState

logger = logging.getLogger(__name__)

_s3 = boto3.client('s3')
UPLOAD_BUCKET = os.environ.get('UPLOAD_BUCKET_NAME', '')

_TAVILY_KEY_PARAM = os.environ.get('TAVILY_API_KEY_PARAM', '/HomeRepairAgent/Tavily/ApiKey')
_tavily_key_loaded = False

_bedrock_agent_runtime = boto3.client('bedrock-agent-runtime')
KNOWLEDGE_BASE_ID = os.environ.get('KNOWLEDGE_BASE_ID', '')
# A knowledge-base chunk counts as "found" when at least one retrieved result
# scores >= KB_RETRIEVAL_MIN_SCORE (0-1 relevance score from Bedrock); below
# that threshold we treat the KB as not having an answer and fall back to
# Tavily web search. KB_RETRIEVAL_MAX_RESULTS caps how many chunks we pull back.
KB_RETRIEVAL_MAX_RESULTS = int(os.environ.get('KB_RETRIEVAL_MAX_RESULTS', '5'))
KB_RETRIEVAL_MIN_SCORE = float(os.environ.get('KB_RETRIEVAL_MIN_SCORE', '0.5'))

_SYSTEM = """You are an expert home repair assistant with deep knowledge of plumbing, electrical,
HVAC, carpentry, roofing, and general home maintenance.

Your goal: help the user diagnose and fix their home repair issue.

First gather (if not already known from the conversation):
1. Which part of the home (e.g. water heater, kitchen, electrical, plumbing, floor, roof, HVAC)
2. The specific problem or question

Once you understand the issue, provide clear diagnostic steps, likely causes, and repair advice.
Keep answers practical and safe — always recommend a licensed professional for electrical or structural work."""

_SEARCH_DECISION = """Given the conversation so far, decide whether you have enough information to search for a solution.
Respond with JSON only (no other text):
{
  "should_search": true or false,
  "search_query": "specific search query if should_search is true, else null",
  "ready_to_answer": true or false
}
Set should_search=true only when you know both the specific part of the home AND the specific problem."""


def home_repair_node(state: AgentState) -> AgentState:
    logger.info('home_repair_node sessionId=%s hasPhoto=%s', state['session_id'], bool(state.get('photo_key')))
    _ensure_tavily_key()
    llm = get_llm()

    lc_messages = [SystemMessage(content=_SYSTEM)]
    history = state['messages']
    # Bedrock Converse requires the first non-system turn to be from the user —
    # drop any leading assistant messages (e.g. the initial greeting).
    while history and history[0]['role'] != 'user':
        history = history[1:]
    for msg in history:
        if msg['role'] == 'user':
            lc_messages.append(HumanMessage(content=msg['content']))
        elif msg['role'] == 'assistant':
            lc_messages.append(AIMessage(content=msg['content']))

    # Current user turn — include photo if present
    current_content = _build_content(state)
    lc_messages.append(HumanMessage(content=current_content))

    # Ask LLM whether to search or keep gathering info
    decision_messages = lc_messages + [HumanMessage(content=_SEARCH_DECISION)]
    decision_raw = llm.invoke(decision_messages).content.strip()

    try:
        decision = json.loads(decision_raw)
    except Exception:
        logger.warning('Search-decision JSON parse failed sessionId=%s raw=%r', state['session_id'], decision_raw)
        decision = {'should_search': False, 'ready_to_answer': False}

    logger.info('home_repair search decision sessionId=%s decision=%s', state['session_id'], decision)

    preference = (state.get('user_profile') or {}).get('preference', 'CONCISE')

    search_query = decision.get('search_query')
    search_context = ''
    search_source = None
    if decision.get('should_search') and search_query:
        search_context = _kb_search(search_query)
        if search_context:
            search_source = 'knowledge_base'
        else:
            search_context = _tavily_search(search_query, preference)
            search_source = 'tavily'
        logger.info(
            'home_repair search sessionId=%s source=%s query=%r',
            state['session_id'], search_source, search_query,
        )

    if search_context:
        lc_messages.append(HumanMessage(
            content=f"Search results for reference:\n{search_context}\n\n"
                    f"Using these results, provide a clear and practical answer to the user's question."
        ))

    response = llm.invoke(lc_messages).content
    logger.info('home_repair_node responding sessionId=%s responseLen=%d', state['session_id'], len(response))

    intro_shown = state.get('home_repair_intro_shown', False)
    if not intro_shown:
        intro = _resolution_intro(state.get('user_profile'))
        if intro:
            response = f"{intro}\n\n{response}"
        intro_shown = True

    current_agent = 'home_repair'
    pending_search_result = None

    if search_context:
        project_id = _default_project_id(state.get('user_profile'))
        if project_id:
            save_result = call_mcp_tool('save_search_result', {
                'projectId': project_id,
                'searchQuestion': search_query,
                'searchResult': search_context,
            })
            pending_search_result = {
                'projectId': project_id,
                'searchResultId': save_result.get('searchResultId'),
                'searchQuestion': search_query,
                'searchResult': search_context,
            }
            response = f"{response}\n\nDoes this resolve your problem?"
            current_agent = 'check_result'

    history = state['messages'] + [
        {'role': 'user', 'content': state['user_message']},
        {'role': 'assistant', 'content': response},
    ]
    return {
        **state,
        'messages': history,
        'response': response,
        'current_agent': current_agent,
        'pending_search_result': pending_search_result,
        'home_repair_intro_shown': intro_shown,
    }


def _default_project_id(profile: dict):
    projects = (profile or {}).get('projects', [])
    default = next((p for p in projects if p.get('isDefaultProject') == 'true'), None)
    if default:
        return default.get('projectId')
    return projects[0]['projectId'] if projects else None


def _resolution_intro(profile: dict):
    projects = (profile or {}).get('projects', [])
    default = next((p for p in projects if p.get('isDefaultProject') == 'true'), None)
    if not default:
        default = projects[0] if projects else None
    if not default:
        return None

    resolution_detail = default.get('resolutionDetail')
    if not resolution_detail:
        return None

    return (
        f"Before we dive in — here's the last resolution on file for "
        f"**{default.get('projectName', 'your project')}**: {resolution_detail}"
    )


def _build_content(state: AgentState):
    text = state.get('user_message') or ''
    photo_key = state.get('photo_key')
    if not photo_key or not UPLOAD_BUCKET:
        return text

    try:
        obj = _s3.get_object(Bucket=UPLOAD_BUCKET, Key=photo_key)
        image_bytes = obj['Body'].read()
        image_b64 = base64.b64encode(image_bytes).decode()
        return [
            {
                'type': 'image',
                'source': {'type': 'base64', 'media_type': 'image/jpeg', 'data': image_b64},
            },
            {'type': 'text', 'text': text},
        ]
    except Exception:
        logger.exception('Failed to load photo from S3 key=%s', photo_key)
        return text


def _kb_search(query: str) -> str:
    if not KNOWLEDGE_BASE_ID:
        return ''

    logger.info('KB retrieve query=%r knowledgeBaseId=%s', query, KNOWLEDGE_BASE_ID)
    try:
        response = _bedrock_agent_runtime.retrieve(
            knowledgeBaseId=KNOWLEDGE_BASE_ID,
            retrievalQuery={'text': query},
            retrievalConfiguration={
                'vectorSearchConfiguration': {'numberOfResults': KB_RETRIEVAL_MAX_RESULTS},
            },
        )
        results = response.get('retrievalResults', [])
        found = [r for r in results if r.get('score', 0) >= KB_RETRIEVAL_MIN_SCORE]
        logger.info(
            'KB retrieve returned %d result(s), %d above min score %.2f',
            len(results), len(found), KB_RETRIEVAL_MIN_SCORE,
        )
        if not found:
            return ''

        return '\n\n'.join(
            r.get('content', {}).get('text', '') for r in found
        )
    except Exception:
        logger.exception('KB retrieve failed query=%r', query)
        return ''


def _tavily_search(query: str, preference: str = 'CONCISE') -> str:
    # CONCISE users get the top 2 results with a basic (short) summary;
    # DETAIL users get more results with advanced depth and full raw content.
    concise = str(preference).upper() != 'DETAIL'
    logger.info('Tavily search query=%r preference=%s', query, preference)
    try:
        from langchain_community.tools.tavily_search import TavilySearchResults
        if concise:
            tool = TavilySearchResults(max_results=2, search_depth='basic')
        else:
            tool = TavilySearchResults(
                max_results=5,
                search_depth='advanced',
                include_raw_content=True,
            )
        results = tool.invoke(query)
        logger.info('Tavily search returned %d result(s)', len(results))

        def _body(r):
            if concise:
                return r.get('content', '')
            return r.get('raw_content') or r.get('content', '')

        return '\n\n'.join(
            f"[{r.get('title', 'Result')}]\n{_body(r)}"
            for r in results
        )
    except Exception as e:
        logger.exception('Tavily search failed query=%r', query)
        return f"(Search unavailable: {e})"


def _ensure_tavily_key():
    global _tavily_key_loaded
    if _tavily_key_loaded or os.environ.get('TAVILY_API_KEY'):
        return
    try:
        ssm = boto3.client('ssm')
        param = ssm.get_parameter(Name=_TAVILY_KEY_PARAM, WithDecryption=True)
        os.environ['TAVILY_API_KEY'] = param['Parameter']['Value']
        _tavily_key_loaded = True
        logger.info('Loaded Tavily API key from SSM param=%s', _TAVILY_KEY_PARAM)
    except Exception:
        logger.exception('Failed to load Tavily API key from SSM param=%s', _TAVILY_KEY_PARAM)
