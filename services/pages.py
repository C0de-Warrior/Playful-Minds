import flet as ft
import os
import bcrypt  # for checking hashed passwords in admin login
import datetime
from services import db, utils, mail, sessions, logs
import json
from services.mail import forgot_password_template
import string
import secrets


# Helper function to generate a strong password.
def back_navigation_view(page: ft.Page, games):
    # Check if current_user exists and is an admin
    if current_user and current_user.get("role", "").lower() == "admin":
        return admin_dashboard_view
    else:
        return landing_view


def select_tab(tabs_obj, index):
    return lambda e: setattr(tabs_obj, "selected_index", index)


def generate_strong_password(length=12):
    characters = string.ascii_letters + string.digits + string.punctuation
    while True:
        password = ''.join(secrets.choice(characters) for _ in range(length))
        if (any(c.islower() for c in password) and
                any(c.isupper() for c in password) and
                any(c.isdigit() for c in password) and
                any(c in string.punctuation for c in password)):
            return password


def exit_application(e):
    # Log the exit action; if no user is logged in, use 0 as the ID.
    user_id = current_user.get("id", 0) if "current_user" in globals() and current_user else 0
    logs.log_event(user_id, "exit", "User exited the application.")
    e.page.window_close()  # Corrected method to close the Flet app.


def save_current_user(user):
    """Persist the current user data to a JSON file.  """
    config_dir = os.path.join(os.getcwd(), "config")
    if not os.path.exists(config_dir):
        os.makedirs(config_dir)
    current_user_path = os.path.join(config_dir, "current_user.json")
    with open(current_user_path, "w") as f:
        json.dump(user, f)


# comment
def clear_current_user():
    """Clear the persisted current user data."""
    current_user_path = os.path.join(os.getcwd(), "config", "current_user.json")
    if os.path.exists(current_user_path):
        os.remove(current_user_path)


# Global current_user variable for session tracking
current_user = None


# -------------------- Landing View --------------------
def landing_view(page: ft.Page, games):
    # Clear existing views.
    page.views.clear()

    # Load accounts from database.
    accounts = db.load_accounts()
    # Check if an admin account exists.
    admin_exists = any(account["role"].lower() == "admin" for account in accounts.values()) if accounts else False

    left_panel_controls = []

    if not admin_exists:
        # No admin account exists: prompt user to create one.
        left_panel_controls.append(
            ft.Text("Welcome! Please create an admin account to get started.", size=18, weight=ft.FontWeight.BOLD,
                    color=ft.Colors.WHITE)
        )
        left_panel_controls.append(ft.Divider(color=ft.Colors.WHITE))
        left_panel_controls.append(
            ft.ListTile(
                leading=ft.Icon(name=ft.icons.PERSON, color=ft.Colors.WHITE),
                title=ft.Text("Create Player Account", color=ft.Colors.WHITE),
                on_click=lambda e: go_to_view(page, create_player_account_view, games)
            )
        )
        left_panel_controls.append(
            ft.ListTile(
                leading=ft.Icon(name=ft.icons.PERSON, color=ft.Colors.WHITE),
                title=ft.Text("Create Admin Account", color=ft.Colors.WHITE),
                on_click=lambda e: go_to_view(page, create_admin_account_view, games)
            )
        )
    else:
        # An admin account exists: show standard login and navigation options.
        left_panel_controls.append(
            ft.ListTile(
                leading=ft.Icon(name=ft.icons.PERSON, color=ft.Colors.WHITE),
                title=ft.Text("Player Login", color=ft.Colors.WHITE),
                on_click=lambda e: go_to_view(page, player_login_view, games)
            )
        )
        left_panel_controls.append(
            ft.ListTile(
                leading=ft.Icon(name=ft.icons.ADMIN_PANEL_SETTINGS, color=ft.Colors.WHITE),
                title=ft.Text("Admin Login", color=ft.Colors.WHITE),
                on_click=lambda e: go_to_view(page, admin_login_view, games)
            )
        )
        left_panel_controls.append(
            ft.ListTile(
                leading=ft.Icon(name=ft.icons.GAMEPAD, color=ft.Colors.WHITE),
                title=ft.Text("Play as Guest", color=ft.Colors.WHITE),
                on_click=lambda e: guest_login(page, games)
            )
        )
        left_panel_controls.append(
            ft.ListTile(
                leading=ft.Icon(name=ft.icons.SETTINGS, color=ft.Colors.WHITE),
                title=ft.Text("Settings", color=ft.Colors.WHITE),
                on_click=lambda e: go_to_view(page, settings_view, games)
            )
        )
        left_panel_controls.append(
            ft.ListTile(
                leading=ft.Icon(name=ft.icons.EXIT_TO_APP, color=ft.Colors.WHITE),
                title=ft.Text("Exit", color=ft.Colors.WHITE),
                on_click=exit_application
            )
        )

    # Left panel container with updated app theme (using purple background).
    left_panel = ft.Container(
        width=300,
        bgcolor=ft.Colors.PURPLE,
        padding=20,
        content=ft.Column(
            left_panel_controls,
            spacing=10,
            alignment=ft.MainAxisAlignment.START,
        ),
    )

    # Right panel: background image plus welcome text and description.
    right_panel = ft.Container(
        expand=True,
        padding=20,
        content=ft.Column(
            [
                ft.Container(
                    content=ft.Image(
                        src="assets/logo.png",  # Replace with your actual image path if needed.
                        width=600,
                        height=350,
                        fit=ft.ImageFit.COVER
                    ),
                ),
                ft.Text("Welcome to Playful Minds!", size=28, weight=ft.FontWeight.BOLD, color=ft.Colors.PURPLE),
                ft.Text(
                    "Playful Minds is a collection of fun, educational games. "
                    "Log in to track your progress, or play as a guest.",
                    size=16,
                    text_align=ft.TextAlign.JUSTIFY,
                    color=ft.Colors.PURPLE
                ),
            ],
            spacing=20,
            alignment=ft.MainAxisAlignment.CENTER,
        ),
    )

    # Overall layout: Row containing left and right panels.
    page.views.append(
        ft.View(
            route="/",
            controls=[
                ft.Row(
                    controls=[left_panel, right_panel],
                    expand=True
                )
            ],
        )
    )
    page.update()


