import base64
import json
import os

import boto3
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

from llm import get_llm
from state import AgentState

_s3 = boto3.client('s3')
UPLOAD_BUCKET = os.environ.get('UPLOAD_BUCKET_NAME', '')

_TAVILY_KEY_PARAM = os.environ.get('TAVILY_API_KEY_PARAM', '/HomeRepairAgent/Tavily/ApiKey')
_tavily_key_loaded = False

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
        decision = {'should_search': False, 'ready_to_answer': False}

    search_context = ''
    if decision.get('should_search') and decision.get('search_query'):
        search_context = _tavily_search(decision['search_query'])

    if search_context:
        lc_messages.append(HumanMessage(
            content=f"Search results for reference:\n{search_context}\n\n"
                    f"Using these results, provide a clear and practical answer to the user's question."
        ))

    response = llm.invoke(lc_messages).content

    history = state['messages'] + [
        {'role': 'user', 'content': state['user_message']},
        {'role': 'assistant', 'content': response},
    ]
    return {**state, 'messages': history, 'response': response, 'current_agent': 'home_repair'}


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
        return text


def _tavily_search(query: str) -> str:
    try:
        from langchain_community.tools.tavily_search import TavilySearchResults
        tool = TavilySearchResults(max_results=3)
        results = tool.invoke(query)
        return '\n\n'.join(
            f"[{r.get('title', 'Result')}]\n{r.get('content', '')}"
            for r in results
        )
    except Exception as e:
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
    except Exception:
        pass
