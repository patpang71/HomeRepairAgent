from langgraph.graph import StateGraph, END, START

from nodes.initial_verification import initial_verification_node
from nodes.orchestrator import orchestrator_node
from nodes.home_repair import home_repair_node
from nodes.project_update import project_update_node
from state import AgentState

_compiled = None


def _route(state: AgentState) -> str:
    return state['current_agent']


def get_graph():
    global _compiled
    if _compiled is not None:
        return _compiled

    workflow = StateGraph(AgentState)
    workflow.add_node('initial_verification', initial_verification_node)
    workflow.add_node('orchestrator', orchestrator_node)
    workflow.add_node('home_repair', home_repair_node)
    workflow.add_node('project_update', project_update_node)

    workflow.add_conditional_edges(START, _route, {
        'initial_verification': 'initial_verification',
        'orchestrator': 'orchestrator',
        'home_repair': 'home_repair',
        'project_update': 'project_update',
    })

    workflow.add_edge('initial_verification', END)
    workflow.add_edge('orchestrator', END)
    workflow.add_edge('home_repair', END)
    workflow.add_edge('project_update', END)

    _compiled = workflow.compile()
    return _compiled
