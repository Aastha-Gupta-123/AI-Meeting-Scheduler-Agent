from crewai import Agent
from llm.model_loader import get_llm

def get_reminder_agent() -> Agent:
    """
    Returns the CrewAI Agent responsible for creating meeting reminders.
    """
    llm = get_llm()
    return Agent(
        role="Meeting Notification Specialist",
        goal="Generate professional reminder summaries and email alert text for meeting invitees.",
        backstory=(
            "You are a clear and concise communicator. You craft high-impact notification "
            "messages that specify the meeting's purpose, time, and attendee list."
        ),
        llm=llm,
        verbose=True,
        allow_delegation=False
    )
