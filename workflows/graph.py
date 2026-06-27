from langgraph.graph import StateGraph, START, END
from workflows.state import MeetingSchedulerState
from agents.crew import crew_manager
from backend.availability_checker import availability_checker
from backend.calendar_manager import calendar_manager
from backend.conflict_resolver import conflict_resolver
from vectorstore.faiss_db import memory_db
from utils.logger import logger
from utils.helpers import normalize_participants

# Define the Nodes
def extract_info(state: MeetingSchedulerState) -> dict:
    """Extracts meeting parameters from raw text using CrewAI Scheduler Agent."""
    logger.info("LangGraph Node: extract_info")
    query = state.get("user_query", "")
    
    extracted = crew_manager.run_extraction_crew(query)
    
    log_msg = (
        f"[Extractor Agent]: Extracted parameters:\n"
        f"  - Title: {extracted.get('title')}\n"
        f"  - Date: {extracted.get('date')}\n"
        f"  - Time: {extracted.get('start_time')}\n"
        f"  - Duration: {extracted.get('duration_mins')} mins\n"
        f"  - Attendees: {extracted.get('participants')}"
    )
    
    return {
        "extracted_details": extracted,
        "agent_logs": [log_msg]
    }

def availability_check(state: MeetingSchedulerState) -> dict:
    """Checks participant availability against SQLite db schedules."""
    logger.info("LangGraph Node: availability_check")
    details = state.get("extracted_details", {})
    
    title = details.get("title", "Meeting")
    date = details.get("date", "")
    start_time = details.get("start_time", "")
    duration = details.get("duration_mins", 60)
    participants = details.get("participants", [])

    res = availability_checker.check_availability(
        date=date,
        start_time=start_time,
        duration_mins=duration,
        participants=participants
    )
    
    log_msg = (
        f"[Availability Agent]: Schedule check completed.\n"
        f"  - Status: {'Available' if res['available'] else 'Busy'}\n"
        f"  - Details: {res['message']}"
    )
    
    return {
        "is_available": res["available"],
        "busy_participants": res["busy_participants"],
        "conflicts": res["conflicting_meetings"],
        "agent_logs": [log_msg]
    }

def decide_routing(state: MeetingSchedulerState) -> str:
    """Routes state graph to alternative suggestions OR scheduling based on conflict check."""
    logger.info("LangGraph Route: decide_routing")
    if state.get("is_available", False):
        return "schedule_meeting"
    else:
        return "suggest_alternatives"

def suggest_alternatives(state: MeetingSchedulerState) -> dict:
    """Finds alternatives and formats response using CrewAI Conflict Agent."""
    logger.info("LangGraph Node: suggest_alternatives")
    details = state.get("extracted_details", {})
    date = details.get("date", "")
    duration = details.get("duration_mins", 60)
    participants = details.get("participants", [])
    busy = state.get("busy_participants", [])
    
    # 1. Compute alternatives
    alts = conflict_resolver.find_alternatives(
        date=date,
        duration_mins=duration,
        participants=participants
    )
    
    # 2. Ask CrewAI conflict agent to generate response
    polite_response = crew_manager.run_conflict_resolution_crew(
        title=details.get("title", "Meeting"),
        date=date,
        start_time=details.get("start_time", ""),
        duration_mins=duration,
        participants=participants,
        busy_list=busy,
        alternatives=alts
    )
    
    log_msg = (
        f"[Conflict Agent]: Formulated conflict resolution response.\n"
        f"  - Alternatives Found: {len(alts)}"
    )
    
    return {
        "alternatives": alts,
        "final_response": polite_response,
        "agent_logs": [log_msg]
    }

def schedule_meeting(state: MeetingSchedulerState) -> dict:
    """Saves the scheduled event inside the SQLite database using Calendar Manager."""
    logger.info("LangGraph Node: schedule_meeting")
    details = state.get("extracted_details", {})
    
    title = details.get("title", "Meeting")
    date = details.get("date", "")
    start_time = details.get("start_time", "")
    duration = details.get("duration_mins", 60)
    description = details.get("description", "")
    participants = details.get("participants", [])

    res = calendar_manager.create_event(
        title=title,
        date=date,
        start_time=start_time,
        duration_mins=duration,
        description=description,
        participants=participants
    )
    
    meeting_id = res.get("meeting_id", -1)
    
    log_msg = (
        f"[Calendar Agent]: Scheduled meeting in SQLite DB.\n"
        f"  - Meeting ID: {meeting_id}\n"
        f"  - Database Status: {res['status'].upper()}"
    )
    
    return {
        "scheduled_meeting_id": meeting_id,
        "agent_logs": [log_msg]
    }

