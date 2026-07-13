import logging

from mcp_client import call_mcp_tool
from nodes.orchestrator import ASK_INTENT_RESPONSE
from state import AgentState

logger = logging.getLogger(__name__)


def initial_verification_node(state: AgentState) -> AgentState:
    logger.info('initial_verification_node sessionId=%s', state['session_id'])
    profile = call_mcp_tool('get_user_profile', {'appleId': state['apple_id']})

    if 'message' in profile:
        logger.warning('Profile verification failed sessionId=%s: %s', state['session_id'], profile['message'])
        response = "Welcome to Home Repair Assistant! I couldn't verify your account — please contact support."
        history = state['messages'] + [{'role': 'assistant', 'content': response}]
        # Leave current_agent as 'initial_verification' so the next turn retries.
        return {**state, 'user_profile': None, 'messages': history, 'response': response}

    first_name = profile.get('firstName') or profile.get('userName', 'there')
    default_project = next(
        (p for p in profile.get('projects', []) if p.get('isDefaultProject') == 'true'),
        None,
    )

    if default_project:
        project_line = (
            f"**{default_project['projectName']}** ({default_project.get('jobType', 'General')}) "
            f"at {default_project.get('streetAddress', 'no address on file')}, "
            f"{default_project.get('city', '')}, {default_project.get('state', '')}"
        )
        greeting = (
            f"Hi {first_name}! Welcome back.\n\n"
            f"Your current default project is:\n{project_line}"
        )
    else:
        greeting = (
            f"Hi {first_name}! Welcome to Home Repair Assistant. "
            f"You don't have a default project set yet."
        )

    response = f"{greeting}\n\n{ASK_INTENT_RESPONSE}"
    history = state['messages'] + [{'role': 'assistant', 'content': response}]
    return {
        **state,
        'user_profile': profile,
        'messages': history,
        'response': response,
        'current_agent': 'orchestrator',
        'orchestrator_stage': 'awaiting_intent',
    }
