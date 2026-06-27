import os
import logging
from logging.handlers import RotatingFileHandler

# Define paths
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOG_FILE = os.path.join(BASE_DIR, "scheduler.log")

def setup_logger(name="meeting_scheduler", log_level=logging.INFO):
    """
    Sets up a global logger that writes to both console and a rotating log file.
    """
    logger = logging.getLogger(name)
    logger.setLevel(log_level)

    # Avoid duplicate handlers if logger is already configured
    if logger.handlers:
        return logger

    # Create formatter
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s"
    )

    # Console Handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # File Handler (rotating, max 5MB, keep 3 backup copies)
    file_handler = RotatingFileHandler(
        LOG_FILE, maxBytes=5 * 1024 * 1024, backupCount=3, encoding="utf-8"
    )
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    return logger

# Initialize default logger
logger = setup_logger()

def get_latest_logs(num_lines=50):
    """
    Reads the last N lines of the log file to display in the UI.
    """
    if not os.path.exists(LOG_FILE):
        return "No log file found yet."
    
    try:
        with open(LOG_FILE, "r", encoding="utf-8") as f:
            lines = f.readlines()
            return "".join(lines[-num_lines:])
    except Exception as e:
        return f"Error reading logs: {str(e)}"
