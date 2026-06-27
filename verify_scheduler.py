import os
import sys

# Ensure base directory is in system path
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from database.db import db
from vectorstore.faiss_db import memory_db
from workflows.graph import app_graph
from utils.logger import logger

def verify_pipeline():
    logger.info("==========================================")
    logger.info("Starting Pipeline Verification...")
    logger.info("==========================================")

    # Clean existing database files to make the verification test idempotent
    import shutil
    from utils.config import config
    
    if os.path.exists(config.DB_PATH):
        try:
            os.remove(config.DB_PATH)
            logger.info("Deleted existing SQLite database for a clean verification run.")
        except Exception as e:
            logger.warning(f"Could not delete SQLite DB file: {e}")

    if os.path.exists(config.FAISS_PATH):
        try:
            shutil.rmtree(config.FAISS_PATH)
            logger.info("Deleted existing FAISS index directory for a clean verification run.")
        except Exception as e:
            logger.warning(f"Could not delete FAISS directory: {e}")

    # 1. Initialize DB and FAISS
    db.init_db()
    memory_db.load_or_create_db()

    # Get initial meeting count
    initial_meetings = db.get_meetings()
    logger.info(f"Initial scheduled meetings in SQLite: {len(initial_meetings)}")

    # 2. Invoke LangGraph with a request that is known to overlap
    # Sample meetings CSV seeds 'alice@example.com;bob@example.com' on 2026-06-15 from 10:00 to 11:00
    # Let's request a slot that is free first to test scheduling:
    # "Schedule roadmap sync with Alice and Charlie tomorrow at 3 PM for 60 mins."
    free_request = "Schedule roadmap sync with Alice and Charlie on 2026-06-17 at 3 PM for 60 mins."
    logger.info(f"Submitting FREE slot request: '{free_request}'")
    
    state_free = {"user_query": free_request, "agent_logs": []}
    res_free = app_graph.invoke(state_free)
    
    logger.info("Result details:")
    logger.info(res_free.get("final_response"))
    logger.info("Logs:")
    for log in res_free.get("agent_logs", []):
        logger.info(log)

    # Check database now
    updated_meetings = db.get_meetings()
    logger.info(f"Scheduled meetings in SQLite now: {len(updated_meetings)}")
    assert len(updated_meetings) == len(initial_meetings) + 1, "Failed: Meeting was not added to SQLite."

    # Search in FAISS
    logger.info("Testing semantic search in FAISS vector database...")
    search_res = memory_db.search_memory("roadmap")
    logger.info(f"Semantic search found {len(search_res)} matching documents.")
    for idx, doc in enumerate(search_res):
        logger.info(f"Match {idx+1}: {doc.metadata.get('title')} - Content: {doc.page_content}")
    
    # Verify reminders exist
    reminders = db.get_reminders()
    logger.info(f"Total reminders in SQLite: {len(reminders)}")
    assert len(reminders) > 0, "Failed: No reminders were created."

    # 3. Request a slot that is busy (2026-06-15 at 10:00) to test Conflict Resolution routing
    busy_request = "Schedule sync with Alice and Bob on 2026-06-15 at 10:00 AM for 60 mins."
    logger.info(f"Submitting CONFLICTING slot request: '{busy_request}'")
    
    state_busy = {"user_query": busy_request, "agent_logs": []}
    res_busy = app_graph.invoke(state_busy)
    
    logger.info("Result details:")
    logger.info(res_busy.get("final_response"))
    logger.info("Logs:")
    for log in res_busy.get("agent_logs", []):
        logger.info(log)

    # Check database meetings didn't increase
    final_meetings = db.get_meetings()
    assert len(final_meetings) == len(updated_meetings), "Failed: Conflicting meeting was scheduled."

    logger.info("==========================================")
    logger.info("Pipeline Verification Successful! All Assertions Passed.")
    logger.info("==========================================")

if __name__ == "__main__":
    verify_pipeline()
