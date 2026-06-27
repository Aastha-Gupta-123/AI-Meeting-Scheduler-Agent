from datetime import datetime, timedelta
from database.db import db
from utils.logger import logger
from utils.helpers import normalize_participants
from typing import List, Dict, Any

class ConflictResolver:
    def __init__(self, database=db):
        self.db = database

    def find_alternatives(self, date: str, duration_mins: int, participants: List[str], max_suggestions: int = 3) -> List[Dict[str, Any]]:
        """
        Scans working hours (9 AM - 5 PM) on the proposed date and subsequent days to locate
        conflict-free slots for all participants.
        Returns a list of suggested slots with date, start_time, and end_time.
        """
        logger.info(f"ConflictResolver: Searching alternative slots for {participants} starting from {date} (Duration: {duration_mins} mins)")
        
        normalized_emails = normalize_participants(participants)
        suggestions = []
        
        # Parse initial date
        try:
            current_date_obj = datetime.strptime(date, "%Y-%m-%d")
        except Exception:
            current_date_obj = datetime.today()

        # Define working hours hourly increments
        work_hours = ["09:00", "10:00", "11:00", "12:00", "13:00", "14:00", "15:00", "16:00"]
        
        # Search over 3 days (proposed date + 2 days)
        for offset in range(3):
            date_to_check = (current_date_obj + timedelta(days=offset)).strftime("%Y-%m-%d")
            
            for start_time in work_hours:
                if len(suggestions) >= max_suggestions:
                    break
                
                # Check conflicts for this candidate slot
                has_conflict, _ = self.db.check_conflicts(
                    date=date_to_check,
                    start_time=start_time,
                    duration_mins=duration_mins,
                    participants=normalized_emails
                )
                
                if not has_conflict:
                    # Calculate end time
                    from utils.helpers import calculate_end_time
                    end_time = calculate_end_time(start_time, duration_mins)
                    
                    # Ensure suggested slot is in the future if it's today
                    if date_to_check == datetime.today().strftime("%Y-%m-%d"):
                        now_str = datetime.now().strftime("%H:%M")
                        if start_time <= now_str:
                            continue # skip past times today
                            
                    suggestions.append({
                        "date": date_to_check,
                        "start_time": start_time,
                        "end_time": end_time,
                        "duration_mins": duration_mins
                    })
                    
            if len(suggestions) >= max_suggestions:
                break
                
        logger.info(f"ConflictResolver: Found {len(suggestions)} alternative slots.")
        return suggestions

# Instantiated service
conflict_resolver = ConflictResolver()
