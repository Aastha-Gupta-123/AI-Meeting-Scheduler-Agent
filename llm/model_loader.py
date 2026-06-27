import os
import json
import re
from typing import List, Optional, Any, Dict

from crewai.llm import LLM as CrewLLM

from utils.config import config
from utils.logger import logger
from utils.helpers import parse_date, parse_time, normalize_participants

def _mock_extraction(text: str) -> str:
    """Helper to extract details using regex patterns."""
    title = "Meeting"
    duration = 60
    date_val = ""
    time_val = ""
    participants = []

    # Find Title/Agenda
    title_match = re.search(r"about ([\w\s\-]{3,40})", text, re.IGNORECASE)
    if title_match:
        title = title_match.group(1).strip()
    else:
        for keyword in ["kick-off", "sync", "roadmap review", "marketing", "brainstorm", "catch-up", "interview"]:
            if keyword in text.lower():
                title = keyword.title()
                break

    # Find Duration
    dur_match = re.search(r"(\d+)\s*(minute|min|hour|hr)", text, re.IGNORECASE)
    if dur_match:
        qty = int(dur_match.group(1))
        unit = dur_match.group(2).lower()
        if "hour" in unit or "hr" in unit:
            duration = qty * 60
        else:
            duration = qty

    # Find Date
    date_explicit = re.search(r"\b\d{4}-\d{2}-\d{2}\b", text)
    if date_explicit:
        date_val = date_explicit.group(0)
    else:
        for rel in ["today", "tomorrow", "day after tomorrow", "monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]:
            if rel in text.lower():
                date_val = parse_date(rel)
                break
    if not date_val:
        date_val = parse_date("tomorrow")

    # Find Time
    time_match = re.search(r"\b\d{1,2}:\d{2}\s*(?:am|pm)?\b|\b\d{1,2}\s*(?:am|pm)\b", text, re.IGNORECASE)
    if time_match:
        time_val = parse_time(time_match.group(0))
    else:
        time_val = "10:00"

    # Find Participants
    for user in ["alice", "bob", "charlie", "hr", "manager"]:
        if user in text.lower():
            participants.append(f"{user}@example.com")
    
    if not participants:
        participants = ["alice@example.com", "bob@example.com"]

    result = {
        "title": title,
        "date": date_val,
        "start_time": time_val,
        "duration_mins": duration,
        "participants": participants,
        "description": f"Scheduled meeting about {title}."
    }
    
    return json.dumps(result, indent=2)

def _mock_availability(text: str) -> str:
    if "conflict" in text.lower():
        return "Some participants have conflicts. alice@example.com is busy."
    return "All participants are available for the proposed meeting slot."

def _mock_conflict_resolution(text: str) -> str:
    return (
        "Conflict detected for Alice between 10:00 and 11:00. "
        "Suggested alternative slots: 13:00-14:00, 14:00-15:00 on the same day."
    )

def _mock_reminder(text: str) -> str:
    return "Reminder created: You have a meeting starting in 15 minutes."

def _mock_calendar_action(text: str) -> str:
    return "Meeting has been successfully scheduled and calendar updated."

class MockLLM(CrewLLM):
    """
    A custom CrewAI LLM subclass that mocks answers locally.
    Guarantees compatibility with CrewAI's Pydantic BaseLLM type checks.
    """
    def __new__(cls, *args: Any, **kwargs: Any) -> "MockLLM":
        # Bypass CrewLLM.__new__ factory logic
        return object.__new__(cls)

    def __init__(self, **kwargs: Any):
        kwargs.setdefault("model", "mock-scheduler-llm")
        super().__init__(**kwargs)

    def call(
        self,
        messages: Any,
        tools: Any = None,
        callbacks: Any = None,
        available_functions: Any = None,
        from_task: Any = None,
        from_agent: Any = None,
        response_model: Any = None,
    ) -> str:
        # Extract prompt text
        if isinstance(messages, str):
            combined_text = messages
        elif isinstance(messages, list):
            parts = []
            for msg in messages:
                if isinstance(msg, dict):
                    parts.append(msg.get("content", ""))
                elif hasattr(msg, "content"):
                    parts.append(getattr(msg, "content", ""))
                elif isinstance(msg, str):
                    parts.append(msg)
                else:
                    parts.append(str(msg))
            combined_text = "\n".join(parts)
        else:
            combined_text = str(messages)
            
        logger.debug(f"MockLLM input text snippet: {combined_text[:300]}...")
        
        if "extract" in combined_text.lower() or "agenda" in combined_text.lower() or "meeting request" in combined_text.lower():
            return _mock_extraction(combined_text)
        elif "availability" in combined_text.lower() or "available" in combined_text.lower():
            return _mock_availability(combined_text)
        elif "conflict" in combined_text.lower() or "overlap" in combined_text.lower() or "alternative" in combined_text.lower():
            return _mock_conflict_resolution(combined_text)
        elif "reminder" in combined_text.lower() or "alert" in combined_text.lower():
            return _mock_reminder(combined_text)
        elif "calendar" in combined_text.lower() or "schedule" in combined_text.lower() or "save" in combined_text.lower():
            return _mock_calendar_action(combined_text)
        else:
            return (
                "I am the AI Meeting Scheduler Assistant. I can help you extract meeting details, "
                "check availability, detect conflicts, suggest alternatives, and schedule meetings."
            )

    async def acall(self, messages: Any, **kwargs: Any) -> str:
        return self.call(messages, **kwargs)

def get_llm() -> Any:
    """
    Factory function to load the correct CrewAI LLM based on configuration.
    """
    provider = config.LLM_PROVIDER
    model = config.MODEL_NAME
    
    logger.info(f"Loading ChatModel/LLM for provider: {provider}, model: {model}")
    
    try:
        if provider == "groq":
            if not config.GROQ_API_KEY:
                logger.warning("GROQ_API_KEY is not set. Falling back to Mock LLM.")
                return MockLLM()
            return CrewLLM(model=f"groq/{model}", api_key=config.GROQ_API_KEY)
            
        elif provider == "gemini":
            if not config.GEMINI_API_KEY:
                logger.warning("GEMINI_API_KEY is not set. Falling back to Mock LLM.")
                return MockLLM()
            return CrewLLM(model=f"gemini/{model}", api_key=config.GEMINI_API_KEY)
            
        elif provider == "openai":
            if not config.OPENAI_API_KEY:
                logger.warning("OPENAI_API_KEY is not set. Falling back to Mock LLM.")
                return MockLLM()
            return CrewLLM(model=model, api_key=config.OPENAI_API_KEY)
            
        elif provider == "ollama":
            return CrewLLM(model=f"ollama/{model}", base_url=config.OLLAMA_BASE_URL)
            
        elif provider == "mock":
            return MockLLM()
            
        else:
            logger.error(f"Unknown LLM provider: {provider}. Defaulting to MockLLM.")
            return MockLLM()
            
    except Exception as e:
        logger.error(f"Error loading LLM provider '{provider}': {e}. Falling back to MockLLM.")
        return MockLLM()
