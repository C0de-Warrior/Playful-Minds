import sqlite3
import os
import datetime

# -------------------- Configuration --------------------
DB_FILE = os.path.join(os.getcwd(), "playful_minds.db")

def _create_connection():
    """Create a database connection to a SQLite database."""
    conn = None
    try:
        conn = sqlite3.connect(DB_FILE)
        return conn
    except Exception as e:
        print(f"Error connecting to database: {e}")
    return conn

def initialize_database():
    """Initialize the database with the necessary tables."""
    conn = _create_connection()
    if conn is not None:
        try:
            cursor = conn.cursor()
            # Create users table with the improved data model
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    firstName TEXT NOT NULL,
                    lastName TEXT NOT NULL,
                    userName TEXT NOT NULL UNIQUE,
                    role TEXT NOT NULL,
                    password TEXT NOT NULL,
                    email TEXT NOT NULL UNIQUE,
                    creationDate TEXT NOT NULL
                )
            """)
            # Create highscores table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS highscores (
                    game_id TEXT NOT NULL,
                    name TEXT NOT NULL,
                    score INTEGER NOT NULL,
                    FOREIGN KEY (game_id) REFERENCES games(game_id)
                )
            """)
            # Create games table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS games (
                    game_id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    file_path TEXT NOT NULL,
                    description TEXT
                )
            """)
            # Create GameSessions table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS GameSessions (
                    session_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    game_id TEXT NOT NULL,
                    start_time TEXT NOT NULL,
                    end_time TEXT,
                    session_type TEXT,
                    level INTEGER DEFAULT 1,
                    FOREIGN KEY (user_id) REFERENCES users(id)
                )
            """)
            # Create UserSessions table (for login sessions)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS UserSessions (
                    session_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    login_time TEXT NOT NULL,
                    last_active TEXT NOT NULL,
                    logout_time TEXT,
                    session_type TEXT,
                    FOREIGN KEY(user_id) REFERENCES users(id)
                )
            """)
            # Create the PlayerProgress table
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




            # Create PlayerLevels table to track cumulative level count for each game per player.
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS PlayerLevels (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    game_id TEXT NOT NULL,
                    level_count INTEGER DEFAULT 0,
                    updated_at TEXT NOT NULL,
                    UNIQUE(user_id, game_id),
                    FOREIGN KEY (user_id) REFERENCES users(id)
                )
            """)
            conn.commit()
            print("Database initialized.")
        except Exception as e:
            print(f"Error initializing database: {e}")
        finally:
            conn.close()

def load_user_by_username(userName):
    """Load a single user by userName from the database."""
    conn = _create_connection()
    if conn is not None:
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM users WHERE userName = ?", (userName,))
            row = cursor.fetchone()
            if row:
                user = {
                    "id": row[0],
                    "firstName": row[1],
                    "lastName": row[2],
                    "userName": row[3],
                    "role": row[4],
                    "password": row[5],
                    "email": row[6],
                    "creationDate": row[7],
                }
                return user
            return None
        except Exception as e:
            print(f"Error loading user: {e}")
            return None
        finally:
            conn.close()

def save_user(firstName, lastName, userName, role, password, email, creationDate):
    """Save a new user to the database using the improved data model."""
    conn = _create_connection()
    if conn is not None:
        try:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO users (firstName, lastName, userName, role, password, email, creationDate)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (firstName, lastName, userName, role, password, email, creationDate))
            conn.commit()
            print("User saved successfully.")
        except Exception as e:
            print(f"Error saving user: {e}")
        finally:
            conn.close()

def load_accounts():
    """
    Load all user accounts from the database.
    Returns a dictionary with userName as key and a dictionary of user details as value.
    """
    accounts = {}
    conn = _create_connection()
    if conn is not None:
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT firstName, lastName, userName, role, password, email, creationDate, id FROM users")
            rows = cursor.fetchall()
            for row in rows:
                accounts[row[2]] = {
                    "firstName": row[0],
                    "lastName": row[1],
                    "role": row[3],
                    "password": row[4],
                    "email": row[5],
                    "creationDate": row[6],
                    "id": row[7]
                }
        except Exception as e:
            print(f"Error loading accounts: {e}")
        finally:
            conn.close()
    return accounts

