import logging

from langchain_core.messages import HumanMessage, SystemMessage

from llm import get_llm
from mcp_client import call_mcp_tool
from state import AgentState

logger = logging.getLogger(__name__)

_INTENT_PROMPT = """Classify the user's reply to the question "Would you like to switch to a different project, \
or do you have a home repair question?".
Respond with exactly one word — PROJECT, QUESTION, or IRRELEVANT:
- PROJECT: user wants to switch/change their project
- QUESTION: user wants to ask about a home repair issue, or is ready to describe their problem
- IRRELEVANT: the reply does not answer the question"""

_ASK_INTENT_RESPONSE = (
    "Would you like to switch to a different project, or do you have a home repair question I can help with?"
)


def orchestrator_node(state: AgentState) -> AgentState:
    logger.info(
        'orchestrator_node sessionId=%s stage=%s',
        state['session_id'], state.get('orchestrator_stage'),
    )
    if state.get('orchestrator_stage') != 'awaiting_intent':
        return _ask_intent(state)
    return _classify_intent(state)


def _ask_intent(state: AgentState) -> AgentState:
    history = state['messages'] + [{'role': 'assistant', 'content': _ASK_INTENT_RESPONSE}]
    return {
        **state,
        'messages': history,
        'response': _ASK_INTENT_RESPONSE,
        'current_agent': 'orchestrator',
        'orchestrator_stage': 'awaiting_intent',
    }


def _classify_intent(state: AgentState) -> AgentState:
    llm = get_llm()
    lc_messages = [
        SystemMessage(content=_INTENT_PROMPT),
        HumanMessage(content=state['user_message'] or ''),
    ]
    classification = llm.invoke(lc_messages).content.strip().upper()
    logger.info('orchestrator classification sessionId=%s result=%s', state['session_id'], classification)

    history = state['messages'] + [{'role': 'user', 'content': state['user_message']}]

    if 'QUESTION' in classification:
        response = "Great! What part of your home needs attention, and what's the issue?"
        history = history + [{'role': 'assistant', 'content': response}]
        return {
            **state,
            'messages': history,
            'response': response,
            'current_agent': 'home_repair',
            'orchestrator_stage': None,
        }

    if 'PROJECT' in classification:
        # Refetch the profile so we're working off current project data, not
        # whatever was cached in state at session start.
        profile = call_mcp_tool('get_user_profile', {'appleId': state['apple_id']})
        if 'message' in profile:
            logger.warning('Profile refresh failed sessionId=%s: %s', state['session_id'], profile['message'])
            profile = state['user_profile']

        all_projects = profile.get('projects', [])
        other_projects = [p for p in all_projects if p.get('isDefaultProject') != 'true']
        logger.info(
            'orchestrator PROJECT answer sessionId=%s otherProjectCount=%d',
            state['session_id'], len(other_projects),
        )

        if not other_projects:
            if all_projects:
                default_project = next(
                    (p for p in all_projects if p.get('isDefaultProject') == 'true'),
                    all_projects[0],
                )
                response = (
                    f"You don't have any other projects — **{default_project['projectName']}** is the only one "
                    f"on file. Would you like to add a new project?"
                )
            else:
                response = "You don't have any projects on file yet. Would you like to add one?"
            history = history + [{'role': 'assistant', 'content': response}]
            return {
                **state,
                'user_profile': profile,
                'messages': history,
                'response': response,
                'current_agent': 'project_update',
                'orchestrator_stage': None,
                'project_update_stage': 'awaiting_new_project_confirmation',
            }

        lines = [
            f"{i + 1}. **{p['projectName']}** ({p.get('jobType', 'MISC')}) — "
            f"{p.get('streetAddress', 'no address')}, {p.get('city', '')}, {p.get('state', '')}"
            for i, p in enumerate(other_projects)
        ]
        project_list = '\n'.join(lines)
        response = (
            f"No problem — here are your other projects:\n\n{project_list}\n\n"
            f"Which one would you like to switch to? Or say **new project** to add a new one."
        )
        history = history + [{'role': 'assistant', 'content': response}]
        return {
            **state,
            'user_profile': profile,
            'messages': history,
            'response': response,
            'current_agent': 'project_update',
            'orchestrator_stage': None,
            'project_update_stage': 'awaiting_selection',
        }

    # IRRELEVANT — ask again
    response = f"Sorry, I didn't quite catch that. {_ASK_INTENT_RESPONSE}"
    history = history + [{'role': 'assistant', 'content': response}]
    return {
        **state,
        'messages': history,
        'response': response,
        'current_agent': 'orchestrator',
        'orchestrator_stage': 'awaiting_intent',
    }
