from services.db import _create_connection
import sqlite3
import datetime
import os
from services import db


def start_user_session(user_id, session_type="login"):
    """
    Starts a new user session for admin or player logins.
    Records the login and last_active timestamp.
    """
    conn = _create_connection()
    if conn:
        try:
            now = datetime.datetime.now().isoformat()
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO UserSessions (user_id, login_time, last_active, session_type)
                VALUES (?, ?, ?, ?)
            """, (user_id, now, now, session_type))
            conn.commit()
            session_id = cursor.lastrowid
            return session_id
        except Exception as e:
            print(f"Error starting user session: {e}")
            return None
        finally:
            conn.close()
    return None


def start_game_session(user_id, game_id, session_type, level=1):
    """
    Starts a new game session and returns the session ID.
    The level parameter allows tracking the player's level during the session.
    """
    conn = sqlite3.connect("../playful_minds.db")
    cursor = conn.cursor()
    try:
        start_time = datetime.datetime.now().isoformat()
        cursor.execute(
            "INSERT INTO GameSessions (user_id, game_id, start_time, session_type, level) VALUES (?, ?, ?, ?, ?)",
            (user_id, game_id, start_time, session_type, level),
        )
        conn.commit()
        session_id = cursor.lastrowid
        conn.close()
        return session_id
    except sqlite3.Error as e:
        print(f"Error starting game session: {e}")
        conn.close()
        return None


def end_game_session(session_id, user_id, game_id, level_increment=0):
    """
    Ends a game session by recording the end time.

    Additionally, if the session resulted in an increase in level,
    level_increment (an integer > 0) will be added to the player's overall level
    for the specified game.
    """
    conn = sqlite3.connect("../playful_minds.db")
    cursor = conn.cursor()
    try:
        end_time = datetime.datetime.now().isoformat()
        cursor.execute(
            "UPDATE GameSessions SET end_time = ? WHERE session_id = ?",
            (end_time, session_id),
        )
        conn.commit()
        conn.close()
        # Update player's overall level if there is an increment.
        if level_increment:
            db.update_player_level(user_id, game_id, level_increment)
    except sqlite3.Error as e:
        print(f"Error ending game session: {e}")
        conn.close()
