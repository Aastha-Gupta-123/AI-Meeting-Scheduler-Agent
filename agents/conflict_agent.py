from crewai import Agent
from llm.model_loader import get_llm

def get_conflict_agent() -> Agent:
    """
    Returns the CrewAI Agent responsible for finding alternative times when conflicts are found.
    """
    llm = get_llm()
    return Agent(
        role="Conflict Resolution Officer",
        goal="Resolve schedule conflicts and recommend standard work hour slots that work for all attendees.",
        backstory=(
            "You are a master coordinator. When conflicts occur, you seamlessly compute alternative "
            "options during standard hours to get everyone aligned without back-and-forth emails."
        ),
        llm=llm,
        verbose=True,
        allow_delegation=False
    )
