from database.db import db
from vectorstore.faiss_db import memory_db
from backend.calendar_manager import calendar_manager
from backend.availability_checker import availability_checker
from backend.conflict_resolver import conflict_resolver
from backend.reminder_service import reminder_service
from utils.logger import logger
from utils.helpers import parse_date, parse_time, normalize_participants
from typing import List, Dict, Any

class MeetingSchedulerService:
    def __init__(self):
        self.db = db
        self.vector_db = memory_db
        self.calendar = calendar_manager
        self.availability = availability_checker
        self.resolver = conflict_resolver
        self.reminders = reminder_service

    def schedule_meeting_flow(self, title: str, date: str, start_time: str, duration_mins: int, description: str, participants: List[str]) -> Dict[str, Any]:
        """
        Full backend sequence for committing a meeting:
        1. Checks availability.
        2. If unavailable, finds and returns alternatives.
        3. If available, commits to SQLite, stores summary in FAISS vector database, registers reminders, and returns details.
        """
        logger.info(f"SchedulerService: Initiating meeting flow for '{title}' on {date} at {start_time}")
        
        # 1. Availability check
        avail_res = self.availability.check_availability(date, start_time, duration_mins, participants)
        
        if not avail_res["available"]:
            # 2. Find alternatives
            alternatives = self.resolver.find_alternatives(date, duration_mins, participants)
            return {
                "status": "conflict",
                "message": f"Conflict detected. Participant(s) {', '.join(avail_res['busy_participants'])} are unavailable.",
                "alternatives": alternatives,
                "busy_participants": avail_res["busy_participants"]
            }
            
        # 3. Schedule the meeting
        try:
            event_res = self.calendar.create_event(
                title=title,
                date=date,
                start_time=start_time,
                duration_mins=duration_mins,
                description=description,
                participants=participants
            )
            
            if event_res["status"] == "success":
                meeting_id = event_res["meeting_id"]
                
                # 4. Store in FAISS
                self.vector_db.add_meeting_to_memory(
                    meeting_id=meeting_id,
                    title=title,
                    date=date,
                    start_time=start_time,
                    duration_mins=duration_mins,
                    description=description,
                    participants=participants
                )
                
                return {
                    "status": "success",
                    "meeting_id": meeting_id,
                    "title": title,
                    "date": date,
                    "start_time": start_time,
                    "duration_mins": duration_mins,
                    "description": description,
                    "participants": normalize_participants(participants),
                    "message": f"Meeting successfully scheduled (ID: {meeting_id}) and indexed in vector memory."
                }
            else:
                return {
                    "status": "error",
                    "message": event_res["message"]
                }
                
        except Exception as e:
            logger.error(f"SchedulerService flow error: {e}")
            return {
                "status": "error",
                "message": f"An unexpected error occurred during scheduling: {str(e)}"
            }

# Instantiated orchestrator
scheduler_service = MeetingSchedulerService()
