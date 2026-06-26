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
    current_agent: str           # 'orchestrator' | 'home_repair' | 'project_update'
    messages: list               # list of Message dicts

    # Project update sub-state
    project_update_stage: Optional[str]   # 'show_projects' | 'awaiting_selection' | 'collecting_new_project'
    pending_project: Optional[dict]        # accumulated fields for new project creation

    # Output — set by whichever node runs
    response: str