def save_accounts(accounts):
    """
    Save multiple user accounts to the database.
    Expects 'accounts' to be a dictionary with userName as key and a dictionary containing
    firstName, lastName, role, password, email, and creationDate as value.
    """
    conn = _create_connection()
    if conn is not None:
        try:
            cursor = conn.cursor()
            # For simplicity, clear existing accounts (not recommended in production)
            cursor.execute("DELETE FROM users")
            for userName, details in accounts.items():
                cursor.execute("""
                    INSERT INTO users (firstName, lastName, userName, role, password, email, creationDate)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    details.get("firstName", ""),
                    details.get("lastName", ""),
                    userName,
                    details.get("role", "player"),
                    details.get("password", ""),
                    details.get("email", ""),
                    details.get("creationDate", datetime.datetime.now().isoformat())
                ))
            conn.commit()
            print("Accounts updated successfully.")
        except Exception as e:
            print(f"Error saving accounts: {e}")
        finally:
            conn.close()

def delete_user(user_id):
    """Delete a user from the database by their user_id."""
    conn = _create_connection()
    if conn is not None:
        try:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM users WHERE id = ?", (user_id,))
            conn.commit()
            print(f"User with id {user_id} deleted.")
        except Exception as e:
            print(f"Error deleting user: {e}")
        finally:
            conn.close()

def update_user(user_id, firstName, lastName, userName, role, email):
    """Update a user record with new information."""
    conn = _create_connection()
    if conn is not None:
        try:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE users
                SET firstName = ?, lastName = ?, userName = ?, role = ?, email = ?
                WHERE id = ?
            """, (firstName, lastName, userName, role, email, user_id))
            conn.commit()
            print(f"User with id {user_id} updated.")
        except Exception as e:
            print(f"Error updating user: {e}")
        finally:
            conn.close()

def get_user_by_id(user_id):
    """Retrieve a user from the database by their user_id."""
    conn = _create_connection()
    if conn is not None:
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
            row = cursor.fetchone()
            if row:
                user = {
                    "id": row[0],
                    "firstName": row[1],
                    "lastName": row[2],
                    "userName": row[3],
                    "role": row[4],
                    "password": row[5],
                    "email": row[6],
                    "creationDate": row[7],
                }
                return user
            return None
        except Exception as e:
            print(f"Error getting user by id: {e}")
            return None
        finally:
            conn.close()

def load_highscores(game_id):
    """Load highscores for a specific game from the database."""
    conn = _create_connection()
    if conn is not None:
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT name, score FROM highscores WHERE game_id = ?", (game_id,))
            rows = cursor.fetchall()
            highscores = [{"name": row[0], "score": row[1]} for row in rows]
            return highscores
        except Exception as e:
            print(f"Error loading highscores: {e}")
            return []
        finally:
            conn.close()
    return []

def save_highscores(game_id, highscores):
    """Save highscores for a specific game to the database."""
    conn = _create_connection()
    if conn is not None:
        try:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM highscores WHERE game_id = ?", (game_id,))
            for entry in highscores:
                cursor.execute("INSERT INTO highscores (game_id, name, score) VALUES (?, ?, ?)",
                               (game_id, entry["name"], entry["score"]))
            conn.commit()
            print("Highscores updated.")
        except Exception as e:
            print(f"Error saving highscores: {e}")
        finally:
            conn.close()

def load_games():
    """Load game details from the database."""
    conn = _create_connection()
    if conn is not None:
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT game_id, title, file_path, description FROM games")
            rows = cursor.fetchall()
            games = []
            for row in rows:
                games.append({
                    "game_id": row[0],
                    "title": row[1],
                    "file": row[2],
                    "description": row[3]
                })
            return games
        except Exception as e:
            print(f"Error loading games: {e}")
            return []
        finally:
            conn.close()
    return []

def save_games(games):
    """Save game details to the database."""
    conn = _create_connection()
    if conn is not None:
        try:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM games")  # Clear existing data
            for game in games:
                cursor.execute("INSERT INTO games (game_id, title, file_path, description) VALUES (?, ?, ?, ?)",
                               (game["game_id"], game["title"], game["file"], game["description"]))
            conn.commit()
            print("Games updated.")
        except Exception as e:
            print(f"Error saving games: {e}")
        finally:
            conn.close()

