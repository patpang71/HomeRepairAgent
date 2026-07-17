import logging

from langchain_core.messages import HumanMessage, SystemMessage

from llm import get_llm
from mcp_client import call_mcp_tool
from nodes.orchestrator import ASK_INTENT_RESPONSE
from state import AgentState

logger = logging.getLogger(__name__)

_RESOLVED_PROMPT = """Classify the user's reply to the question "Does this resolve your problem?".
Respond with exactly one word — YES, NO, or UNCLEAR."""

_SUMMARY_PROMPT = """Summarize the following home repair search question and result into a single summary \
of no more than 35 words. Respond with only the summary text, no preamble.

Question: {question}

Result: {result}"""


def check_result_node(state: AgentState) -> AgentState:
    logger.info('check_result_node sessionId=%s', state['session_id'])
    llm = get_llm()

    classification = llm.invoke([
        SystemMessage(content=_RESOLVED_PROMPT),
        HumanMessage(content=state['user_message'] or ''),
    ]).content.strip().upper()
    logger.info('check_result classification sessionId=%s result=%s', state['session_id'], classification)

    history = state['messages'] + [{'role': 'user', 'content': state['user_message']}]
    pending = state.get('pending_search_result') or {}

    if 'YES' in classification:
        return _resolve(state, history, pending, llm, resolved=True)

    if 'NO' in classification:
        return _resolve(state, history, pending, llm, resolved=False)

    response = "Sorry, I didn't catch that — did that resolve your problem? Please answer yes or no."
    history = history + [{'role': 'assistant', 'content': response}]
    return {**state, 'messages': history, 'response': response}


def _resolve(state: AgentState, history: list, pending: dict, llm, resolved: bool) -> AgentState:
    summary = _summarize(llm, pending)
    project_id = pending.get('projectId')
    if project_id:
        call_mcp_tool('update_resolution', {
            'projectId': project_id,
            'resolutionDetail': summary,
            'resolved': resolved,
        })

    if resolved:
        response = f"Glad that helped! {ASK_INTENT_RESPONSE}"
        history = history + [{'role': 'assistant', 'content': response}]
        return {
            **state,
            'messages': history,
            'response': response,
            'current_agent': 'orchestrator',
            'orchestrator_stage': 'awaiting_intent',
            'pending_search_result': None,
        }

    response = "Sorry that didn't do it — let's keep troubleshooting. What else can you tell me about the issue?"
    history = history + [{'role': 'assistant', 'content': response}]
    return {
        **state,
        'messages': history,
        'response': response,
        'current_agent': 'home_repair',
        'pending_search_result': None,
    }


def _summarize(llm, pending: dict) -> str:
    question = pending.get('searchQuestion', '')
    result = pending.get('searchResult', '')
    prompt = _SUMMARY_PROMPT.format(question=question, result=result)
    try:
        return llm.invoke([HumanMessage(content=prompt)]).content.strip()
    except Exception:
        logger.exception('Resolution summary failed')
        return (question or '')[:200]
