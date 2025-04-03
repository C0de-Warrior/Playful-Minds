import flet as ft
import os
import json
import subprocess
import sys

# Define configuration file paths
CONFIG_DIR = os.path.join(os.getcwd(), "config")
CONFIG_PATH = os.path.join(CONFIG_DIR, "settings.json")

def load_config():
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
            set_camera_index(0)
            return 0
    else:
        set_camera_index(0)
        return 0

def set_camera_index(index):
    if not os.path.exists(CONFIG_DIR):
        os.makedirs(CONFIG_DIR)
    with open(CONFIG_PATH, "w") as f:
        json.dump({"camera_index": index}, f)
    print(f"Camera index set to: {index}")

def launch_game(game_file):
    # Launch the game file from the "games" folder using the same Python interpreter.
    game_path = os.path.join(os.getcwd(), "games", game_file)
    if os.path.exists(game_path):
        subprocess.Popen([sys.executable, game_path])
    else:
        print(f"Game file {game_path} not found.")

# List of games with details (update the "image" key with a valid image path if available)
games = [
    {"title": "Edible Game", "file": "edible.py", "description": "Bite edible items while avoiding non-edible ones.", "image": ""},
    {"title": "Color Smash", "file": "color_smash.py", "description": "Match colors in a fun and fast-paced game.", "image": ""},
    {"title": "Number Dash", "file": "number_dash.py", "description": "Run through numbers in a challenging dash.", "image": ""},
    {"title": "Odd One Out", "file": "odd_one_out.py", "description": "Identify the odd item among similar ones.", "image": ""},
    {"title": "Shape Sorter", "file": "shape-sorter.py", "description": "Sort shapes to boost your visual skills.", "image": ""},
    {"title": "Spell Drop", "file": "spell_drop.py", "description": "Drop letters to form words correctly.", "image": ""},
    {"title": "Text Recognition", "file": "text_reco.py", "description": "Recognize text in images and have fun.", "image": ""},
    {"title": "Word Builder", "file": "word_builder.py", "description": "Construct words from jumbled letters.", "image": ""}
]

def main(page: ft.Page):
    # Set app title and background color
    page.title = "Playful Minds"
    page.bgcolor = ft.colors.YELLOW_200  # Bright yellow background
    page.padding = 20

    # Load camera configuration
    camera_index = load_config()

    # --- Navigation Helper ---
    def go_to_view(view: ft.View):
        page.views.clear()
        page.views.append(view)
        page.update()

    # --- Welcome View ---
    welcome_view = ft.View(
        "/welcome",
        controls=[
            ft.Column(
                [
                    ft.Text("Welcome to Playful Minds!", size=32, color=ft.colors.PURPLE, weight="bold"),
                    ft.ElevatedButton("Go to Game Selection", on_click=lambda e: go_to_view(game_selection_view)),
                ],
                alignment=ft.MainAxisAlignment.CENTER,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                spacing=20,
            )
        ]
    )

    # --- Build Game Items ---
    def create_game_item(game: dict) -> ft.Container:
        # Left side: image or placeholder
        if game["image"] and os.path.exists(game["image"]):
            img = ft.Image(src=game["image"], width=100, height=100, fit=ft.ImageFit.CONTAIN)
        else:
            img = ft.Container(
                content=ft.Text("No Image", size=16, color=ft.colors.WHITE),
                width=100,
                height=100,
                alignment=ft.alignment.center,
                bgcolor=ft.colors.GREY,
            )
        # Right side: title and description
        text_column = ft.Column(
            [
                ft.Text(game["title"], size=20, weight="bold", color=ft.colors.WHITE),
                ft.Text(game["description"], size=16, color=ft.colors.WHITE),
            ],
            spacing=5,
            expand=True,
        )
        # Create a clickable container for the game item
        return ft.Container(
            content=ft.Row(
                [
                    ft.Container(content=img, width=100, height=100),
                    text_column,
                ],
                alignment=ft.MainAxisAlignment.START,
            ),
            bgcolor=ft.colors.GREY_700,
            border_radius=8,
            padding=10,
            margin=5,
            on_click=lambda e, file=game["file"]: launch_game(file),
            width=page.width - 40,
            height=150,
        )

    # --- Game Selection View ---
    game_items = [create_game_item(game) for game in games]
    game_selection_view = ft.View(
        "/game_selection",
        controls=[
            ft.Column(
                [
                    ft.Text("Select a Game", size=32, color=ft.colors.PURPLE, weight="bold"),
                    ft.ListView(expand=True, spacing=10, controls=game_items),
                    ft.Row(
                        [
                            ft.ElevatedButton("Settings", on_click=lambda e: go_to_view(settings_view)),
                            ft.ElevatedButton("Quit", on_click=lambda e: page.window_destroy()),
                        ],
                        alignment=ft.MainAxisAlignment.CENTER,
                        spacing=20,
                    ),
                ],
                expand=True,
                spacing=10,
            )
        ]
    )

    # --- Settings View ---
    def camera_changed(e: ft.ControlEvent):
        try:
            idx = int(camera_dropdown.value)
            set_camera_index(idx)
        except Exception as ex:
            print("Error setting camera index:", ex)

    camera_dropdown = ft.Dropdown(
        value=str(camera_index),
        options=[ft.dropdown.Option(str(i)) for i in range(4)],
        on_change=camera_changed,
    )
    settings_view = ft.View(
        "/settings",
        controls=[
            ft.Column(
                [
                    ft.Text("Settings", size=32, color=ft.colors.PURPLE, weight="bold"),
                    ft.Text("Select Camera:", size=20, color=ft.colors.PURPLE),
                    camera_dropdown,
                    ft.ElevatedButton("Back", on_click=lambda e: go_to_view(game_selection_view)),
                ],
                alignment=ft.MainAxisAlignment.CENTER,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                spacing=20,
            )
        ]
    )

    # --- Game View (Placeholder) ---
    game_view = ft.View(
        "/game",
        controls=[
            ft.Column(
                [
                    ft.Text("Game Screen - Launching Game...", size=32, color=ft.colors.PURPLE, weight="bold"),
                    ft.ElevatedButton("Back to Menu", on_click=lambda e: go_to_view(game_selection_view)),
                ],
                alignment=ft.MainAxisAlignment.CENTER,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                spacing=20,
            )
        ]
    )

    # Start with the welcome view.
    page.views.append(welcome_view)
    page.update()

ft.app(target=main)
