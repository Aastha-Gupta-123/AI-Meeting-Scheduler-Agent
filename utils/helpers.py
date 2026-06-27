import re
from datetime import datetime, timedelta
from utils.logger import logger

def parse_date(date_str: str) -> str:
    """
    Parses a date string and returns it in YYYY-MM-DD format.
    Supports relative dates: 'today', 'tomorrow', 'day after tomorrow', 'in N days'
    Supports standard formats like YYYY-MM-DD, MM/DD/YYYY, DD-MM-YYYY, etc.
    """
    if not date_str:
        return datetime.today().strftime("%Y-%m-%d")
        
    date_str_clean = date_str.lower().strip()
    today = datetime.today()

    # Relative days
    if date_str_clean == "today":
        return today.strftime("%Y-%m-%d")
    elif date_str_clean == "tomorrow":
        return (today + timedelta(days=1)).strftime("%Y-%m-%d")
    elif date_str_clean == "day after tomorrow":
        return (today + timedelta(days=2)).strftime("%Y-%m-%d")
    
    # Matches 'in X days'
    match_in_days = re.search(r"in (\d+) day", date_str_clean)
    if match_in_days:
        days = int(match_in_days.group(1))
        return (today + timedelta(days=days)).strftime("%Y-%m-%d")
        
    # Matches 'next Monday/Tuesday/etc'
    weekdays = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
    for i, w in enumerate(weekdays):
        if f"next {w}" in date_str_clean or f"on {w}" in date_str_clean or date_str_clean == w:
            current_wd = today.weekday()  # Mon = 0, Sun = 6
            target_wd = i
            days_ahead = target_wd - current_wd
            if days_ahead <= 0:  # Target day has passed this week, or is today
                days_ahead += 7
            return (today + timedelta(days=days_ahead)).strftime("%Y-%m-%d")

    # Try standard date parses
    formats = [
        "%Y-%m-%d", "%d-%m-%Y", "%m/%d/%Y", "%d/%m/%Y",
        "%B %d, %Y", "%b %d, %Y", "%d %B %Y", "%d %b %Y",
        "%Y/%m/%d"
    ]
    for fmt in formats:
        try:
            parsed = datetime.strptime(date_str, fmt)
            # Adjust year if it's missing or parsed as 1900
            if parsed.year == 1900:
                parsed = parsed.replace(year=today.year)
            return parsed.strftime("%Y-%m-%d")
        except ValueError:
            continue

    # Fallback: clean non-digits and try simple formats or return today
    logger.warning(f"Could not reliably parse date: '{date_str}'. Falling back to current date.")
    return today.strftime("%Y-%m-%d")


def parse_time(time_str: str) -> str:
    """
    Parses a time string and returns it in HH:MM format (24-hour).
    Supports formats like '3 PM', '15:30', '10:00 AM', 'noon', etc.
    """
    if not time_str:
        return "09:00"
        
    time_str_clean = time_str.lower().strip()
    
    if time_str_clean == "noon":
        return "12:00"
    if time_str_clean == "midnight":
        return "00:00"
        
    # Clean string and parse standard time
    # Check AM/PM
    is_pm = "pm" in time_str_clean
    is_am = "am" in time_str_clean
    
    # Extract digits
    digits = re.findall(r"\d+", time_str_clean)
    if not digits:
        return "09:00"
        
    hour = int(digits[0])
    minute = int(digits[1]) if len(digits) > 1 else 0
    
    if is_pm and hour < 12:
        hour += 12
    elif is_am and hour == 12:
        hour = 0
        
    # Format to HH:MM
    return f"{hour:02d}:{minute:02d}"


def calculate_end_time(start_time_str: str, duration_mins: int) -> str:
    """
    Calculates end time based on start time (HH:MM) and duration in minutes.
    """
    try:
        t = datetime.strptime(start_time_str, "%H:%M")
        end_t = t + timedelta(minutes=duration_mins)
        return end_t.strftime("%H:%M")
    except Exception as e:
        logger.error(f"Error calculating end time: {e}")
        return start_time_str


def is_overlapping(start1: str, end1: str, start2: str, end2: str) -> bool:
    """
    Checks if two time intervals overlap.
    """
    try:
        s1 = datetime.strptime(start1, "%H:%M").time()
        e1 = datetime.strptime(end1, "%H:%M").time()
        s2 = datetime.strptime(start2, "%H:%M").time()
        e2 = datetime.strptime(end2, "%H:%M").time()
        
        # Overlap happens when max(start) < min(end)
        return max(s1, s2) < min(e1, e2)
    except Exception as e:
        logger.error(f"Overlap check failed: {e}")
        return False


def normalize_participants(participants_input) -> list:
    """
    Normalizes different participant inputs (string, list, semi-colon separated) into a list of emails.
    Converts name tokens to emails if they don't look like emails (e.g. 'Alice' -> 'alice@example.com').
    """
    if not participants_input:
        return []
        
    if isinstance(participants_input, str):
        # Split on commas, semicolons or 'and'
        parts = re.split(r"[,;]|\band\b", participants_input)
    elif isinstance(participants_input, list):
        parts = participants_input
    else:
        parts = [str(participants_input)]
        
    emails = []
    for p in parts:
        clean_p = p.strip()
        if not clean_p:
            continue
        # Check if it looks like an email
        if "@" in clean_p:
            emails.append(clean_p.lower())
        else:
            # Generate a default mock email for names
            email_friendly = re.sub(r"\s+", "", clean_p).lower()
            emails.append(f"{email_friendly}@example.com")
            
    return list(dict.fromkeys(emails)) # remove duplicates keeping order
