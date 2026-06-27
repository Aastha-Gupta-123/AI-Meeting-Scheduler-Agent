import os
from dotenv import load_dotenv
from utils.logger import logger

# Load environment variables
load_dotenv()

# Base directory
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Config Class
class Config:
    BASE_DIR = BASE_DIR
    # LLM Settings
    LLM_PROVIDER = os.getenv("LLM_PROVIDER", "mock").lower()
    MODEL_NAME = os.getenv("MODEL_NAME", "gemma2-9b-it")
    
    # API Keys
    GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
    
    # Ollama settings
    OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    
    # Embeddings
    EMBEDDING_MODEL_NAME = os.getenv("EMBEDDING_MODEL_NAME", "sentence-transformers/all-MiniLM-L6-v2")
    
    # Paths
    DB_RELATIVE_PATH = os.getenv("DB_PATH", "database/meetings.db")
    FAISS_RELATIVE_PATH = os.getenv("FAISS_PATH", "vectorstore/meeting_memory")
    
    DB_PATH = os.path.join(BASE_DIR, DB_RELATIVE_PATH)
    FAISS_PATH = os.path.join(BASE_DIR, FAISS_RELATIVE_PATH)
    
    # Create directories if they don't exist
    db_dir = os.path.dirname(DB_PATH)
    if db_dir and not os.path.exists(db_dir):
        os.makedirs(db_dir, exist_ok=True)
        logger.info(f"Created database directory at {db_dir}")
        
    faiss_dir = os.path.dirname(FAISS_PATH)
    if faiss_dir and not os.path.exists(faiss_dir):
        os.makedirs(faiss_dir, exist_ok=True)
        logger.info(f"Created FAISS directory at {faiss_dir}")
        
    # Application Config
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
    PORT = int(os.getenv("PORT", "7860"))
    HOST = os.getenv("HOST", "127.0.0.1")

# Instantiate configuration
config = Config()
logger.info(f"Configuration loaded. Provider: {config.LLM_PROVIDER}, Model: {config.MODEL_NAME}")
