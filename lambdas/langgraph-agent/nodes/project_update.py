import json

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

from llm import get_llm
from mcp_client import call_mcp_tool
from state import AgentState

_SELECT_PROMPT = """The user was shown a numbered list of their home repair projects and asked to pick one or create a new one.
From their reply, determine:
- Did they pick an existing project by number or name? → action: "select", projectIndex: <0-based index>
- Do they want to create a new project? → action: "new"
- Unclear? → action: "unclear"

Respond with JSON only (no other text):
{"action": "select" | "new" | "unclear", "projectIndex": <integer or null>}"""

_COLLECT_PROMPT = """You are collecting information to create a new home repair project.
Required fields: Project Name, Job Type (e.g. PLUMBING, ELECTRICAL, HVAC, FLOORING, ROOFING, PAINTING, MISC), Zip Code.
Optional fields: Street Address, City, State, Description.

Collected so far: {collected}

If Zip Code is not yet collected, ask for it specifically before finishing.
When you have Project Name, Job Type, AND Zip Code, respond with JSON only:
{{"ready": true, "project": {{"projectName": "...", "jobType": "...", "streetAddress": "...", "city": "...", "state": "...", "zipCode": "...", "description": "..."}}}}

Otherwise ask a natural conversational question to gather missing required fields. Do NOT output JSON when still gathering."""


def project_update_node(state: AgentState) -> AgentState:
    stage = state.get('project_update_stage') or 'show_projects'

    if stage == 'show_projects':
        return _show_projects(state)
    if stage == 'awaiting_selection':
        return _handle_selection(state)
    if stage == 'collecting_new_project':
        return _collect_project_info(state)

    return {**state, 'current_agent': 'orchestrator', 'response': "Let me take you back to the main menu."}


# ── Stage: show projects list ────────────────────────────────────────────────

def _show_projects(state: AgentState) -> AgentState:
    profile = state.get('user_profile') or {}
    projects = profile.get('projects', [])

    if not projects:
        response = "You don't have any projects yet. Let's create your first one! What would you like to name it?"
        history = state['messages'] + [{'role': 'assistant', 'content': response}]
        return {
            **state,
            'messages': history,
            'response': response,
            'project_update_stage': 'collecting_new_project',
            'pending_project': {},
        }

    lines = [
        f"{i + 1}. **{p['projectName']}** ({p.get('jobType', 'MISC')}) — "
        f"{p.get('streetAddress', 'no address')}, {p.get('city', '')}, {p.get('state', '')}"
        for i, p in enumerate(projects)
    ]
    project_list = '\n'.join(lines)
    response = (
        f"Here are your current projects:\n\n{project_list}\n\n"
        f"Which project would you like to set as your default? "
        f"Or say **new project** to add a new one."
    )
    history = state['messages'] + [{'role': 'assistant', 'content': response}]
    return {
        **state,
        'messages': history,
        'response': response,
        'project_update_stage': 'awaiting_selection',
    }


# ── Stage: process the user's pick ──────────────────────────────────────────

def _handle_selection(state: AgentState) -> AgentState:
    llm = get_llm()
    profile = state.get('user_profile') or {}
    projects = profile.get('projects', [])

    lc_messages = [
        SystemMessage(content=_SELECT_PROMPT),
        HumanMessage(content=f"Projects: {json.dumps(projects)}\nUser said: {state['user_message']}"),
    ]
    raw = llm.invoke(lc_messages).content.strip()

    try:
        decision = json.loads(raw)
    except Exception:
        decision = {'action': 'unclear'}

    history = state['messages'] + [{'role': 'user', 'content': state['user_message']}]

    if decision.get('action') == 'select':
        idx = decision.get('projectIndex')
        if idx is not None and 0 <= int(idx) < len(projects):
            chosen = projects[int(idx)]
            result = call_mcp_tool('set_project_as_default', {
                'userId': profile['userId'],
                'projectId': chosen['projectId'],
            })
            if 'successfully' in result.get('message', '').lower():
                response = (
                    f"Done! **{chosen['projectName']}** is now your default project. "
                    f"Now let's get to work — what's the home repair issue?"
                )
                history = history + [{'role': 'assistant', 'content': response}]
                return {
                    **state,
                    'messages': history,
                    'response': response,
                    'current_agent': 'orchestrator',
                    'project_update_stage': None,
                    'user_profile': None,  # force profile refresh on next orchestrator turn
                }
        # Index out of range or parse failed — fall through to unclear

    if decision.get('action') == 'new':
        response = "Let's create a new project! What would you like to name it?"
        history = history + [{'role': 'assistant', 'content': response}]
        return {
            **state,
            'messages': history,
            'response': response,
            'project_update_stage': 'collecting_new_project',
            'pending_project': {},
        }

    response = "I didn't catch that. Please pick a project number from the list, or say **new project** to create one."
    history = history + [{'role': 'assistant', 'content': response}]
    return {**state, 'messages': history, 'response': response}


# ── Stage: collect new project fields ───────────────────────────────────────

def _collect_project_info(state: AgentState) -> AgentState:
    llm = get_llm()
    pending = state.get('pending_project') or {}

    system = _COLLECT_PROMPT.format(collected=json.dumps(pending))
    lc_messages = [SystemMessage(content=system)]

    # Include recent conversation for natural follow-ups
    history = state['messages'][-8:]
    # Bedrock Converse requires the first non-system turn to be from the user —
    # drop any leading assistant messages left over from the slice window.
    while history and history[0]['role'] != 'user':
        history = history[1:]
    for msg in history:
        if msg['role'] == 'user':
            lc_messages.append(HumanMessage(content=msg['content']))
        elif msg['role'] == 'assistant':
            lc_messages.append(AIMessage(content=msg['content']))
    lc_messages.append(HumanMessage(content=state['user_message']))

    raw = llm.invoke(lc_messages).content.strip()
    history = state['messages'] + [{'role': 'user', 'content': state['user_message']}]

    # Check if LLM returned the ready JSON
    try:
        data = json.loads(raw)
        if data.get('ready') and data.get('project'):
            return _save_new_project(state, data['project'], history)
    except Exception:
        pass

    # LLM is still gathering — return its conversational message
    history = history + [{'role': 'assistant', 'content': raw}]
    return {
        **state,
        'messages': history,
        'response': raw,
        'project_update_stage': 'collecting_new_project',
        'pending_project': pending,
    }


def _save_new_project(state: AgentState, project_data: dict, history: list) -> AgentState:
    profile = state.get('user_profile') or {}
    user_id = profile.get('userId')

    add_result = call_mcp_tool('add_project', {
        'userId': user_id,
        'projectName': project_data.get('projectName', 'New Project'),
        'jobType': project_data.get('jobType', 'MISC'),
        'streetAddress': project_data.get('streetAddress'),
        'city': project_data.get('city'),
        'state': project_data.get('state'),
        'zipCode': project_data['zipCode'],
        'description': project_data.get('description'),
        'isDefaultProject': True,
    })

    if 'projectId' in add_result:
        call_mcp_tool('set_project_as_default', {
            'userId': user_id,
            'projectId': add_result['projectId'],
        })

    project_name = project_data.get('projectName', 'your new project')
    response = (
        f"**{project_name}** has been created and set as your default project. "
        f"Now, what's the home repair issue you'd like help with?"
    )
    history = history + [{'role': 'assistant', 'content': response}]
    return {
        **state,
        'messages': history,
        'response': response,
        'current_agent': 'orchestrator',
        'project_update_stage': None,
        'pending_project': None,
        'user_profile': None,  # refresh profile on next orchestrator turn
    }
