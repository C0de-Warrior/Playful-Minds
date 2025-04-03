import os
import datetime
import json
from plyer import notification

# File to store the last active timestamp.
LAST_ACTIVE_FILE = os.path.join(os.getcwd(), "config", "last_active.json")

def update_last_active():
    """
    Update the last active timestamp in the config file.
    Call this function whenever the app is opened or a user interacts.
    """
    now = datetime.datetime.now().isoformat()
    os.makedirs(os.path.dirname(LAST_ACTIVE_FILE), exist_ok=True)
    data = {"last_active": now}
    with open(LAST_ACTIVE_FILE, "w") as f:
        json.dump(data, f)

def check_inactivity_and_notify():
    """
    Checks if 24 hours have passed since the last recorded activity.
    If so, sends a push notification with a creative message.
    """
    try:
        with open(LAST_ACTIVE_FILE, "r") as f:
            data = json.load(f)
        last_active = datetime.datetime.fromisoformat(data.get("last_active"))
    except Exception:
        # If the file doesn't exist or cannot be read, assume current time.
        last_active = datetime.datetime.now()

    now = datetime.datetime.now()
    elapsed_seconds = (now - last_active).total_seconds()

    if elapsed_seconds >= 24 * 3600:
        # 24 hours have passed without activity.
        send_push_notification("Playful Minds misses you! Come back and play today!")
    # Optionally, you could add further scheduling or additional reminders.

def send_push_notification(message):
    """
    Sends a local push notification with the given message.
    Make sure plyer is installed: pip install plyer
    """
    notification.notify(
        title="Playful Minds",
        message=message,
        app_name="Playful Minds App",
        timeout=10  # Notification stays for 10 seconds
    )
