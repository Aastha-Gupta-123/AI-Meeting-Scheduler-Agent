import os
import sys

# Add root folder to sys.path to resolve imports smoothly
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from utils.config import config
from utils.logger import logger
from database.db import db
from vectorstore.faiss_db import memory_db
from frontend.ui import create_ui

def main():
    logger.info("==================================================")
    logger.info("Starting AI Meeting Scheduler Agent System...")
    logger.info(f"Root Workspace Directory: {BASE_DIR}")
    
    # 1. Initialize databases
    try:
        logger.info("Bootstrapping SQLite calendar records...")
        db.init_db()
        logger.info("Bootstrapping FAISS vector retrieval records...")
        memory_db.load_or_create_db()
    except Exception as e:
        logger.critical(f"Failed to initialize database structures: {e}")
        sys.exit(1)
        
    # 2. Compile Gradio UI
    logger.info("Initializing Gradio blocks layout...")
    demo, theme, css = create_ui()
    
    # 3. Launch UI Server
    host = config.HOST
    port = config.PORT
    
    logger.info(f"Launching Gradio dashboard server on http://{host}:{port} ...")
    demo.launch(
        server_name=host,
        server_port=port,
        share=False,
        show_error=True,
        theme=theme,
        css=css
    )

if __name__ == "__main__":
    main()
