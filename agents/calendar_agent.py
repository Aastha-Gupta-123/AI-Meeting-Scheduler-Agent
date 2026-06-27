from crewai import Agent
from llm.model_loader import get_llm

def get_calendar_agent() -> Agent:
    """
    Returns the CrewAI Agent responsible for final calendar additions.
    """
    llm = get_llm()
    return Agent(
        role="Calendar Integration Officer",
        goal="Commit confirmed meeting details to databases and draft a clean execution summary.",
        backstory=(
            "You are a database and systems integration expert. You write schedules "
            "to the central database and ensure all records are consistent and complete."
        ),
        llm=llm,
        verbose=True,
        allow_delegation=False
    )
