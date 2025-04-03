import flet as ft
import os
import sys
import bcrypt  # for checking hashed passwords in admin login
import datetime
from services import db, utils, mail, sessions, logs
import json


def save_current_user(user):
    """Persist the current user data to a JSON file."""
    config_dir = os.path.join(os.getcwd(), "config")
    if not os.path.exists(config_dir):
        os.makedirs(config_dir)
    current_user_path = os.path.join(config_dir, "current_user.json")
    with open(current_user_path, "w") as f:
        json.dump(user, f)

#comment
def clear_current_user():
    """Clear the persisted current user data."""
    current_user_path = os.path.join(os.getcwd(), "config", "current_user.json")
    if os.path.exists(current_user_path):
        os.remove(current_user_path)


# Global current_user variable for session tracking
current_user = None

# -------------------- Landing View --------------------
def landing_view(page: ft.Page, games):
    page.views.clear()
    page.views.append(
        ft.View(
            route="/",
            controls=[
                ft.Column(
                    [
                        ft.Text("Welcome to Playful Minds!", size=32, weight="bold", color=ft.Colors.PURPLE),
                        ft.Text(
                            "Playful Minds is a collection of fun, educational games.\n"
                            "Log in to track your progress, or play as a guest.",
                            size=20, color=ft.Colors.PURPLE, text_align=ft.TextAlign.CENTER
                        ),
                        ft.Row(
                            [
                                ft.ElevatedButton("Player Login", on_click=lambda e: go_to_view(page, player_login_view, games)),
                                ft.ElevatedButton("Create Player Account", on_click=lambda e: go_to_view(page, create_player_account_view, games)),
                                ft.ElevatedButton("Create Admin Account", on_click=lambda e: go_to_view(page, create_admin_account_view, games)),
                            ],
                            alignment=ft.MainAxisAlignment.CENTER,
                            spacing=20,
                        ),
                        ft.Row(
                            [
                                ft.ElevatedButton("Play as Guest", on_click=lambda e: guest_login(page, games)),
                                ft.ElevatedButton("Admin Login", on_click=lambda e: go_to_view(page, admin_login_view, games)),
                            ],
                            alignment=ft.MainAxisAlignment.CENTER,
                            spacing=20,
                        ),
                    ],
                    alignment=ft.MainAxisAlignment.CENTER,
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    spacing=30,
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
                        ft.Text("Player Login", size=32, weight="bold", color=ft.Colors.PURPLE),
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
    admin_password = ft.TextField(label="Password", password=True)
    error_text = ft.Text("", color=ft.Colors.RED)
    page.views.clear()
    page.views.append(
        ft.View(
            route="/admin_login",
            controls=[
                ft.Column(
                    [
                        ft.Text("Admin Login", size=32, weight="bold", color=ft.Colors.PURPLE),
                        admin_username,
                        admin_password,
                        error_text,
                        ft.ElevatedButton("Log In", on_click=do_admin_login),
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
                        ft.Text("Create Player Account", size=32, weight="bold", color=ft.Colors.PURPLE),
                        first_name_field,
                        last_name_field,
                        username_field,
                        confirm_username_field,
                        username_error,
                        error_text,
                        success_text,
                        ft.ElevatedButton("Create Account", on_click=do_create_player),
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

def create_admin_account_view(page: ft.Page, games):
    def validate_passwords(e):
        if password_field.value != confirm_password_field.value:
            password_error.value = "Passwords do not match."
        elif not utils.is_strong_password(password_field.value):
            password_error.value = "Password must be at least 8 characters with uppercase, lowercase, number, and symbol."
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
        success_text.value = f"Admin account '{uname}' created successfully!"
        error_text.value = ""
        page.update()

    first_name_field = ft.TextField(label="First Name")
    last_name_field = ft.TextField(label="Last Name")
    username_field = ft.TextField(label="Username", value="ClassName_Admin", tooltip="Suggested pattern: ClassName_Admin#")
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
                        ft.Text("Create Admin Account", size=32, weight="bold", color=ft.Colors.PURPLE),
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
                            ft.Text(game["title"], size=20, weight="bold", color=ft.Colors.WHITE),
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
    page.views.clear()
    page.views.append(
        ft.View(
            route="/game_selection",
            controls=[
                ft.Column(
                    [
                        ft.Text("Select a Game", size=32, weight="bold", color=ft.Colors.PURPLE),
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
    page.views.clear()
    page.views.append(
        ft.View(
            route="/settings",
            controls=[
                ft.Column(
                    [
                        ft.Text("Settings", size=32, weight="bold", color=ft.Colors.PURPLE),
                        ft.Text("Select Camera Index:", size=20, color=ft.Colors.PURPLE),
                        camera_dropdown,
                        notification_text,
                        ft.ElevatedButton("Back", on_click=lambda e: go_to_view(page, game_selection_view, games)),
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
                        ft.Text("Update User", size=32, weight="bold", color=ft.Colors.PURPLE),
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
def admin_dashboard_view(page: ft.Page, games):
    global current_user  # Declare global before using it
    # Display a welcome line for the admin using session data.
    welcome_line = ft.Text(
        f"Welcome, {current_user.get('firstName', current_user.get('userName', 'Admin'))}!",
        size=24, weight="bold", color=ft.Colors.BLUE
    )

    # Retrieve player accounts (role "player")
    accounts = db.load_accounts()
    player_accounts = [acct for acct in accounts.values() if acct["role"].lower() == "player"]

    # Build Player Accounts Report as a DataTable with headers.
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
                ft.DataCell(ft.Text(" | ".join(
                    [f"{game['title']}: Lvl {db.get_player_level(p.get('id', 0), game.get('game_id', game.get('title')))}"
                     for game in games]
                )))
            ])
            for p in player_accounts
        ]
    )

    # Build Session Statistics Report with headers.
    overall_stats = db.load_overall_session_stats()
    session_stats_table = ft.DataTable(
        columns=[
            ft.DataColumn(ft.Text("Statistic")),
            ft.DataColumn(ft.Text("Value"))
        ],
        rows=[
            ft.DataRow(cells=[
                ft.DataCell(ft.Text("Total Play Time (min)")),
                ft.DataCell(ft.Text(str(int(overall_stats.get("total_play_time", 0)))))
            ]),
            # Add more stats here if available.
        ]
    )

    # Build Logs Report as a DataTable (fetch recent logs; limit 20).
    log_entries = logs.get_logs(limit=20)
    logs_table = ft.DataTable(
        columns=[
            ft.DataColumn(ft.Text("Timestamp")),
            ft.DataColumn(ft.Text("User ID")),
            ft.DataColumn(ft.Text("Action")),
            ft.DataColumn(ft.Text("Details")),
        ],
        rows=[
            ft.DataRow(cells=[
                ft.DataCell(ft.Text(entry.get("timestamp", ""))),
                ft.DataCell(ft.Text(str(entry.get("user_id", "")))),
                ft.DataCell(ft.Text(entry.get("action", ""))),
                ft.DataCell(ft.Text(entry.get("details", ""))),
            ])
            for entry in log_entries
        ]
    )

    # Build User Management Report as a DataTable with Update and Delete options.
    user_entries = []
    for user_id, u in accounts.items():
        actions = ft.Row(
            controls=[
                ft.ElevatedButton("Update", on_click=lambda e, uid=u["id"]: go_to_view(page, lambda p, g: update_user_view(p, g, uid), games)),
                ft.ElevatedButton("Delete", on_click=lambda e, uid=u["id"]: delete_and_refresh(page, games, uid)),
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
                ft.DataCell(actions),
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
            ft.DataColumn(ft.Text("Actions")),
        ],
        rows=user_entries
    )

    # NEW: Build Player Progress Report as a DataTable.
    # Retrieve progress records from the database.
    progress_records = db.get_all_player_progress()  # Ensure this function is implemented in db.py
    progress_table = ft.DataTable(
        columns=[
            ft.DataColumn(ft.Text("User ID")),
            ft.DataColumn(ft.Text("Game ID")),
            ft.DataColumn(ft.Text("Level")),
            ft.DataColumn(ft.Text("Points")),
            ft.DataColumn(ft.Text("Last Updated")),
        ],
        rows=[
            ft.DataRow(cells=[
                ft.DataCell(ft.Text(str(record.get("user_id", "")))),
                ft.DataCell(ft.Text(record.get("game_id", ""))),
                ft.DataCell(ft.Text(str(record.get("level", "")))),
                ft.DataCell(ft.Text(str(record.get("points", "")))),
                ft.DataCell(ft.Text(record.get("updated_at", ""))),
            ])
            for record in progress_records
        ]
    )

    # Create tabs for each report.
    tabs = ft.Tabs(
        selected_index=0,
        tabs=[
            ft.Tab(
                text="Player Accounts",
                content=ft.Column(
                    controls=[
                        ft.Text("Player Accounts Report", size=24, weight="bold"),
                        player_table,
                    ],
                    scroll=True,
                    spacing=10
                )
            ),
            ft.Tab(
                text="Session Stats",
                content=ft.Column(
                    controls=[
                        ft.Text("Session Statistics", size=24, weight="bold"),
                        session_stats_table,
                    ],
                    spacing=10
                )
            ),
            ft.Tab(
                text="Logs",
                content=ft.Column(
                    controls=[
                        ft.Text("Recent Logs", size=24, weight="bold"),
                        logs_table,
                    ],
                    scroll=True,
                    spacing=10
                )
            ),
            ft.Tab(
                text="User Management",
                content=ft.Column(
                    controls=[
                        ft.Text("User Management", size=24, weight="bold"),
                        users_table,
                    ],
                    scroll=True,
                    spacing=10
                )
            ),
            # New Tab for Player Progress
            ft.Tab(
                text="Player Progress",
                content=ft.Column(
                    controls=[
                        ft.Text("Player Progress Report", size=24, weight="bold"),
                        progress_table,
                    ],
                    scroll=True,
                    spacing=10
                )
            ),
        ]
    )

    # Navigation bar for the admin dashboard: Refresh and Log Out.
    nav_bar = ft.Row(
        controls=[
            ft.ElevatedButton("Refresh", on_click=lambda e: go_to_view(page, admin_dashboard_view, games)),
            ft.ElevatedButton("Log Out", on_click=lambda e: admin_logout(page, games)),
        ],
        alignment=ft.MainAxisAlignment.CENTER,
        spacing=20
    )

    # Compose the dashboard view.
    page.views.clear()
    page.views.append(
        ft.View(
            route="/admin_dashboard",
            controls=[
                ft.Column(
                    controls=[
                        welcome_line,
                        ft.Divider(),
                        nav_bar,
                        tabs,
                    ],
                    spacing=20,
                    expand=True,
                )
            ],
        )
    )
    page.update()


# -------------------- Navigation Helper --------------------
def go_to_view(page: ft.Page, view_func, games):
    view_func(page, games)
