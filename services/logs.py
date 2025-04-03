import sqlite3
import os
import datetime

DB_FILE = os.path.join(os.getcwd(), "playful_minds.db")


def _create_connection():
    """Create a database connection to the SQLite database."""
    conn = None
    try:
        conn = sqlite3.connect(DB_FILE)
        return conn
    except Exception as e:
        print(f"Error connecting to database: {e}")
    return conn


def initialize_logs_table():
    """
    Create the Logs table if it does not exist.
    This table records user interactions, including login, logout, game actions, admin actions, and guest activity.
    """
    conn = _create_connection()
    if conn:
        try:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS Logs (
                    log_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    action TEXT NOT NULL,
                    details TEXT,
                    timestamp TEXT NOT NULL,
                    FOREIGN KEY(user_id) REFERENCES users(id)
                )
            """)
            conn.commit()
        except Exception as e:
            print(f"Error initializing Logs table: {e}")
        finally:
            conn.close()


def log_event(user_id, action, details=""):
    """
    Record an event in the Logs table.

    Parameters:
        user_id (int or None): The ID of the user performing the action (can be NULL for guest actions).
        action (str): A short description of the event (e.g., "login", "game_start", "report_generated").
        details (str): Optional additional information about the event.
    """
    conn = _create_connection()
    if conn:
        try:
            now = datetime.datetime.now().isoformat()
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO Logs (user_id, action, details, timestamp)
                VALUES (?, ?, ?, ?)
            """, (user_id, action, details, now))
            conn.commit()
        except Exception as e:
            print(f"Error logging event: {e}")
        finally:
            conn.close()


def get_logs(limit=50):
    """
    Retrieve the most recent logs (default limit is 50).

    Returns:
        List of dictionaries, each representing a log record.
    """
    logs = []
    conn = _create_connection()
    if conn:
        try:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT log_id, user_id, action, details, timestamp
                FROM Logs
                ORDER BY timestamp DESC
                LIMIT ?
            """, (limit,))
            rows = cursor.fetchall()
            for row in rows:
                logs.append({
                    "log_id": row[0],
                    "user_id": row[1],
                    "action": row[2],
                    "details": row[3],
                    "timestamp": row[4]
                })
        except Exception as e:
            print(f"Error retrieving logs: {e}")
        finally:
            conn.close()
    return logs


# Initialize the Logs table on module load
initialize_logs_table()