# -------------------- Player Login View --------------------
def player_login_view(page: ft.Page, games):
    def do_login(e):
        username = username_field.value.strip()
        if username == "":
            error_text.value = "Username is required."
            page.update()
            return
        user = db.load_user_by_username(username)
        if user is None or user["role"].lower() != "player":
            error_text.value = "Player account not found."
            page.update()
            return
        global current_user
        current_user = user
        # Save current user info to file for use by game modules.
        save_current_user(user)
        go_to_view(page, game_selection_view, games)

    username_field = ft.TextField(label="Username")
    error_text = ft.Text("", color=ft.Colors.RED)
    page.views.clear()
    page.views.append(
        ft.View(
            route="/player_login",
            controls=[
                ft.Column(
                    [
                        ft.Text("Player Login", size=32, weight=ft.FontWeight.BOLD, color=ft.Colors.PURPLE),
                        username_field,
                        error_text,
                        ft.ElevatedButton("Log In", on_click=do_login),
                        ft.TextButton("Back", on_click=lambda e: go_to_view(page, landing_view, games)),
                    ],
                    alignment=ft.MainAxisAlignment.CENTER,
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    spacing=20,
                )
            ],
        )
    )
    page.update()


# -------------------- Player Log out --------------------
def player_logout(page: ft.Page, games):
    global current_user
    # Log the logout event
    logs.log_event(current_user.get("id", 0), "logout", "Player logged out.")
    current_user = None
    # Clear the persisted user data.
    clear_current_user()
    go_to_view(page, landing_view, games)


# -------------------- Admin Login View --------------------
def admin_login_view(page: ft.Page, games):
    def toggle_password_visibility(field: ft.TextField):
        field.password = not field.password
        new_icon = ft.icons.VISIBILITY_OFF if not field.password else ft.icons.VISIBILITY
        field.suffix = ft.IconButton(icon=new_icon, on_click=lambda e: toggle_password_visibility(field))
        page.update()

    def do_admin_login(e):
        username = admin_username.value.strip()
        pwd = admin_password.value.strip()
        if username == "" or pwd == "":
            error_text.value = "Username and password are required."
            page.update()
            return
        user = db.load_user_by_username(username)
        if user is None or user["role"].lower() != "admin":
            error_text.value = "Admin account not found."
            page.update()
            return
        if bcrypt.checkpw(pwd.encode('utf-8'), user["password"].encode('utf-8')):
            global current_user
            current_user = user
            sessions.start_user_session(user["id"], session_type="admin")
            go_to_view(page, admin_dashboard_view, games)
        else:
            error_text.value = "Incorrect password."
            page.update()

    admin_username = ft.TextField(label="Admin Username")

    admin_password = ft.TextField(
        label="Password",
        password=True,
        suffix=ft.IconButton(icon=ft.icons.VISIBILITY, on_click=lambda e: toggle_password_visibility(admin_password))
    )

    error_text = ft.Text("", color=ft.Colors.RED)

    # "Forgot Password?" button is left-aligned directly below the password field.
    forgot_password_button = ft.TextButton(
        "Forgot Password?",
        on_click=lambda e: go_to_view(page, forgot_password_view, games),
        style=ft.ButtonStyle(
            padding=ft.Padding(0, 0, 0, 0),
            alignment=ft.alignment.center_left
        )
    )

    page.views.clear()
    page.views.append(
        ft.View(
            route="/admin_login",
            controls=[
                ft.Column(
                    [
                        ft.Text("Admin Login", size=32, weight=ft.FontWeight.BOLD, color=ft.Colors.PURPLE),
                        admin_username,
                        admin_password,
                        ft.Row([forgot_password_button], alignment=ft.MainAxisAlignment.START),  # Left-align the button
                        error_text,
                        ft.ElevatedButton("Log In", on_click=do_admin_login),
                        ft.TextButton("Back", on_click=lambda e: go_to_view(page, landing_view, games)),
                    ],
                    alignment=ft.MainAxisAlignment.CENTER,
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    spacing=10,  # Reduced spacing to make the layout compact
                )
            ],
        )
    )
    page.update()