def store_in_vectorstore(state: MeetingSchedulerState) -> dict:
    """Indexes the scheduled meeting summary in FAISS vector database."""
    logger.info("LangGraph Node: store_in_vectorstore")
    details = state.get("extracted_details", {})
    meeting_id = state.get("scheduled_meeting_id", -1)
    
    title = details.get("title", "Meeting")
    date = details.get("date", "")
    start_time = details.get("start_time", "")
    duration = details.get("duration_mins", 60)
    description = details.get("description", "")
    participants = details.get("participants", [])

    memory_db.add_meeting_to_memory(
        meeting_id=meeting_id,
        title=title,
        date=date,
        start_time=start_time,
        duration_mins=duration,
        description=description,
        participants=participants
    )
    
    log_msg = (
        f"[System]: Added scheduled event (ID: {meeting_id}) to FAISS vector memory "
        f"for semantic queries."
    )
    
    return {
        "agent_logs": [log_msg]
    }

def generate_reminder(state: MeetingSchedulerState) -> dict:
    """Generates a text alert using CrewAI Reminder Agent."""
    logger.info("LangGraph Node: generate_reminder")
    details = state.get("extracted_details", {})
    
    title = details.get("title", "Meeting")
    date = details.get("date", "")
    start_time = details.get("start_time", "")
    participants = details.get("participants", [])

    reminder_txt = crew_manager.run_reminder_generation_crew(
        title=title,
        date=date,
        start_time=start_time,
        participants=participants
    )
    
    log_msg = (
        f"[Reminder Agent]: Formulated participant notifications.\n"
        f"  - Content: {reminder_txt}"
    )
    
    return {
        "reminder_text": reminder_txt,
        "agent_logs": [log_msg]
    }

def create_response(state: MeetingSchedulerState) -> dict:
    """Compiles the final confirmation message to return to the interface."""
    logger.info("LangGraph Node: create_response")
    
    if state.get("final_response"):
        # If alternative suggestions were generated, final response is already formulated
        return {
            "agent_logs": ["[System]: Workflow complete with alternative options proposed."]
        }
        
    details = state.get("extracted_details", {})
    title = details.get("title", "Meeting")
    date = details.get("date", "")
    start_time = details.get("start_time", "")
    participants = details.get("participants", [])
    meeting_id = state.get("scheduled_meeting_id", -1)
    
    final_msg = (
        f"📅 **Meeting Successfully Scheduled!**\n\n"
        f"**Subject:** {title}\n"
        f"**Date:** {date}\n"
        f"**Time:** {start_time}\n"
        f"**Attendees:** {', '.join(normalize_participants(participants))}\n"
        f"**Meeting ID:** {meeting_id}\n\n"
        f"🔔 *Reminders have been set for all participants 15 minutes before start.*"
    )
    
    return {
        "final_response": final_msg,
        "agent_logs": ["[System]: Workflow complete. Meeting successfully scheduled."]
    }


# Assemble the LangGraph StateGraph
workflow = StateGraph(MeetingSchedulerState)

# Add Nodes
workflow.add_node("extract_info", extract_info)
workflow.add_node("availability_check", availability_check)
workflow.add_node("suggest_alternatives", suggest_alternatives)
workflow.add_node("schedule_meeting", schedule_meeting)
workflow.add_node("store_in_vectorstore", store_in_vectorstore)
workflow.add_node("generate_reminder", generate_reminder)
workflow.add_node("create_response", create_response)

# Set Entry Point
workflow.add_edge(START, "extract_info")
workflow.add_edge("extract_info", "availability_check")

# Add Conditional Edges from Availability Check
workflow.add_conditional_edges(
    "availability_check",
    decide_routing,
    {
        "schedule_meeting": "schedule_meeting",
        "suggest_alternatives": "suggest_alternatives"
    }
)

# Wire up scheduling chain
workflow.add_edge("schedule_meeting", "store_in_vectorstore")
workflow.add_edge("store_in_vectorstore", "generate_reminder")
workflow.add_edge("generate_reminder", "create_response")

# Wire up conflict resolution chain
workflow.add_edge("suggest_alternatives", "create_response")

# Set Exit Point
workflow.add_edge("create_response", END)

# Compile Graph
app_graph = workflow.compile()
logger.info("LangGraph workflow compiled successfully.")
