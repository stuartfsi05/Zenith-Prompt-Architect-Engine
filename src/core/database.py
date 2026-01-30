import json
import os
import sqlite3
from datetime import datetime
from typing import Any, Dict, List, Optional

from src.core.config import Config
from src.utils.logger import setup_logger

logger = setup_logger("DatabaseManager")


class DatabaseManager:
    """
    Manages SQLite storage for sessions and interactions.
    """

    def __init__(self, config: Config):
        self.config = config
        self.db_path = os.path.join(os.getcwd(), "data", "zenith.db")
        self._ensure_data_dir()
        self._create_tables()

    def _ensure_data_dir(self):
        """Ensures data directory exists."""
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)

    def _get_connection(self) -> sqlite3.Connection:
        """Returns a new database connection."""
        return sqlite3.connect(self.db_path)

    def _create_tables(self):
        """Creates the necessary tables if they don't exist."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()

                # Table: Interactions
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS interactions (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        session_id TEXT NOT NULL,
                        role TEXT NOT NULL,
                        content TEXT NOT NULL,
                        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                        metadata TEXT
                    )
                """
                )

                # Table: Sessions
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS sessions (
                        id TEXT PRIMARY KEY,
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                        last_active DATETIME DEFAULT CURRENT_TIMESTAMP
                    )
                """
                )

                conn.commit()
        except Exception as e:
            logger.critical(f"Database Initialization Failed: {e}")

    def create_session(self, session_id: str):
        """Registers a new session or updates last_active if exists."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    INSERT INTO sessions (id, created_at, last_active)
                    VALUES (?, ?, ?)
                    ON CONFLICT(id)
                    DO UPDATE SET last_active = excluded.last_active
                """,
                    (session_id, datetime.now(), datetime.now()),
                )
                conn.commit()
        except Exception as e:
            logger.error(f"Failed to create/update session: {e}")

    def log_interaction(
        self, session_id: str, role: str, content: str, metadata: Optional[Dict] = None
    ):
        """Logs a single turn (User or Model) to the database."""
        try:
            meta_json = json.dumps(metadata) if metadata else "{}"
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    INSERT INTO interactions
                    (session_id, role, content, timestamp, metadata)
                    VALUES (?, ?, ?, ?, ?)
                """,
                    (session_id, role, content, datetime.now(), meta_json),
                )

                cursor.execute(
                    "UPDATE sessions SET last_active = ? WHERE id = ?",
                    (datetime.now(), session_id),
                )

                conn.commit()
        except Exception as e:
            logger.error(f"Failed to log interaction: {e}")

    def get_history(self, session_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        """
        Retrieves the chat history for a session.
        """
        history = []
        try:
            with self._get_connection() as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                cursor.execute(
                    """
                    SELECT role, content, metadata
                    FROM interactions
                    WHERE session_id = ?
                    ORDER BY id ASC
                    LIMIT ?
                """,
                    (session_id, limit),
                )

                rows = cursor.fetchall()
                for row in rows:
                    history.append(
                        {
                            "role": row["role"],
                            "parts": [row["content"]],
                            "metadata": (
                                json.loads(row["metadata"]) if row["metadata"] else {}
                            ),
                        }
                    )
        except Exception as e:
            logger.error(f"Failed to retrieve history: {e}")

        return history

    def get_analytics_summary(self) -> Dict[str, Any]:
        """Returns basic stats about usage."""
        stats = {}
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT COUNT(*) FROM interactions")
                stats["total_interactions"] = cursor.fetchone()[0]

                cursor.execute("SELECT COUNT(DISTINCT session_id) FROM sessions")
                stats["total_sessions"] = cursor.fetchone()[0]
        except Exception as e:
            logger.error(f"Analytics failure: {e}")
        return stats
