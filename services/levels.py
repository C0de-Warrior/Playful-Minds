import os
import sqlite3
import datetime

# Define the database file – should be the same as used elsewhere.
DB_FILE = os.path.join(os.getcwd(), "../playful_minds.db")

def _create_connection():
    """Create and return a connection to the SQLite database."""
    try:
        conn = sqlite3.connect(DB_FILE)
        return conn
    except Exception as e:
        print(f"Error connecting to database: {e}")
    return None

def initialize_progress_table():
    """
    Create the PlayerProgress table if it does not exist.
    This table tracks the level and accumulated points for each user and game.
    """
    conn = _create_connection()
    if conn:
        try:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS PlayerProgress (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    game_id TEXT NOT NULL,
                    level INTEGER DEFAULT 0,
                    points INTEGER DEFAULT 0,
                    updated_at TEXT NOT NULL,
                    UNIQUE(user_id, game_id),
                    FOREIGN KEY(user_id) REFERENCES users(id)
                )
            """)
            conn.commit()
        except Exception as e:
            print(f"Error initializing PlayerProgress table: {e}")
        finally:
            conn.close()

def get_required_points(current_level):
    """
    Returns the required points for a player to level up from the current level.
    - For level 0: 10 points.
    - For levels 1 to 10: 20 points each.
    - For levels 11 to 20: 30 points each.
    - And so on: for every 10 levels, the threshold increases by 10.
    """
    if current_level == 0:
        return 10
    else:
        # Calculate group: levels 1-10 are group 1, 11-20 group 2, etc.
        group = ((current_level - 1) // 10) + 1
        return 10 + (group * 10)

def get_player_progress(user_id, game_id):
    """
    Retrieves the current progress for the specified user and game.
    Returns a dictionary: { "level": int, "points": int }.
    If no record exists, returns None.
    """
    conn = _create_connection()
    progress = None
    if conn:
        try:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT level, points FROM PlayerProgress
                WHERE user_id = ? AND game_id = ?
            """, (user_id, game_id))
            row = cursor.fetchone()
            if row:
                progress = {"level": row[0], "points": row[1]}
        except Exception as e:
            print(f"Error fetching progress for user {user_id}, game {game_id}: {e}")
        finally:
            conn.close()
    return progress

def init_player_progress(user_id, game_id):
    """
    Ensures a progress record exists for the user and game.
    If not, creates one with level 0 and 0 points.
    """
    if get_player_progress(user_id, game_id) is None:
        conn = _create_connection()
        if conn:
            try:
                now = datetime.datetime.now().isoformat()
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO PlayerProgress (user_id, game_id, level, points, updated_at)
                    VALUES (?, ?, 0, 0, ?)
                """, (user_id, game_id, now))
                conn.commit()
            except Exception as e:
                print(f"Error initializing progress for user {user_id}, game {game_id}: {e}")
            finally:
                conn.close()

def update_player_progress(user_id, game_id, additional_points):
    """
    Updates the player's progress by adding additional_points.
    This function will:
      - Initialize the progress record if it doesn't exist.
      - Add the points to the current total.
      - Check if the points meet or exceed the required threshold(s).
      - Increase the level accordingly and subtract the used points.
      - Update the record and return the updated progress.
    Returns a dictionary: { "level": int, "points": int }.
    """
    init_player_progress(user_id, game_id)
    progress = get_player_progress(user_id, game_id)
    if progress is None:
        return None  # Should not happen since we just initialized it.
    new_points = progress["points"] + additional_points
    current_level = progress["level"]
    required = get_required_points(current_level)
    # Loop to handle the case where multiple levels can be gained.
    while new_points >= required:
        new_points -= required
        current_level += 1
        required = get_required_points(current_level)
    # Update the DB with new level and points.
    conn = _create_connection()
    if conn:
        try:
            now = datetime.datetime.now().isoformat()
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE PlayerProgress
                SET level = ?, points = ?, updated_at = ?
                WHERE user_id = ? AND game_id = ?
            """, (current_level, new_points, now, user_id, game_id))
            conn.commit()
        except Exception as e:
            print(f"Error updating progress for user {user_id}, game {game_id}: {e}")
        finally:
            conn.close()
    return {"level": current_level, "points": new_points}

# In levels.py add:

def get_average_level_gain():
    conn = _create_connection()
    avg_level = 0
    if conn:
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT AVG(level_count) FROM PlayerProgress")
            avg_level = cursor.fetchone()[0] or 0
        except Exception as e:
            print(f"Error getting average level: {e}")
        finally:
            conn.close()
    return round(avg_level, 1)