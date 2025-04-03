import flet as ft
import os
from services import db, pages, utils, push, logs, sessions

# -------------------- Game List --------------------
# List of games available in the app.
games = [
    {
        "title": "Edible Game",
        "file": "edible.py",
        "description": "Bite edible items while avoiding non-edible ones.",
        "image": os.path.join("assets", "logos", "edible_game.png")
    },
    {
        "title": "Color Smash",
        "file": "color_smash.py",
        "description": "Match colors in a fun, fast-paced game.",
        "image": os.path.join("assets", "logos", "color_smash.png")
    },
    {
        "title": "Number Dash",
        "file": "number_dash.py",
        "description": "Run through numbers in a challenging dash.",
        "image": os.path.join("assets", "logos", "number_dash.png")
    },
    {
        "title": "Odd One Out",
        "file": "odd_one_out.py",
        "description": "Identify the odd item among similar ones.",
        "image": os.path.join("assets", "logos", "odd_one_out.png")
    },
    {
        "title": "Shape Sorter",
        "file": "shape-sorter.py",
        "description": "Sort shapes to boost your visual skills.",
        "image": os.path.join("assets", "logos", "shape_sorter.png")
    },
    {
        "title": "Spell Drop",
        "file": "spell_drop.py",
        "description": "Drop letters to form words correctly.",
        "image": os.path.join("assets", "logos", "spell_drop.png")
    },
    {
        "title": "Maths Quest",
        "file": "math_quest.py",
        "description": "Embark on a Maths Quest where you solve challenging maths problems.",
        "image": os.path.join("assets", "logos", "math_quest.png")
    },
    {
        "title": "Word Builder",
        "file": "word_builder.py",
        "description": "Construct words from jumbled letters.",
        "image": os.path.join("assets", "logos", "word_builder.png")
    },
]

# -------------------- Global State --------------------
# current_user holds a dictionary (e.g., {"id": 1, "userName": "Guest", "role": "player"})
current_user = None


# -------------------- Main Function --------------------
def main(page: ft.Page):
    page.title = "Playful Minds"
    page.bgcolor = ft.Colors.YELLOW
    page.horizontal_alignment = ft.CrossAxisAlignment.CENTER
    page.vertical_alignment = ft.MainAxisAlignment.CENTER

    # Initialize the database and any necessary tables.
    db.initialize_database()

    # Update the push notification system's last active timestamp.
    push.update_last_active()

    # Optionally log that the application has started (using 0 for system/guest actions).
    logs.log_event(0, "app_start", "Application has started.")

    # Launch the landing view (menu) with the game list.
    pages.landing_view(page, games)


# -------------------- Run App --------------------
ft.app(target=main)
