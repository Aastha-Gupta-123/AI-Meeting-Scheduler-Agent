from crewai import Agent
from llm.model_loader import get_llm
from llm.prompts import SCHEDULER_SYSTEM_PROMPT

def get_scheduler_agent() -> Agent:
    """
    Returns the CrewAI Agent responsible for extracting structured meeting details
    from natural language user prompts.
    """
    llm = get_llm()
    return Agent(
        role="Meeting Scheduler Specialist",
        goal="Extract title, date, start_time, duration_mins, and participants list from meeting requests.",
        backstory=(
            "You are an elite virtual assistant specialized in parsing natural language commands. "
            "Your critical task is to strip away irrelevant wording and accurately identify "
            "meeting details (who, when, what, and for how long), formatting them in clean, structured JSON."
        ),
        llm=llm,
        verbose=True,
        allow_delegation=False
    )
