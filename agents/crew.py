import json
from crewai import Crew, Task, Process
from utils.logger import logger

# Import agents
from agents.scheduler_agent import get_scheduler_agent
from agents.availability_agent import get_availability_agent
from agents.conflict_agent import get_conflict_agent
from agents.reminder_agent import get_reminder_agent
from agents.calendar_agent import get_calendar_agent

class MeetingSchedulerCrew:
    def __init__(self):
        # Instantiate agents
        self.scheduler_agent = get_scheduler_agent()
        self.availability_agent = get_availability_agent()
        self.conflict_agent = get_conflict_agent()
        self.reminder_agent = get_reminder_agent()
        self.calendar_agent = get_calendar_agent()

    def run_extraction_crew(self, request_text: str) -> dict:
        """
        Runs a CrewAI task to parse a natural language scheduling request
        and extract structured details.
        """
        logger.info("CrewAI: Executing extraction crew...")
        
        extract_task = Task(
            description=(
                f"Analyze this raw meeting request: '{request_text}'\n"
                "Extract the following fields:\n"
                "- title (brief agenda summary)\n"
                "- date (YYYY-MM-DD)\n"
                "- start_time (HH:MM format)\n"
                "- duration_mins (integer minutes)\n"
                "- participants (list of attendee email addresses)\n"
                "- description (purpose sentence)\n"
                "You must output ONLY a valid JSON object. No other text."
            ),
            expected_output="A JSON codeblock containing keys: title, date, start_time, duration_mins, participants, description.",
            agent=self.scheduler_agent
        )

        crew = Crew(
            agents=[self.scheduler_agent],
            tasks=[extract_task],
            process=Process.sequential,
            verbose=True
        )
        
        result_text = crew.kickoff()
        logger.info(f"CrewAI: Extraction finished. Raw output: {result_text}")
        
        # Clean markdown codeblock wrap if present
        clean_text = str(result_text).strip()
        if clean_text.startswith("```"):
            # Strip codeblock wrappers
            clean_text = re.sub(r"^```(?:json)?\n|```$", "", clean_text, flags=re.MULTILINE).strip()
            
        try:
            # Let's import re here inside the function in case it's needed
            import re
            # Ensure double backticks or other formats are cleaned
            clean_text = re.sub(r"^```(?:json)?\n|```$", "", str(result_text), flags=re.MULTILINE).strip()
            return json.loads(clean_text)
        except Exception as e:
            logger.warning(f"CrewAI extraction did not output valid JSON: {e}. Attempting manual fallback parse.")
            # Standard regex fallback logic
            from utils.helpers import parse_date, parse_time
            # Try to search for json block
            json_search = re.search(r"\{.*\}", str(result_text), re.DOTALL)
            if json_search:
                try:
                    return json.loads(json_search.group(0))
                except Exception:
                    pass
            
            # Simple rule-based extraction fallback if LLM returned free text
            participants = []
            for user in ["alice", "bob", "charlie", "hr", "manager"]:
                if user in request_text.lower():
                    participants.append(f"{user}@example.com")
            if not participants:
                participants = ["alice@example.com"]
                
            return {
                "title": "Meeting",
                "date": parse_date("tomorrow"),
                "start_time": "10:00",
                "duration_mins": 60,
                "participants": participants,
                "description": f"Extracted from request: {request_text}"
            }

    def run_reminder_generation_crew(self, title: str, date: str, start_time: str, participants: list) -> str:
        """
        Runs CrewAI task to generate a professional reminder message text.
        """
        logger.info("CrewAI: Executing reminder generation crew...")
        
        reminder_task = Task(
            description=(
                f"Draft a professional, brief reminder notification for a meeting titled '{title}'.\n"
                f"Details: Date={date}, Time={start_time}, Attendees={', '.join(participants)}.\n"
                "The text should be welcoming and direct."
            ),
            expected_output="A single paragraph containing the meeting reminder text.",
            agent=self.reminder_agent
        )

        crew = Crew(
            agents=[self.reminder_agent],
            tasks=[reminder_task],
            process=Process.sequential,
            verbose=True
        )
        
        result = crew.kickoff()
        return str(result).strip()

    def run_conflict_resolution_crew(self, title: str, date: str, start_time: str, duration_mins: int, participants: list, busy_list: list, alternatives: list) -> str:
        """
        Runs CrewAI task to formulate a friendly response explaining scheduling conflicts
        and proposing alternative dates/times.
        """
        logger.info("CrewAI: Executing conflict resolver crew...")
        
        alt_str = "\n".join([f"- {a['date']} at {a['start_time']} ({a['duration_mins']} mins)" for a in alternatives])
        
        conflict_task = Task(
            description=(
                f"We attempted to schedule a meeting '{title}' on {date} at {start_time} for attendees: {', '.join(participants)}.\n"
                f"However, a scheduling conflict was detected. Busy participants: {', '.join(busy_list)}.\n"
                f"Here are the alternative slots we computed:\n{alt_str}\n"
                "Draft a polite, informative response explaining the conflict and proposing these alternative slots for confirmation."
            ),
            expected_output="A polite message outlining the conflict and presenting the computed alternative slots.",
            agent=self.conflict_agent
        )

        crew = Crew(
            agents=[self.conflict_agent],
            tasks=[conflict_task],
            process=Process.sequential,
            verbose=True
        )
        
        result = crew.kickoff()
        return str(result).strip()

# Instantiated crew manager
crew_manager = MeetingSchedulerCrew()
