import os
import sqlite3
import csv
from datetime import datetime, timedelta
from typing import List, Dict, Any, Tuple
from utils.config import config
from utils.logger import logger
from utils.helpers import is_overlapping, calculate_end_time, normalize_participants

class SchedulerDB:
    def __init__(self, db_path: str = config.DB_PATH):
        self.db_path = db_path
        self.init_db()

    def _get_connection(self):
        """Returns a connection to the SQLite database."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def init_db(self):
        """Initializes tables and seeds sample data."""
        logger.info(f"Initializing SQLite database at: {self.db_path}")
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # Create participants table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS participants (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    email TEXT UNIQUE NOT NULL
                )
            """)

            # Create meetings table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS meetings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    date TEXT NOT NULL,
                    start_time TEXT NOT NULL,
                    end_time TEXT NOT NULL,
                    duration_mins INTEGER NOT NULL,
                    description TEXT,
                    participants_list TEXT NOT NULL  -- Semicolon-separated list of emails
                )
            """)

            # Create reminders table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS reminders (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    meeting_id INTEGER,
                    participant_email TEXT NOT NULL,
                    trigger_time TEXT NOT NULL,
                    status TEXT NOT NULL,  -- PENDING, SENT, FAILED
                    text TEXT NOT NULL,
                    FOREIGN KEY (meeting_id) REFERENCES meetings(id) ON DELETE CASCADE
                )
            """)
            conn.commit()

        # Seed initial participants and check for sample meetings
        self.seed_participants()
        self.seed_sample_meetings()

    def seed_participants(self):
        """Seeds default participants."""
        default_users = [
            ("Alice Smith", "alice@example.com"),
            ("Bob Jones", "bob@example.com"),
            ("Charlie Brown", "charlie@example.com"),
            ("HR Department", "hr@example.com"),
            ("Project Manager", "manager@example.com")
        ]
        
        with self._get_connection() as conn:
            cursor = conn.cursor()
            for name, email in default_users:
                try:
                    cursor.execute(
                        "INSERT OR IGNORE INTO participants (name, email) VALUES (?, ?)",
                        (name, email)
                    )
                except Exception as e:
                    logger.error(f"Error seeding user {name}: {e}")
            conn.commit()

    def seed_sample_meetings(self):
        """Seeds sample meetings from CSV if meetings table is empty."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM meetings")
            count = cursor.fetchone()[0]
            if count > 0:
                logger.info("Meetings table already seeded. Skipping CSV seeding.")
                return

        # Load CSV path
        csv_path = os.path.join(config.BASE_DIR, "data", "sample_meetings.csv")
        if not os.path.exists(csv_path):
            logger.warning(f"Sample CSV not found at {csv_path}. Skipping sample seeding.")
            return

        logger.info(f"Seeding meetings from {csv_path}...")
        try:
            with open(csv_path, mode="r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    title = row["title"]
                    date = row["date"]
                    start_time = row["start_time"]
                    end_time = row["end_time"]
                    participants_str = row["participants_list"]
                    description = row["description"]
                    
                    # Calculate duration
                    try:
                        s_t = datetime.strptime(start_time, "%H:%M")
                        e_t = datetime.strptime(end_time, "%H:%M")
                        duration = int((e_t - s_t).total_seconds() / 60)
                    except Exception:
                        duration = 60

                    self.add_meeting(title, date, start_time, duration, description, participants_str.split(";"))
            logger.info("Sample meetings seeded successfully.")
        except Exception as e:
            logger.error(f"Failed to seed meetings from CSV: {e}")

    def add_meeting(self, title: str, date: str, start_time: str, duration_mins: int, description: str, participants: List[str]) -> int:
        """Adds a meeting and schedules its reminders."""
        end_time = calculate_end_time(start_time, duration_mins)
        participants_str = ";".join(normalize_participants(participants))

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO meetings (title, date, start_time, end_time, duration_mins, description, participants_list)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (title, date, start_time, end_time, duration_mins, description, participants_str)
            )
            meeting_id = cursor.lastrowid
            conn.commit()

        # Add reminders automatically for this meeting
        self.create_reminders_for_meeting(meeting_id, title, date, start_time, participants)
        logger.info(f"Successfully scheduled meeting ID {meeting_id}: '{title}' on {date} at {start_time}")
        return meeting_id

    def create_reminders_for_meeting(self, meeting_id: int, title: str, date: str, start_time: str, participants: List[str]):
        """Generates reminder entries (15 minutes prior) in DB."""
        # Calculate reminder trigger time
        try:
            mtg_dt = datetime.strptime(f"{date} {start_time}", "%Y-%m-%d %H:%M")
            reminder_dt = mtg_dt - timedelta(minutes=15)
            trigger_time_str = reminder_dt.strftime("%Y-%m-%d %H:%M")
        except Exception:
            trigger_time_str = f"{date} {start_time}" # fallback same as meeting time

        with self._get_connection() as conn:
            cursor = conn.cursor()
            for email in normalize_participants(participants):
                text = f"Reminder: You have a meeting '{title}' starting in 15 minutes at {start_time}."
                cursor.execute(
                    """
                    INSERT INTO reminders (meeting_id, participant_email, trigger_time, status, text)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (meeting_id, email, trigger_time_str, "PENDING", text)
                )
            conn.commit()

    def get_meetings(self) -> List[Dict[str, Any]]:
        """Retrieves all scheduled meetings."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM meetings ORDER BY date ASC, start_time ASC")
            rows = cursor.fetchall()
            return [dict(row) for row in rows]

    def get_meetings_for_participant(self, email: str, date: str = None) -> List[Dict[str, Any]]:
        """Retrieves meetings for a specific participant (optionally filtered by date)."""
        sql = "SELECT * FROM meetings WHERE participants_list LIKE ? "
        params = [f"%{email}%"]
        
        if date:
            sql += "AND date = ? "
            params.append(date)
            
        sql += "ORDER BY start_time ASC"
        
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(sql, params)
            rows = cursor.fetchall()
            return [dict(row) for row in rows]

    def check_conflicts(self, date: str, start_time: str, duration_mins: int, participants: List[str]) -> Tuple[bool, List[Dict[str, Any]]]:
        """
        Checks if there are conflicts for any of the participants.
        Returns a tuple: (has_conflict: bool, list_of_conflicting_meetings: list).
        """
        end_time = calculate_end_time(start_time, duration_mins)
        normalized_emails = normalize_participants(participants)
        conflicts = []

        # Find meetings on the same date
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM meetings WHERE date = ?", (date,))
            meetings_on_day = [dict(row) for row in cursor.fetchall()]

        for meeting in meetings_on_day:
            # Check if any participant overlaps
            meeting_participants = meeting["participants_list"].split(";")
            common_participants = set(normalized_emails).intersection(set(meeting_participants))
            
            if common_participants:
                # Check time overlap
                if is_overlapping(start_time, end_time, meeting["start_time"], meeting["end_time"]):
                    conflicts.append(meeting)

        return len(conflicts) > 0, conflicts

    def get_reminders(self) -> List[Dict[str, Any]]:
        """Gets all reminders in the system."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT r.*, m.title as meeting_title 
                FROM reminders r 
                LEFT JOIN meetings m ON r.meeting_id = m.id
                ORDER BY r.trigger_time DESC
                """
            )
            rows = cursor.fetchall()
            return [dict(row) for row in rows]

    def update_reminder_status(self, reminder_id: int, status: str):
        """Updates the status of a reminder (e.g. SENT, FAILED)."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE reminders SET status = ? WHERE id = ?",
                (status, reminder_id)
            )
            conn.commit()

    def get_participant_by_name(self, name: str) -> Dict[str, Any]:
        """Resolves a name to standard participant info."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM participants WHERE name LIKE ?", (f"%{name}%",))
            row = cursor.fetchone()
            return dict(row) if row else {}

# Instantiated single instance database
db = SchedulerDB()
if __name__ == "__main__":
    # Test DB
    meetings = db.get_meetings()
    print(f"Loaded {len(meetings)} meetings.")
