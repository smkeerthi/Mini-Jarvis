"""
=============================================================================
MINI JARVIS - Persistent Memory Module (database.py)
=============================================================================
This module handles all persistent storage using Python's built-in SQLite3.

Computer Science Concepts Explained:
1. Relational Database (RDBMS):
   A structured way to store data in tables with rows (records) and
   columns (attributes). SQLite is serverless, zero-configuration, and stores
   the entire database in a single `.db` file on your disk.

2. CRUD Operations:
   - Create: INSERT new notes, to-dos, or chat logs.
   - Read:   SELECT records to retrieve memory and history.
   - Update: UPDATE settings or mark to-dos as completed.
   - Delete: DELETE records when no longer needed.

3. Concurrency & Thread Safety:
   In desktop assistants, background audio threads and UI threads might both
   need the database. We open a fresh connection per operation or use
   proper connection scoping with `sqlite3.connect(..., check_same_thread=False)`.
=============================================================================
"""

import sqlite3
import datetime
from typing import List, Dict, Any, Optional
from config import DB_PATH, DEFAULT_USER_NAME, DEFAULT_VOICE_RATE, DEFAULT_VOICE_VOLUME, DEFAULT_VOICE_INDEX


class DatabaseManager:
    """Manages SQLite storage for Jarvis's settings, notes, to-dos, and memory."""

    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path
        self.init_database()

    def get_connection(self) -> sqlite3.Connection:
        """
        Creates and returns a thread-safe connection to the SQLite database.
        Row factory is set to sqlite3.Row so we can access columns by name like dicts!
        """
        conn = sqlite3.connect(self.db_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn

    def init_database(self) -> None:
        """
        Creates the necessary tables if they do not already exist.
        This runs automatically when Jarvis boots up.
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()

            # 1. Key-Value Settings table (User Name, Voice preferences, etc.)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS settings (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                )
            """)

            # 2. Conversation History table (Chat logs for memory & context)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS conversation_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    sender TEXT NOT NULL,
                    message TEXT NOT NULL,
                    timestamp TEXT NOT NULL
                )
            """)

            # 3. Notes table (Quick saved thoughts, code snippets, reminders)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS notes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    content TEXT NOT NULL,
                    timestamp TEXT NOT NULL
                )
            """)

            # 4. To-Do List table (Tasks with status)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS todos (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    task TEXT NOT NULL,
                    is_completed INTEGER DEFAULT 0,
                    created_at TEXT NOT NULL
                )
            """)

            # Seed default settings if they are not already set
            defaults = {
                "user_name": DEFAULT_USER_NAME,
                "voice_rate": str(DEFAULT_VOICE_RATE),
                "voice_volume": str(DEFAULT_VOICE_VOLUME),
                "voice_index": str(DEFAULT_VOICE_INDEX),
            }
            for key, val in defaults.items():
                cursor.execute(
                    "INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)",
                    (key, val)
                )

            conn.commit()

    # -----------------------------------------------------------------------
    # SETTINGS & USER PROFILE METHODS
    # -----------------------------------------------------------------------
    def get_setting(self, key: str, default: Optional[str] = None) -> Optional[str]:
        """Fetch a single setting value by its key."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT value FROM settings WHERE key = ?", (key,))
            row = cursor.fetchone()
            return row["value"] if row else default

    def set_setting(self, key: str, value: Any) -> None:
        """Insert or update a setting value."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO settings (key, value) VALUES (?, ?) "
                "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
                (key, str(value))
            )
            conn.commit()

    def get_user_name(self) -> str:
        """Get the user's preferred name."""
        return self.get_setting("user_name", DEFAULT_USER_NAME) or DEFAULT_USER_NAME

    def set_user_name(self, name: str) -> None:
        """Update the user's preferred name."""
        self.set_setting("user_name", name.strip())

    # -----------------------------------------------------------------------
    # CONVERSATION MEMORY METHODS
    # -----------------------------------------------------------------------
    def add_conversation(self, sender: str, message: str) -> None:
        """
        Record a single utterance (either from 'user' or 'jarvis')
        into persistent memory with current ISO timestamp.
        """
        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO conversation_history (sender, message, timestamp) VALUES (?, ?, ?)",
                (sender, message, now)
            )
            conn.commit()

    def get_recent_conversations(self, limit: int = 15) -> List[Dict[str, Any]]:
        """
        Retrieve recent messages ordered from oldest to newest.
        Used to feed context into the AI brain.
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT id, sender, message, timestamp FROM conversation_history "
                "ORDER BY id DESC LIMIT ?",
                (limit,)
            )
            rows = cursor.fetchall()
            # Reverse so the dialogue flows chronologically
            return [dict(row) for row in reversed(rows)]

    def clear_conversation_history(self) -> None:
        """Wipe all past conversation records."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM conversation_history")
            conn.commit()

    # -----------------------------------------------------------------------
    # NOTES METHODS
    # -----------------------------------------------------------------------
    def add_note(self, content: str, title: str = "Quick Note") -> int:
        """Save a new note and return its generated ID."""
        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO notes (title, content, timestamp) VALUES (?, ?, ?)",
                (title.strip(), content.strip(), now)
            )
            conn.commit()
            return cursor.lastrowid

    def get_all_notes(self) -> List[Dict[str, Any]]:
        """Retrieve all notes, newest first."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id, title, content, timestamp FROM notes ORDER BY id DESC")
            return [dict(row) for row in cursor.fetchall()]

    def delete_note(self, note_id: int) -> bool:
        """Delete a specific note by ID."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM notes WHERE id = ?", (note_id,))
            conn.commit()
            return cursor.rowcount > 0

    def clear_all_notes(self) -> None:
        """Delete all saved notes."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM notes")
            conn.commit()

    # -----------------------------------------------------------------------
    # TO-DO LIST METHODS
    # -----------------------------------------------------------------------
    def add_todo(self, task: str) -> int:
        """Add a new pending task to the to-do list."""
        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO todos (task, is_completed, created_at) VALUES (?, 0, ?)",
                (task.strip(), now)
            )
            conn.commit()
            return cursor.lastrowid

    def get_all_todos(self) -> List[Dict[str, Any]]:
        """Get all to-do items ordered by completion status then creation date."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT id, task, is_completed, created_at FROM todos ORDER BY is_completed ASC, id DESC"
            )
            return [dict(row) for row in cursor.fetchall()]

    def toggle_todo(self, todo_id: int) -> bool:
        """Toggle a task between completed (1) and incomplete (0)."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE todos SET is_completed = CASE WHEN is_completed = 1 THEN 0 ELSE 1 END WHERE id = ?",
                (todo_id,)
            )
            conn.commit()
            return cursor.rowcount > 0

    def delete_todo(self, todo_id: int) -> bool:
        """Remove a to-do item by its ID."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM todos WHERE id = ?", (todo_id,))
            conn.commit()
            return cursor.rowcount > 0

    def clear_all_todos(self) -> None:
        """Wipe all to-dos."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM todos")
            conn.commit()


# Singleton instance for simple direct access across modules
db = DatabaseManager()
