import os
from langchain_core.documents import Document
from langchain_community.vectorstores import FAISS
from langchain_huggingface import HuggingFaceEmbeddings
from utils.config import config
from utils.logger import logger

class MeetingMemoryDB:
    def __init__(self, model_name: str = config.EMBEDDING_MODEL_NAME, save_path: str = config.FAISS_PATH):
        self.save_path = save_path
        logger.info(f"Initializing HuggingFace Embeddings with model: {model_name}")
        self.embeddings = HuggingFaceEmbeddings(model_name=model_name)
        self.db = None
        self.load_or_create_db()

    def load_or_create_db(self):
        """Loads index from disk, or initializes an empty FAISS vectorstore."""
        index_file = os.path.join(self.save_path, "index.faiss")
        if os.path.exists(index_file):
            try:
                logger.info(f"Loading existing FAISS index from {self.save_path}")
                self.db = FAISS.load_local(self.save_path, self.embeddings, allow_dangerous_deserialization=True)
            except Exception as e:
                logger.error(f"Error loading FAISS database: {e}. Re-initializing database.")
                self.db = None
                
        if self.db is None:
            logger.info("Initializing a new empty FAISS database.")
            # We seed it with a welcome document because FAISS needs at least one document to initialize
            initial_doc = Document(
                page_content="Meeting memory initialized. This system stores meeting schedules and histories.",
                metadata={"title": "System Initialization", "type": "system"}
            )
            self.db = FAISS.from_documents([initial_doc], self.embeddings)
            self.save_db()

    def save_db(self):
        """Saves current FAISS index to the configured directory path."""
        try:
            self.db.save_local(self.save_path)
            logger.info(f"FAISS database saved to {self.save_path}")
        except Exception as e:
            logger.error(f"Failed to save FAISS database: {e}")

    def add_meeting_to_memory(self, meeting_id: int, title: str, date: str, start_time: str, duration_mins: int, description: str, participants: list):
        """Formats and indexes a scheduled meeting in FAISS for future semantic search."""
        participants_str = ", ".join(participants)
        content = (
            f"Meeting ID: {meeting_id}\n"
            f"Title: {title}\n"
            f"Date: {date}\n"
            f"Time: {start_time} (Duration: {duration_mins} mins)\n"
            f"Participants: {participants_str}\n"
            f"Description/Agenda: {description}"
        )
        
        doc = Document(
            page_content=content,
            metadata={
                "meeting_id": meeting_id,
                "title": title,
                "date": date,
                "participants": participants_str
            }
        )
        
        logger.info(f"Adding meeting summary of ID {meeting_id} to FAISS index...")
        self.db.add_documents([doc])
        self.save_db()

    def search_memory(self, query: str, k: int = 4) -> list:
        """Performs semantic similarity search on meeting memory and returns matching records."""
        if not self.db:
            return []
            
        logger.info(f"Searching meeting memory for query: '{query}'")
        try:
            results = self.db.similarity_search(query, k=k)
            # Filter out system initialization message
            filtered_results = [
                doc for doc in results 
                if doc.metadata.get("type") != "system"
            ]
            return filtered_results
        except Exception as e:
            logger.error(f"FAISS semantic search failed: {e}")
            return []

# Instantiate memory database
memory_db = MeetingMemoryDB()
