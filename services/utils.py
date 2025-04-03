import os
import subprocess
import sys
import re
import json

# -------------------- Configuration --------------------
CONFIG_DIR = os.path.join(os.getcwd(), "config")
CONFIG_PATH = os.path.join(CONFIG_DIR, "settings.json")

def load_camera_index():
    """Load camera index from config."""
    if not os.path.exists(CONFIG_DIR):
        os.makedirs(CONFIG_DIR)
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, "r") as f:
                content = f.read().strip()
                if not content:
                    raise ValueError("Empty config file")
                config = json.loads(content)
                return config.get("camera_index", 0)
        except Exception as e:
            print(f"Error loading config: {e}. Initializing with default settings.")
            save_camera_index(0)
            return 0
    else:
        save_camera_index(0)
        return 0

def save_camera_index(index):
    """Save camera index to config."""
    if not os.path.exists(CONFIG_DIR):
        os.makedirs(CONFIG_DIR)
    with open(CONFIG_PATH, "w") as f:
        json.dump({"camera_index": index}, f)
    print(f"Camera index set to: {index}")

def launch_game(game_file: str):
    """Launch a game located in the 'games' folder."""
    game_path = os.path.join(os.getcwd(), "games", game_file)
    try:
        if os.path.exists(game_path):
            subprocess.Popen([sys.executable, game_path])
        else:
            print(f"Game file {game_path} not found.")
    except Exception as e:
        print(f"Error launching game {game_file}: {e}")

def is_strong_password(pw: str) -> bool:
    """
    Validate that the password is strong.
    A strong password has at least 8 characters, one lowercase, one uppercase,
    one digit, and one special symbol.
    """
    return bool(re.match(r'^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&])[A-Za-z\d@$!%*?&]{8,}$', pw))
