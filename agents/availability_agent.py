from crewai import Agent
from llm.model_loader import get_llm

def get_availability_agent() -> Agent:
    """
    Returns the CrewAI Agent responsible for checking participant schedules in SQLite.
    """
    llm = get_llm()
    return Agent(
        role="Participant Availability Auditor",
        goal="Audit availability records for each requested email to confirm no schedule overlaps exist.",
        backstory=(
            "You are a detail-oriented auditor. You verify schedule availability for proposed "
            "meetings, and ensure no developer or stakeholder is double-booked."
        ),
        llm=llm,
        verbose=True,
        allow_delegation=False
    )