def load_sessions_by_user(user_id):
    """
    Load all game sessions for a specific user.
    Returns a list of session dictionaries.
    """
    sessions = []
    conn = _create_connection()
    if conn is not None:
        try:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT session_id, game_id, start_time, end_time, session_type, level
                FROM GameSessions
                WHERE user_id = ?
            """, (user_id,))
            rows = cursor.fetchall()
            for row in rows:
                sessions.append({
                    "session_id": row[0],
                    "game_id": row[1],
                    "start_time": row[2],
                    "end_time": row[3],
                    "session_type": row[4],
                    "level": row[5]
                })
        except Exception as e:
            print(f"Error loading sessions for user {user_id}: {e}")
        finally:
            conn.close()
    return sessions

def load_overall_session_stats():
    """
    Compute overall session statistics such as total play time and average level per game.
    Returns a dictionary with the computed statistics.
    Note: Assumes 'start_time' and 'end_time' are stored as ISO strings.
    """
    stats = {"total_play_time": 0, "average_level_per_game": {}}
    conn = _create_connection()
    if conn is not None:
        try:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT game_id, start_time, end_time, level
                FROM GameSessions
                WHERE end_time IS NOT NULL
            """)
            rows = cursor.fetchall()
            game_levels = {}
            for game_id, start_time, end_time, level in rows:
                start_dt = datetime.datetime.fromisoformat(start_time)
                end_dt = datetime.datetime.fromisoformat(end_time)
                duration = (end_dt - start_dt).total_seconds() / 60  # minutes
                stats["total_play_time"] += duration
                if game_id not in game_levels:
                    game_levels[game_id] = []
                game_levels[game_id].append(level)
            for game_id, levels_list in game_levels.items():
                avg_level = sum(levels_list) / len(levels_list)
                stats["average_level_per_game"][game_id] = avg_level
        except Exception as e:
            print(f"Error computing session statistics: {e}")
        finally:
            conn.close()
    return stats

# -------------------- New Functions for Player Level Management --------------------
def get_all_player_progress():
    conn = sqlite3.connect("playful_minds.db")
    cursor = conn.cursor()
    cursor.execute("SELECT user_id, game_id, level, points, updated_at FROM PlayerProgress")
    rows = cursor.fetchall()
    conn.close()
    # Create a list of dicts for each progress entry.
    progress_list = [
        {"user_id": row[0], "game_id": row[1], "level": row[2], "points": row[3], "updated_at": row[4]}
        for row in rows
    ]
    return progress_list

def get_player_level(user_id, game_id):
    """
    Get the current cumulative level count for a specific user and game.
    Returns the level_count (integer) or 0 if not found.
    """
    conn = _create_connection()
    level_count = 0
    if conn is not None:
        try:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT level_count FROM PlayerLevels
                WHERE user_id = ? AND game_id = ?
            """, (user_id, game_id))
            row = cursor.fetchone()
            if row:
                level_count = row[0]
        except Exception as e:
            print(f"Error fetching player level for user {user_id}, game {game_id}: {e}")
        finally:
            conn.close()
    return level_count

def update_player_level(user_id, game_id, additional_levels):
    """
    Update the cumulative level count for a user and game.
    If no record exists, create one starting with additional_levels.
    Otherwise, add additional_levels to the current level count.
    """
    conn = _create_connection()
    if conn is not None:
        try:
            current_level = get_player_level(user_id, game_id)
            new_level = current_level + additional_levels
            now = datetime.datetime.now().isoformat()
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE PlayerLevels
                SET level_count = ?, updated_at = ?
                WHERE user_id = ? AND game_id = ?
            """, (new_level, now, user_id, game_id))
            if cursor.rowcount == 0:
                cursor.execute("""
                    INSERT INTO PlayerLevels (user_id, game_id, level_count, updated_at)
                    VALUES (?, ?, ?, ?)
                """, (user_id, game_id, additional_levels, now))
            conn.commit()
            print(f"Updated player level for user {user_id} in game {game_id} to {new_level}")
        except Exception as e:
            print(f"Error updating player level for user {user_id}, game {game_id}: {e}")
        finally:
            conn.close()
    return

if __name__ == "__main__":
    initialize_database()
