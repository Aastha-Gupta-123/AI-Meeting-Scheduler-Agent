from database.db import db
from utils.logger import logger
from utils.helpers import normalize_participants
from typing import List, Dict, Any

class AvailabilityChecker:
    def __init__(self, database=db):
        self.db = database

    def check_availability(self, date: str, start_time: str, duration_mins: int, participants: List[str]) -> Dict[str, Any]:
        """
        Queries the database for existing meeting overlaps for any participant.
        Returns check summary including flags, busy list, and descriptions.
        """
        logger.info(f"AvailabilityChecker: Checking availability on {date} at {start_time} for {participants}")
        
        normalized_emails = normalize_participants(participants)
        if not normalized_emails:
            return {
                "available": True,
                "busy_participants": [],
                "conflicting_meetings": [],
                "message": "No valid participants provided. Slot is considered available."
            }

        try:
            # Query conflicts from DB
            has_conflict, conflicts = self.db.check_conflicts(
                date=date,
                start_time=start_time,
                duration_mins=duration_mins,
                participants=normalized_emails
            )
            
            if not has_conflict:
                logger.info("AvailabilityChecker: All participants are available.")
                return {
                    "available": True,
                    "busy_participants": [],
                    "conflicting_meetings": [],
                    "message": "All participants are free."
                }
            
            # Find which exact participants have conflicts
            busy_participants = set()
            for conflict in conflicts:
                conflict_emails = conflict["participants_list"].split(";")
                overlapping_busy = set(normalized_emails).intersection(set(conflict_emails))
                busy_participants.update(overlapping_busy)

            busy_list = list(busy_participants)
            logger.info(f"AvailabilityChecker: Conflicts found. Busy participants: {busy_list}")
            
            return {
                "available": False,
                "busy_participants": busy_list,
                "conflicting_meetings": conflicts,
                "message": f"Conflict detected for: {', '.join(busy_list)}."
            }
            
        except Exception as e:
            logger.error(f"AvailabilityChecker error: {e}")
            return {
                "available": False,
                "busy_participants": [],
                "conflicting_meetings": [],
                "message": f"Error during availability checks: {str(e)}"
            }

# Instantiated service
availability_checker = AvailabilityChecker()
