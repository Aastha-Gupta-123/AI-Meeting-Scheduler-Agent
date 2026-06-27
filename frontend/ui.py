import os
import pandas as pd
import gradio as gr

from workflows.graph import app_graph
from database.db import db
from backend.reminder_service import reminder_service
from vectorstore.faiss_db import memory_db
from utils.logger import get_latest_logs, logger
from frontend.theme import get_custom_theme

# Load CSS Styles
CSS_PATH = os.path.join(os.path.dirname(__file__), "assets", "styles.css")
try:
    with open(CSS_PATH, "r", encoding="utf-8") as f:
        custom_css = f.read()
except Exception as e:
    logger.error(f"Failed to load CSS file: {e}")
    custom_css = ""

# Absolute Path to Logo
LOGO_PATH = os.path.join(os.path.dirname(__file__), "assets", "logo.png")

# Data Refresh Helpers
def get_meetings_dataframe():
    """Fetches meeting schedules from database and returns standard DataFrame."""
    meetings = db.get_meetings()
    if not meetings:
        return pd.DataFrame(columns=["ID", "Subject", "Date", "Start Time", "End Time", "Duration (Mins)", "Attendees", "Description"])
    
    data = []
    for m in meetings:
        data.append([
            m["id"],
            m["title"],
            m["date"],
            m["start_time"],
            m["end_time"],
            m["duration_mins"],
            m["participants_list"].replace(";", ", "),
            m["description"]
        ])
    return pd.DataFrame(data, columns=["ID", "Subject", "Date", "Start Time", "End Time", "Duration (Mins)", "Attendees", "Description"])

def get_reminders_dataframe():
    """Fetches alerts list and returns standard DataFrame."""
    reminders = db.get_reminders()
    if not reminders:
        return pd.DataFrame(columns=["ID", "Meeting Title", "Recipient Email", "Trigger Time", "Status", "Message Alert"])
        
    data = []
    for r in reminders:
        data.append([
            r["id"],
            r["meeting_title"] or "N/A",
            r["participant_email"],
            r["trigger_time"],
            r["status"],
            r["text"]
        ])
    return pd.DataFrame(data, columns=["ID", "Meeting Title", "Recipient Email", "Trigger Time", "Status", "Message Alert"])


def handle_schedule_chat(message: str, chat_history: list):
    """
    Submits user request into LangGraph flow and appends response to chat history.
    """
    if not message.strip():
        return "", chat_history, get_meetings_dataframe(), get_reminders_dataframe(), get_latest_logs()
        
    logger.info(f"UI: Received chat prompt: '{message}'")
    
    try:
        # Execute LangGraph workflow
        state = {"user_query": message, "agent_logs": []}
        result = app_graph.invoke(state)
        
        final_msg = result.get("final_response", "⚠️ Workflow execution returned an empty response.")
        agent_logs = result.get("agent_logs", [])
        
        # Append details into log file for tracing
        for log in agent_logs:
            logger.info(log)
            
    except Exception as e:
        logger.error(f"UI: LangGraph execution error: {e}")
        final_msg = f"❌ **Error executing workflow:** {str(e)}"
        
    chat_history.append({"role": "user", "content": message})
    chat_history.append({"role": "assistant", "content": final_msg})
    
    # Refresh dashboard elements
    meetings_df = get_meetings_dataframe()
    reminders_df = get_reminders_dataframe()
    latest_logs = get_latest_logs()
    
    return "", chat_history, meetings_df, reminders_df, latest_logs

def search_meeting_history(query: str):
    """Queries vector database and formats results."""
    if not query.strip():
        return "⚠️ Please enter a search term."
        
    results = memory_db.search_memory(query)
    if not results:
        return "🔍 No matches found in meeting memory."
        
    md = ""
    for idx, doc in enumerate(results):
        meta = doc.metadata
        md += f"### Match #{idx+1}: {meta.get('title')}\n"
        md += f"- **Date & Time:** {meta.get('date')}\n"
        md += f"- **Attendees:** {meta.get('participants')}\n"
        md += f"```text\n{doc.page_content}\n```\n\n---\n"
    return md

def run_reminder_checks():
    """Runs temporal check to trigger reminders."""
    processed = reminder_service.process_pending_reminders()
    reminders_df = get_reminders_dataframe()
    log_text = f"Processed {processed} pending reminders."
    logger.info(log_text)
    return reminders_df, get_latest_logs(), f"Success: {log_text}"


