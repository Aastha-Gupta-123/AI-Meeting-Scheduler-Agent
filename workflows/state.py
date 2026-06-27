from typing import TypedDict, List, Dict, Any, Annotated
import operator

def append_log(left: List[str], right: List[str]) -> List[str]:
    """Helper reducer to append logs in LangGraph state."""
    return left + right

class MeetingSchedulerState(TypedDict):
    """
    State representing the context of a meeting schedule workflow execution.
    """
    user_query: str
    extracted_details: Dict[str, Any]
    is_available: bool
    busy_participants: List[str]
    conflicts: List[Dict[str, Any]]
    alternatives: List[Dict[str, Any]]
    scheduled_meeting_id: int
    reminder_text: str
    final_response: str
    agent_logs: Annotated[List[str], append_log]