# -------------------- Forgot Password View --------------------
def forgot_password_view(page: ft.Page, games):
    def do_reset_password(e):
        username = username_field.value.strip()
        email = email_field.value.strip()
        if username == "" or email == "":
            error_text.value = "Username and email are required."
            page.update()
            return
        # Verify the account exists and the email matches.
        user = db.load_user_by_username(username)
        if user is None or user.get("email", "").lower() != email.lower():
            error_text.value = "Account not found or email does not match."
            page.update()
            return
        # Generate a new strong password.
        new_password = generate_strong_password()
        # Hash the new password.
        hashed_password = bcrypt.hashpw(new_password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        # Update the admin's password in the database.
        db.update_user_password(user["id"], hashed_password)  # Ensure this function exists in your db module.
        # Send an email with the new password.
        subject, plain_text, html_content = forgot_password_template(new_password)
        mail.send_email(user["email"], subject, plain_text,
                        html_content)  # Ensure send_email exists in your mail module.
        success_text.value = "A new password has been generated and sent to your email."
        error_text.value = ""
        page.update()

    username_field = ft.TextField(label="Username")
    email_field = ft.TextField(label="Email")
    error_text = ft.Text("", color=ft.Colors.RED)
    success_text = ft.Text("", color=ft.Colors.GREEN)

    page.views.clear()
    page.views.append(
        ft.View(
            route="/forgot_password",
            controls=[
                ft.Column(
                    [
                        ft.Text("Forgot Password", size=32, weight=ft.FontWeight.BOLD, color=ft.Colors.PURPLE),
                        username_field,
                        email_field,
                        error_text,
                        ft.ElevatedButton("Reset Password", on_click=do_reset_password),
                        success_text,
                        ft.TextButton("Back", on_click=lambda e: go_to_view(page, admin_login_view, games)),
                    ],
                    alignment=ft.MainAxisAlignment.CENTER,
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    spacing=20,
                )
            ],
        )
    )
    page.update()


# -------------------- Account Creation Views --------------------
def create_player_account_view(page: ft.Page, games):
    def validate_usernames(e):
        if username_field.value != confirm_username_field.value:
            username_error.value = "Usernames do not match."
        else:
            username_error.value = ""
        page.update()

    def do_create_player(e):
        fname = first_name_field.value.strip()
        lname = last_name_field.value.strip()
        uname = username_field.value.strip()
        email = f"{uname}@playfulminds.com"
        if not all([fname, lname, uname]):
            error_text.value = "All fields are required."
            page.update()
            return
        accounts = db.load_accounts()
        if uname in accounts:
            error_text.value = "Username already exists."
            page.update()
            return
        creation_date = datetime.datetime.now().isoformat()
        db.save_user(fname, lname, uname, "player", "", email, creation_date)
        # Log the player account creation.
        logs.log_event(0, "create_player_account", f"Player account '{uname}' created.")
        success_text.value = f"Player account '{uname}' created successfully!"
        error_text.value = ""
        page.update()

    first_name_field = ft.TextField(label="First Name")
    last_name_field = ft.TextField(label="Last Name")
    username_field = ft.TextField(label="Username", on_change=validate_usernames)
    confirm_username_field = ft.TextField(label="Confirm Username", on_change=validate_usernames)
    username_error = ft.Text("", color=ft.Colors.RED)
    error_text = ft.Text("", color=ft.Colors.RED)
    success_text = ft.Text("", color=ft.Colors.GREEN)

    page.views.clear()
    page.views.append(
        ft.View(
            route="/create_player_account",
            controls=[
                ft.Column(
                    [
                        ft.Text("Create Player Account", size=32, weight=ft.FontWeight.BOLD, color=ft.Colors.PURPLE),
                        first_name_field,
                        last_name_field,
                        username_field,
                        confirm_username_field,
                        username_error,
                        error_text,
                        success_text,
                        ft.ElevatedButton("Create Account", on_click=do_create_player),
                        ft.TextButton(
                            "Back",
                            on_click=lambda e: go_to_view(page, back_navigation_view(page, games), games)
                        ),
                    ],
                    alignment=ft.MainAxisAlignment.CENTER,
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    spacing=20,
                )
            ],
        )
    )
    page.update()


def create_admin_account_view(page: ft.Page, games):
    def validate_passwords(e):
        if password_field.value != confirm_password_field.value:
            password_error.value = "Passwords do not match."
        elif not utils.is_strong_password(password_field.value):
            password_error.value = ("Password must be at least 8 characters with uppercase, lowercase, number, "
                                    "and symbol.")
        else:
            password_error.value = ""
        page.update()

    def do_create_admin(e):
        fname = first_name_field.value.strip()
        lname = last_name_field.value.strip()
        uname = username_field.value.strip()
        email = email_field.value.strip()
        pwd = password_field.value.strip()
        if not all([fname, lname, uname, email, pwd, confirm_password_field.value.strip()]):
            error_text.value = "All fields are required."
            page.update()
            return
        accounts = db.load_accounts()
        if uname in accounts:
            error_text.value = "Username already exists."
            page.update()
            return
        if pwd != confirm_password_field.value or not utils.is_strong_password(pwd):
            error_text.value = "Password does not meet requirements or does not match."
            page.update()
            return
        hashed_pwd = bcrypt.hashpw(pwd.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        creation_date = datetime.datetime.now().isoformat()
        db.save_user(fname, lname, uname, "admin", hashed_pwd, email, creation_date)
        # Log the admin account creation.
        logs.log_event(0, "create_admin_account", f"Admin account '{uname}' created.")
        success_text.value = f"Admin account '{uname}' created successfully!"
        error_text.value = ""
        page.update()

    first_name_field = ft.TextField(label="First Name")
    last_name_field = ft.TextField(label="Last Name")
    username_field = ft.TextField(label="Username", value="ClassName_Admin",
                                  tooltip="Suggested pattern: ClassName_Admin#")
    email_field = ft.TextField(label="Email")
    password_field = ft.TextField(label="Password", password=True, on_change=validate_passwords)
    confirm_password_field = ft.TextField(label="Confirm Password", password=True, on_change=validate_passwords)
    password_error = ft.Text("", color=ft.Colors.RED)
    error_text = ft.Text("", color=ft.Colors.RED)
    success_text = ft.Text("", color=ft.Colors.GREEN)

    page.views.clear()
    page.views.append(
        ft.View(
            route="/create_admin_account",
            controls=[
                ft.Column(
                    [
                        ft.Text("Create Admin Account", size=32, weight=ft.FontWeight.BOLD, color=ft.Colors.PURPLE),
                        first_name_field,
                        last_name_field,
                        username_field,
                        email_field,
                        password_field,
                        confirm_password_field,
                        password_error,
                        error_text,
                        success_text,
                        ft.ElevatedButton("Create Account", on_click=do_create_admin),
                        ft.TextButton(
                            "Back",
                            on_click=lambda e: go_to_view(page, back_navigation_view(page, games), games)
                        ),
                    ],
                    alignment=ft.MainAxisAlignment.CENTER,
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    spacing=20,
                )
            ],
        )
    )
    page.update()


# -------------------- Game Selection & Guest Login --------------------
def guest_login(page: ft.Page, games):
    global current_user
    current_user = {"id": 0, "userName": "Guest", "role": "player", "email": ""}
    go_to_view(page, game_selection_view, games)


def game_selection_view(page: ft.Page, games):
    game_items = []
    for game in games:
        if game["image"] and os.path.exists(game["image"]):
            img = ft.Image(src=game["image"], width=100, height=100, fit=ft.ImageFit.CONTAIN)
        else:
            img = ft.Container(
                content=ft.Text("No Image", size=16, color=ft.Colors.WHITE),
                width=100, height=100, alignment=ft.alignment.center, bgcolor=ft.Colors.GREY,
            )
        item = ft.Container(
            content=ft.Row(
                [
                    ft.Container(content=img, width=100, height=100),
                    ft.Column(
                        [
                            ft.Text(game["title"], size=20, weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE),
                            ft.Text(game["description"], size=16, color=ft.Colors.WHITE),
                        ],
                        expand=True, spacing=5,
                    ),
                ],
                spacing=10, alignment=ft.MainAxisAlignment.START,
            ),
            bgcolor=ft.Colors.GREY_700, border_radius=8, padding=10, margin=5,
            width=page.width - 40, height=150,
            on_click=lambda e, file=game["file"]: utils.launch_game(file),
        )
        game_items.append(item)

    # Create a welcome message based on session data.
    welcome_message = (
        "Welcome, Guest!"
        if current_user.get("id", 0) == 0
        else f"Welcome, {current_user.get('firstName', 'Player')}!"
    )

    page.views.clear()
    page.views.append(
        ft.View(
            route="/game_selection",
            controls=[
                ft.Column(
                    [
                        # Added welcome text:
                        ft.Text(welcome_message, size=24, weight=ft.FontWeight.BOLD, color=ft.Colors.BLUE),
                        ft.Text("Select a Game", size=32, weight=ft.FontWeight.BOLD, color=ft.Colors.PURPLE),
                        ft.ListView(expand=True, spacing=10, controls=game_items),
                        ft.Row(
                            [
                                ft.ElevatedButton("Settings",
                                                  on_click=lambda e: go_to_view(page, settings_view, games)),
                                ft.ElevatedButton("Log Out", on_click=lambda e: player_logout(page, games)),
                            ],
                            alignment=ft.MainAxisAlignment.CENTER, spacing=20,
                        ),
                    ],
                    expand=True, spacing=10,
                )
            ],
        )
    )
    page.update()


def settings_view(page: ft.Page, games):
    current_idx = utils.load_camera_index()

    def camera_changed(e: ft.ControlEvent):
        try:
            idx = int(camera_dropdown.value)
            utils.save_camera_index(idx)
            notification_text.value = f"Camera index updated to: {idx}"
        except Exception as ex:
            notification_text.value = f"Error: {ex}"
        page.update()

    camera_dropdown = ft.Dropdown(
        value=str(current_idx),
        options=[ft.dropdown.Option(str(i)) for i in range(4)],
        on_change=camera_changed,
    )
    notification_text = ft.Text("", color=ft.Colors.GREEN)

    # Back button now checks if the current user is a player.
    back_button = ft.ElevatedButton(
        "Back",
        on_click=lambda e: go_to_view(
            page,
            game_selection_view if (
                    current_user and current_user.get("role", "").lower() == "player") else landing_view,
            games
        )
    )

    page.views.clear()
    page.views.append(
        ft.View(
            route="/settings",
            controls=[
                ft.Column(
                    [
                        ft.Text("Settings", size=32, weight=ft.FontWeight.BOLD, color=ft.Colors.PURPLE),
                        ft.Text("Select Camera Index:", size=20, color=ft.Colors.PURPLE),
                        camera_dropdown,
                        notification_text,
                        back_button,
                    ],
                    alignment=ft.MainAxisAlignment.CENTER,
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    spacing=20,
                )
            ],
        )
    )
    page.update()


# -------------------- Enhanced Admin Dashboard with Reports & User Management --------------------
def admin_logout(page: ft.Page, games):
    global current_user  # Declare global at the beginning
    # Optionally log the logout event.
    logs.log_event(current_user.get("id", 0), "logout", "Admin logged out.")
    current_user = None
    # Navigate back to the landing view.
    go_to_view(page, landing_view, games)


def delete_and_refresh(page: ft.Page, games, user_id):
    db.delete_user(user_id)
    logs.log_event(user_id, "delete", "User account deleted by admin.")
    go_to_view(page, admin_dashboard_view, games)


def update_user_view(page: ft.Page, games, user_id):
    user_data = db.get_user_by_id(user_id)
    if not user_data:
        go_to_view(page, admin_dashboard_view, games)
        return
    first_name_field = ft.TextField(label="First Name", value=user_data.get("firstName", ""))
    last_name_field = ft.TextField(label="Last Name", value=user_data.get("lastName", ""))
    username_field = ft.TextField(label="Username", value=user_data.get("userName", ""))
    role_field = ft.TextField(label="Role", value=user_data.get("role", ""))
    email_field = ft.TextField(label="Email", value=user_data.get("email", ""))
    error_text = ft.Text("", color=ft.Colors.RED)

    def do_update(e):
        fname = first_name_field.value.strip()
        lname = last_name_field.value.strip()
        uname = username_field.value.strip()
        role = role_field.value.strip()
        email = email_field.value.strip()
        if not all([fname, lname, uname, role, email]):
            error_text.value = "All fields are required."
            page.update()
            return
        db.update_user(user_id, fname, lname, uname, role, email)
        logs.log_event(user_id, "update", "User account updated by admin.")
        go_to_view(page, admin_dashboard_view, games)

    def cancel_update(e):
        go_to_view(page, admin_dashboard_view, games)

    page.views.clear()
    page.views.append(
        ft.View(
            route="/update_user",
            controls=[
                ft.Column(
                    controls=[
                        ft.Text("Update User", size=32, weight=ft.FontWeight.BOLD, color=ft.Colors.PURPLE),
                        first_name_field,
                        last_name_field,
                        username_field,
                        role_field,
                        email_field,
                        error_text,
                        ft.Row(
                            controls=[
                                ft.ElevatedButton("Save", on_click=do_update),
                                ft.ElevatedButton("Cancel", on_click=cancel_update),
                            ],
                            spacing=20,
                            alignment=ft.MainAxisAlignment.CENTER,
                        ),
                    ],
                    alignment=ft.MainAxisAlignment.CENTER,
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    spacing=20,
                )
            ],
        )
    )
    page.update()


# Placeholder functions for new analytics DB queries (to be implemented in db.py)
# --- Dummy Export/Print/Email Functions (to be implemented as needed) ---
def export_table_to_csv(data, filename):
    import csv
    with open(filename, "w", newline="") as f:
        writer = csv.writer(f)
        for row in data:
            writer.writerow(row)


# In pages.py replace placeholder functions with:

def get_active_users_count():
    return db.get_active_users_count()


def get_total_sessions():
    return db.get_total_sessions()


def get_avg_session_duration():
    stats = db.load_overall_session_stats()
    return round(stats.get("total_play_time", 0) / (stats.get("session_count", 1) or 1), 1)


def get_avg_level_gain():
    return db.get_avg_level_gain()  # Requires similar DB function


def get_game_play_counts(order="desc", limit=3):
    return db.get_game_play_counts(limit=limit, order=order)


def get_top_players_by_level_up(limit=5, days=7):
    return db.get_top_players_by_level(limit=limit, days=days)


def get_inactive_players(days=3):
    return db.get_inactive_players(days=days)  # Requires similar DB function


# Start of Dashboard View

# New Admin Dashboard View
# --- Navigation Helper Function ---
def go_to_view(page: ft.Page, view_func, games):
    page.views.clear()  # Clear all existing views
    view_func(page, games)  # Call the view function to build the new view
    page.update()  # Refresh the page


# --- Test View (for debugging navigation) ---
def test_view(page: ft.Page, games):
    page.views.clear()
    page.views.append(
        ft.View(
            route="/test",
            controls=[
                ft.Column(
                    controls=[
                        ft.Text("Test View", size=32, weight=ft.FontWeight.BOLD, color=ft.Colors.BLUE),
                        ft.ElevatedButton("Back to Dashboard",
                                          on_click=lambda e: go_to_view(page, admin_dashboard_view, games))
                    ],
                    alignment=ft.MainAxisAlignment.CENTER,
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    spacing=20
                )
            ]
        )
    )
    page.update()


# --- Updated Admin Dashboard View ---
def admin_dashboard_view(page: ft.Page, games):
    global current_user  # Ensure current_user is available

    # --- Welcome Header & Navigation ---
    welcome_line = ft.Text(
        f"Welcome, {current_user.get('firstName', current_user.get('userName', 'Admin'))}!",
        size=24, weight=ft.FontWeight.BOLD, color=ft.Colors.BLUE
    )
    nav_bar = ft.Row(
        controls=[
            ft.ElevatedButton("Refresh", on_click=lambda event: go_to_view(page, admin_dashboard_view, games)),
            ft.ElevatedButton("Log Out", on_click=lambda event: admin_logout(page, games))
        ],
        alignment=ft.MainAxisAlignment.CENTER,
        spacing=20
    )

    # --- KPI Cards Section ---
    def kpi_card(title, value):
        return ft.Container(
            content=ft.Column(
                controls=[
                    ft.Text(title, size=16),
                    ft.Text(str(value), size=24, weight=ft.FontWeight.BOLD, color=ft.Colors.GREEN)
                ],
                horizontal_alignment=ft.CrossAxisAlignment.CENTER
            ),
            padding=10,
            bgcolor=ft.Colors.PURPLE,
            border_radius=8,
            width=250
        )

    kpi_cards = ft.Row(
        controls=[
            kpi_card("Active Users", db.get_active_users_count()),
            kpi_card("Total Sessions", db.get_total_sessions()),
            kpi_card("Avg Session (min)", db.get_avg_session_duration()),
            kpi_card("Avg Levels", db.get_avg_level_gain())
        ],
        spacing=20
    )

    # --- Player Accounts Tab ---
    accounts = db.load_accounts()
    player_accounts = [acct for acct in accounts.values() if acct["role"].lower() == "player"]
    player_table = ft.DataTable(
        columns=[
            ft.DataColumn(ft.Text("First Name")),
            ft.DataColumn(ft.Text("Last Name")),
            ft.DataColumn(ft.Text("Username")),
            ft.DataColumn(ft.Text("Levels"))
        ],
        rows=[
            ft.DataRow(cells=[
                ft.DataCell(ft.Text(p.get("firstName", ""))),
                ft.DataCell(ft.Text(p.get("lastName", ""))),
                ft.DataCell(ft.Text(p.get("userName", ""))),
                ft.DataCell(ft.Text(" | ".join([
                    f"{game.get('title', 'Unknown')}: Lvl {db.get_player_level(p.get('id', 0),
                                                                               game.get('game_id', game.get('title', '')))}"
                    for game in games
                ])))
            ])
            for p in player_accounts
        ]
    )
    player_accounts_section = ft.Column(
        controls=[
            ft.Text("Player Accounts Report", size=24, weight=ft.FontWeight.BOLD),
            player_table,
        ],
        scroll=ft.ScrollMode.AUTO,
        spacing=10
    )

    # --- Sessions Stats Tab ---
    conn = db._create_connection()
    sessions_table = None
    if conn is not None:
        try:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT session_id, user_id, game_id, start_time, end_time, session_type, level
                FROM GameSessions
            """)
            session_rows = cursor.fetchall()
            sessions_table = ft.DataTable(
                columns=[
                    ft.DataColumn(ft.Text("Session ID")),
                    ft.DataColumn(ft.Text("User ID")),
                    ft.DataColumn(ft.Text("Game ID")),
                    ft.DataColumn(ft.Text("Start Time")),
                    ft.DataColumn(ft.Text("End Time")),
                    ft.DataColumn(ft.Text("Session Type")),
                    ft.DataColumn(ft.Text("Level"))
                ],
                rows=[
                    ft.DataRow(cells=[
                        ft.DataCell(ft.Text(str(row[0]))),
                        ft.DataCell(ft.Text(str(row[1]))),
                        ft.DataCell(ft.Text(row[2])),
                        ft.DataCell(ft.Text(row[3])),
                        ft.DataCell(ft.Text(row[4] if row[4] is not None else "N/A")),
                        ft.DataCell(ft.Text(row[5] if row[5] is not None else "N/A")),
                        ft.DataCell(ft.Text(str(row[6])))
                    ])
                    for row in session_rows
                ]
            )
        except Exception as e:
            print(f"Error fetching session stats: {e}")
        finally:
            conn.close()
    sessions_section = ft.Column(
        controls=[
            ft.Text("Game Sessions", size=24, weight=ft.FontWeight.BOLD),
            sessions_table if sessions_table is not None else ft.Text("No session data available."),
        ],
        scroll=ft.ScrollMode.AUTO,
        spacing=10
    )

    # --- Player Progress Tab ---
    progress_records = db.get_all_player_progress()
    progress_table = ft.DataTable(
        columns=[
            ft.DataColumn(ft.Text("User ID")),
            ft.DataColumn(ft.Text("Game ID")),
            ft.DataColumn(ft.Text("Level")),
            ft.DataColumn(ft.Text("Points")),
            ft.DataColumn(ft.Text("Last Updated"))
        ],
        rows=[
            ft.DataRow(cells=[
                ft.DataCell(ft.Text(str(record.get("user_id", "")))),
                ft.DataCell(ft.Text(record.get("game_id", ""))),
                ft.DataCell(ft.Text(str(record.get("level", "")))),
                ft.DataCell(ft.Text(str(record.get("points", "")))),
                ft.DataCell(ft.Text(record.get("updated_at", "")))
            ])
            for record in progress_records
        ]
    )
    progress_section = ft.Column(
        controls=[
            ft.Text("Player Progress Report", size=24, weight=ft.FontWeight.BOLD),
            progress_table,
        ],
        scroll=ft.ScrollMode.AUTO,
        spacing=10
    )

    # --- Logs Tab ---
    log_entries = logs.get_logs(limit=20)
    logs_table = ft.DataTable(
        columns=[
            ft.DataColumn(ft.Text("Timestamp")),
            ft.DataColumn(ft.Text("User ID")),
            ft.DataColumn(ft.Text("Action")),
            ft.DataColumn(ft.Text("Details"))
        ],
        rows=[
            ft.DataRow(cells=[
                ft.DataCell(ft.Text(entry.get("timestamp", ""))),
                ft.DataCell(ft.Text(str(entry.get("user_id", "")))),
                ft.DataCell(ft.Text(entry.get("action", ""))),
                ft.DataCell(ft.Text(entry.get("details", "")))
            ])
            for entry in log_entries
        ]
    )
    logs_section = ft.Column(
        controls=[
            ft.Text("Recent Logs", size=24, weight=ft.FontWeight.BOLD),
            logs_table,
        ],
        scroll=ft.ScrollMode.AUTO,
        spacing=10
    )

    # --- User Management Tab ---
    user_entries = []
    for user_key, u in accounts.items():
        actions = ft.Row(
            controls=[
                ft.ElevatedButton("Update", on_click=lambda event, uid=u["id"]: go_to_view(page,
                                                                                           lambda p,
                                                                                                  g: update_user_view(p,
                                                                                                                      g,
                                                                                                                      uid),
                                                                                           games)),
                ft.ElevatedButton("Delete", on_click=lambda event, uid=u["id"]: delete_and_refresh(page, games, uid))
            ],
            spacing=10
        )
        user_entries.append(
            ft.DataRow(cells=[
                ft.DataCell(ft.Text(u.get("firstName", ""))),
                ft.DataCell(ft.Text(u.get("lastName", ""))),
                ft.DataCell(ft.Text(u.get("userName", ""))),
                ft.DataCell(ft.Text(u.get("role", ""))),
                ft.DataCell(ft.Text(u.get("email", ""))),
                ft.DataCell(ft.Text(u.get("creationDate", ""))),
                ft.DataCell(actions)
            ])
        )
    users_table = ft.DataTable(
        columns=[
            ft.DataColumn(ft.Text("First Name")),
            ft.DataColumn(ft.Text("Last Name")),
            ft.DataColumn(ft.Text("Username")),
            ft.DataColumn(ft.Text("Role")),
            ft.DataColumn(ft.Text("Email")),
            ft.DataColumn(ft.Text("Created On")),
            ft.DataColumn(ft.Text("Actions"))
        ],
        rows=user_entries
    )
    user_management_section = ft.Column(
        controls=[
            ft.Text("User Management", size=24, weight=ft.FontWeight.BOLD),
            ft.Row(
                controls=[
                    ft.ElevatedButton("Create Player Account",
                                      on_click=lambda e: go_to_view(page, create_player_account_view, games)),
                    ft.ElevatedButton("Create Admin Account",
                                      on_click=lambda e: go_to_view(page, create_admin_account_view, games))
                ],
                spacing=20,
                alignment=ft.MainAxisAlignment.CENTER
            ),
            ft.Divider(),
            users_table
        ],
        scroll=ft.ScrollMode.AUTO,
        spacing=10
    )

    # --- Analytics Section (Using Dummy Data Functions) ---
    top_games = get_game_play_counts(order="desc", limit=3)
    bottom_games = get_game_play_counts(order="asc", limit=3)
    top_players = get_top_players_by_level_up(limit=5, days=7)
    inactive_players = get_inactive_players(days=3)

    top_games_rows = [
        ft.DataRow(cells=[
            ft.DataCell(ft.Text(game["title"], color=ft.Colors.GREEN)),
            ft.DataCell(ft.Text(str(game["session_count"]), color=ft.Colors.GREEN))
        ])
        for game in top_games
    ]
    top_games_table = ft.DataTable(
        columns=[ft.DataColumn(ft.Text("Game")), ft.DataColumn(ft.Text("Sessions"))],
        rows=top_games_rows
    )
    bottom_games_rows = [
        ft.DataRow(cells=[
            ft.DataCell(ft.Text(game["title"], color=ft.Colors.RED)),
            ft.DataCell(ft.Text(str(game["session_count"]), color=ft.Colors.RED))
        ])
        for game in bottom_games
    ]
    bottom_games_table = ft.DataTable(
        columns=[ft.DataColumn(ft.Text("Game")), ft.DataColumn(ft.Text("Sessions"))],
        rows=bottom_games_rows
    )
    top_players_rows = [
        ft.DataRow(cells=[
            ft.DataCell(ft.Text(str(player["user_id"]))),
            ft.DataCell(ft.Text(player["username"])),
            ft.DataCell(ft.Text(str(player["level_gain"])))
        ])
        for player in top_players
    ]
    top_players_table = ft.DataTable(
        columns=[ft.DataColumn(ft.Text("User ID")), ft.DataColumn(ft.Text("Username")),
                 ft.DataColumn(ft.Text("Level Gain"))],
        rows=top_players_rows
    )
    inactive_players_rows = [
        ft.DataRow(cells=[
            ft.DataCell(ft.Text(str(player["user_id"]))),
            ft.DataCell(ft.Text(player["username"])),
            ft.DataCell(ft.Text(player["last_update"]))
        ])
        for player in inactive_players
    ]
    inactive_players_table = ft.DataTable(
        columns=[ft.DataColumn(ft.Text("User ID")), ft.DataColumn(ft.Text("Username")),
                 ft.DataColumn(ft.Text("Last Update"))],
        rows=inactive_players_rows
    )
    analytics_section = ft.Column(
        controls=[
            ft.Text("Analytics", size=24, weight=ft.FontWeight.BOLD),
            ft.Row(
                controls=[
                    ft.Column(
                        controls=[
                            ft.Text("Top 3 Most Played Games", color=ft.Colors.GREEN),
                            top_games_table,
                            ft.Text("Bottom 3 Least Played Games", color=ft.Colors.RED),
                            bottom_games_table
                        ],
                        spacing=10
                    ),
                    ft.Column(
                        controls=[
                            ft.Text("Top 5 Players by Level Gains", color=ft.Colors.GREEN),
                            top_players_table,
                            ft.Text("Players Inactive >3 Days", color=ft.Colors.RED),
                            inactive_players_table
                        ],
                        spacing=10
                    )
                ],
                spacing=20
            )
        ],
        spacing=20,
        scroll=ft.ScrollMode.AUTO,
        expand=True
    )

    # --- Assemble All Tabs ---
    tabs = ft.Tabs(
        selected_index=0,
        tabs=[
            ft.Tab(text="Player Accounts", content=player_accounts_section),
            ft.Tab(text="Session Stats", content=sessions_section),
            ft.Tab(text="Logs", content=logs_section),
            ft.Tab(text="User Management", content=user_management_section),
            ft.Tab(text="Player Progress", content=progress_section),
            ft.Tab(text="Analytics", content=ft.Container(analytics_section, padding=10))
        ]
    )

    # --- Compose the Final Dashboard View ---
    page.views.clear()
    page.views.append(
        ft.View(
            route="/admin_dashboard",
            controls=[
                ft.Column(
                    controls=[
                        welcome_line,
                        ft.Divider(),
                        kpi_cards,
                        nav_bar,
                        tabs,
                    ],
                    spacing=20,
                    expand=True,
                    scroll=ft.ScrollMode.AUTO,
                )
            ]
        )
    )
    page.update()
