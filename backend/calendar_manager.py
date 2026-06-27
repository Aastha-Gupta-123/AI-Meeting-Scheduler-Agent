from database.db import db
from utils.logger import logger
from typing import List

class CalendarManager:
    def __init__(self, database=db):
        self.db = database

    def create_event(self, title: str, date: str, start_time: str, duration_mins: int, description: str, participants: List[str]) -> dict:
        """
        Commits a new meeting event to the calendar SQLite database.
        Returns a dict summarizing the scheduled event details.
        """
        logger.info(f"CalendarManager: Scheduling event '{title}' on {date} at {start_time} for participants {participants}")
        try:
            meeting_id = self.db.add_meeting(
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
                "participants": participants,
                "message": f"Successfully created event ID {meeting_id}."
            }
        except Exception as e:
            logger.error(f"CalendarManager error: Failed to schedule meeting. Error: {e}")
            return {
                "status": "error",
                "message": f"Failed to write calendar event: {str(e)}"
            }

    def list_events(self) -> List[dict]:
        """Returns all scheduled events in the system."""
        return self.db.get_meetings()

# Instantiated single service
calendar_manager = CalendarManager()
