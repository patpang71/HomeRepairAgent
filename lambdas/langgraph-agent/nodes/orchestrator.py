from langchain_core.messages import HumanMessage, SystemMessage

from llm import get_llm
from mcp_client import call_mcp_tool
from state import AgentState

_CLASSIFY_PROMPT = """Classify the user's reply to the question "Are you working on [project name] today?".
Respond with exactly one word — YES, NO, or IRRELEVANT:
- YES: user confirms they want to work on the shown project
- NO: user wants a different project or to switch projects
- IRRELEVANT: the reply does not answer the question"""


def orchestrator_node(state: AgentState) -> AgentState:
    if state['user_profile'] is None:
        return _initial_greeting(state)
    return _classify_response(state)


def _initial_greeting(state: AgentState) -> AgentState:
    profile = call_mcp_tool('get_user_profile', {'appleId': state['apple_id']})

    if 'message' in profile:
        response = "Welcome to Home Repair Assistant! I couldn't load your profile — please contact support."
        return {**state, 'user_profile': {}, 'response': response}

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
        response = (
            f"Hi {first_name}! Welcome back.\n\n"
            f"Your current default project is:\n{project_line}\n\n"
            f"Are you working on this project today?"
        )
    else:
        response = (
            f"Hi {first_name}! Welcome to Home Repair Assistant. "
            f"You don't have a default project set yet. Would you like to set one up?"
        )

    history = state['messages'] + [{'role': 'assistant', 'content': response}]
    return {
        **state,
        'user_profile': profile,
        'messages': history,
        'response': response,
        'current_agent': 'orchestrator',
    }


def _classify_response(state: AgentState) -> AgentState:
    llm = get_llm()
    lc_messages = [
        SystemMessage(content=_CLASSIFY_PROMPT),
        HumanMessage(content=state['user_message'] or ''),
    ]
    classification = llm.invoke(lc_messages).content.strip().upper()

    history = state['messages'] + [{'role': 'user', 'content': state['user_message']}]

    if 'YES' in classification:
        response = "Great! What part of your home needs attention, and what's the issue?"
        history = history + [{'role': 'assistant', 'content': response}]
        return {**state, 'messages': history, 'response': response, 'current_agent': 'home_repair'}

    if 'NO' in classification:
        response = "No problem — let me pull up your projects so we can switch to the right one."
        history = history + [{'role': 'assistant', 'content': response}]
        return {
            **state,
            'messages': history,
            'response': response,
            'current_agent': 'project_update',
            'project_update_stage': 'show_projects',
        }

    # IRRELEVANT — ask again
    default_project = next(
        (p for p in state['user_profile'].get('projects', []) if p.get('isDefaultProject') == 'true'),
        None,
    )
    project_name = default_project['projectName'] if default_project else 'your current project'
    response = f"Sorry, I didn't quite catch that. Are you working on **{project_name}** today? Please answer yes or no."
    history = history + [{'role': 'assistant', 'content': response}]
    return {**state, 'messages': history, 'response': response, 'current_agent': 'orchestrator'}
