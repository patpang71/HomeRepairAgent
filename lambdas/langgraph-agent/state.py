from typing import Optional
from typing_extensions import TypedDict


class Message(TypedDict):
    role: str    # 'user' | 'assistant'
    content: str


class AgentState(TypedDict):
    # Identity — set on first invocation and persisted
    apple_id: str
    session_id: str

    # Per-invocation input
    user_message: str
    photo_key: Optional[str]

    # Persisted across turns
    user_profile: Optional[dict]
    current_agent: str           # 'initial_verification' | 'orchestrator' | 'home_repair' | 'project_update' | 'check_result'
    messages: list               # list of Message dicts

    # Orchestrator sub-state
    orchestrator_stage: Optional[str]     # None | 'awaiting_intent'

    # Project update sub-state
    project_update_stage: Optional[str]   # 'show_projects' | 'awaiting_selection' | 'collecting_new_project'
    pending_project: Optional[dict]        # accumulated fields for new project creation

    # Check-result sub-state — the search Q&A awaiting a yes/no from the user
    pending_search_result: Optional[dict]  # {'projectId', 'searchResultId', 'searchQuestion', 'searchResult'}

    # Home-repair sub-state — whether the last-resolution intro paragraph has
    # already been shown for the current issue (reset when a new issue starts)
    home_repair_intro_shown: Optional[bool]

    # Output — set by whichever node runs
    response: str