def create_ui():
    """Builds the Gradio Blocks Layout."""
    theme = get_custom_theme()
    
    with gr.Blocks(title="AI Meeting Scheduler Agent Dashboard") as demo:
        
        # Header Layout
        with gr.Row():
            with gr.Column(scale=1, min_width=80):
                if os.path.exists(LOGO_PATH):
                    gr.Image(LOGO_PATH, show_label=False, container=False, interactive=False, height=80, width=80)
            with gr.Column(scale=10):
                gr.Markdown(
                    """
                    # AI Meeting Scheduler Agent
                    ### Production-ready multi-agent scheduling assistant powered by LangGraph, CrewAI, FAISS, and SQLite.
                    """,
                    elem_classes=["header-container"]
                )
                
        # Main Dashboard Layout
        with gr.Tabs():
            
            # Tab 1: Chat interface and scheduled list
            with gr.TabItem("🗓️ Scheduler Dashboard"):
                with gr.Row():
                    
                    # Left: Chatbot Interface
                    with gr.Column(scale=5):
                        gr.Markdown("### 🤖 Natural Language Scheduler")
                        chatbot = gr.Chatbot(
                            label="Meeting Coordinator Chat",
                            value=[],
                            elem_id="chatbox",
                            height=400
                        )
                        msg_input = gr.Textbox(
                            placeholder="e.g. Schedule team sync with Alice and Bob tomorrow at 2 PM for 45 minutes about Roadmap alignment.",
                            label="Request",
                            lines=1,
                            max_lines=3,
                        )
                        with gr.Row():
                            clear_btn = gr.Button("🗑️ Clear Chat", variant="secondary")
                            submit_btn = gr.Button("🚀 Submit Request", variant="primary")
                            
                    # Right: Scheduled Meetings Table
                    with gr.Column(scale=7):
                        gr.Markdown("### 📅 Active Calendar Events")
                        meetings_tbl = gr.Dataframe(
                            value=get_meetings_dataframe(),
                            interactive=False,
                            wrap=True,
                        )
                        refresh_btn = gr.Button("🔄 Refresh Tables", variant="secondary")
                        
            # Tab 2: FAISS Semantic Search
            with gr.TabItem("🔍 Vector Meeting Memory"):
                gr.Markdown("### 🧠 Semantic History Retrieval")
                gr.Markdown("Ask natural questions about past schedules. The system searches the FAISS Vector Database for contextual memory.")
                
                with gr.Row():
                    search_input = gr.Textbox(placeholder="e.g. Find meetings involving bob about roadmap", label="Search Prompt")
                    search_action = gr.Button("🔍 Search Vector DB", variant="primary")
                    
                search_output = gr.Markdown("*Search results will appear here.*")
                
            # Tab 3: Reminders & Alerts
            with gr.TabItem("🔔 Reminders & Notifications"):
                gr.Markdown("### 🕒 SQLite Scheduled Alerts (15 Minutes Prior)")
                
                with gr.Row():
                    reminders_tbl = gr.Dataframe(
                        value=get_reminders_dataframe(),
                        interactive=False,
                        wrap=True
                    )
                with gr.Row():
                    reminder_status_text = gr.Markdown("*Pending reminders check results will show here.*")
                with gr.Row():
                    trigger_reminders_btn = gr.Button("⏰ Check & Process Reminders", variant="primary")

            # Tab 4: Agent Tracing Logs
            with gr.TabItem("📋 Agent Activity Logs"):
                gr.Markdown("### 🔍 Real-time Log Stream")
                gr.Markdown("Trace background executions, LLM parser output, availability audits, and LangGraph workflow nodes.")
                
                logs_box = gr.Textbox(
                    value=get_latest_logs(),
                    label="scheduler.log",
                    lines=15,
                    max_lines=30,
                    elem_classes=["log-box"],
                    interactive=False
                )
                refresh_logs_btn = gr.Button("🔄 Refresh Logs", variant="secondary")

        # Connect actions
        
        # Chat interactions
        submit_btn.click(
            handle_schedule_chat,
            inputs=[msg_input, chatbot],
            outputs=[msg_input, chatbot, meetings_tbl, reminders_tbl, logs_box]
        )
        msg_input.submit(
            handle_schedule_chat,
            inputs=[msg_input, chatbot],
            outputs=[msg_input, chatbot, meetings_tbl, reminders_tbl, logs_box]
        )
        
        clear_btn.click(lambda: ("", []), outputs=[msg_input, chatbot])
        
        # Refresh buttons
        refresh_btn.click(
            fn=lambda: (get_meetings_dataframe(), get_reminders_dataframe(), get_latest_logs()),
            outputs=[meetings_tbl, reminders_tbl, logs_box]
        )
        
        refresh_logs_btn.click(
            fn=get_latest_logs,
            outputs=logs_box
        )
        
        # Semantic search
        search_action.click(
            search_meeting_history,
            inputs=search_input,
            outputs=search_output
        )
        
        # Process reminders
        trigger_reminders_btn.click(
            run_reminder_checks,
            outputs=[reminders_tbl, logs_box, reminder_status_text]
        )
        
    return demo, theme, custom_css
