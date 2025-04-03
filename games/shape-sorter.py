import sys
import os
import cv2
import random
import numpy as np
import pygame
from cvzone.HandTrackingModule import HandDetector
import cvzone
import math
import sys
import os
import sqlite3
import datetime
import json
from services import sessions, levels, logs, utils

# Load current user info from the shared JSON file
current_user_path = os.path.join(os.getcwd(), "config", "current_user.json")
try:
    with open(current_user_path, "r") as f:
        current_user = json.load(f)
except Exception as e:
    current_user = {"id": 0, "firstName": "Guest", "userName": "Guest", "role": "player", "email": ""}
    print("No current user found; defaulting to Guest.")

# Define USER_ID based on the loaded current_user
USER_ID = current_user["id"]


# --------------------- Theme Settings ---------------------
THEME_BG = (210, 180, 140)  # Light Brown (Tan)
THEME_TEXT = (72, 45, 20)   # Dark Brown (Saddle Brown)
BUTTON_BG = (139, 69, 19)    # Medium Brown (Chocolate)
BUTTON_TEXT = (245, 245, 220) # Light Beige (Beige)
HINT_COLOR = (255, 165, 0)   # Muted Orange (Orange)
TARGET_BG = (222, 184, 135)  # Light Tan (for target area)

# --------------------- Available Colors for Shapes (Simplified) ---------------------
available_colors = [(255, 0, 0), (255, 255, 0), (0, 0, 255), (0, 255, 0),
                    (255, 165, 0), (255, 192, 203), (128, 0, 128), (139, 69, 19),
                    (0, 0, 0)] # Red, Yellow, Blue, Green, Orange, Pink, Purple, Brown, Black
color_names = {(255, 0, 0): "Red", (255, 255, 0): "Yellow", (0, 0, 255): "Blue",
               (0, 255, 0): "Green", (255, 165, 0): "Orange", (255, 192, 203): "Pink",
               (128, 0, 128): "Purple", (139, 69, 19): "Brown", (0, 0, 0): "Black"}

# --------------------- Pygame Setup ---------------------
pygame.init()
width, height = 1280, 720
screen = pygame.display.set_mode((width, height))
pygame.display.set_caption("Shape Sorter Game")
clock = pygame.time.Clock()

# Use playful fonts for a kid-friendly look.
font_large = pygame.font.SysFont("Comic Sans MS", 80)
font_medium = pygame.font.SysFont("Comic Sans MS", 60)
font_small = pygame.font.SysFont("Comic Sans MS", 40)

# --------------------- Button Class (Template) ---------------------
class Button:
    def __init__(self, text, x, y, btn_width, btn_height, action=None):
        self.text = text
        self.rect = pygame.Rect(x, y, btn_width, btn_height)
        self.action = action

    def draw(self, surface):
        # Draw the button background and border.
        pygame.draw.rect(surface, BUTTON_BG, self.rect, border_radius=10)
        pygame.draw.rect(surface, THEME_BG, self.rect, 3, border_radius=10)
        # Render text and center it.
        text_surface = font_small.render(self.text, True, BUTTON_TEXT)
        text_rect = text_surface.get_rect(center=self.rect.center)
        surface.blit(text_surface, text_rect)

    def is_clicked(self, pos):
        return self.rect.collidepoint(pos)

# --------------------- Menu Layout Functions ---------------------
def get_main_menu_buttons():
    btn_width, btn_height = 300, 80
    start_btn = Button("Start Game", width // 2 - btn_width // 2, 400, btn_width, btn_height, action="start")
    quit_btn = Button("Quit", width // 2 - btn_width // 2, 500, btn_width, btn_height, action="quit")
    return [start_btn, quit_btn]

def get_pause_menu_buttons():
    btn_width, btn_height = 300, 80
    resume_btn = Button("Resume", width // 2 - btn_width // 2, 300, btn_width, btn_height, action="resume")
    quit_menu_btn = Button("Quit to Menu", width // 2 - btn_width // 2, 400, btn_width, btn_height, action="main_menu")
    return [resume_btn, quit_menu_btn]

def get_game_over_buttons():
    btn_width, btn_height = 300, 80
    restart_btn = Button("Play Again", width // 2 - btn_width // 2, 400, btn_width, btn_height, action="start")
    menu_btn = Button("Main Menu", width // 2 - btn_width // 2, 500, btn_width, btn_height, action="main_menu")
    quit_btn = Button("Quit", width // 2 - btn_width // 2, 600, btn_width, btn_height, action="quit")
    return [restart_btn, menu_btn, quit_btn]

# ---------------------- Helper Functions for Collision (Existing) ---------------------- #
def get_bbox(shape_type, pos, size):
    if shape_type in ['circle', 'star', 'pentagon', 'hexagon', 'oval', 'diamond']:
        return (pos[0] - size, pos[1] - size, pos[0] + size, pos[1] + size)
    elif shape_type == 'rectangle':
        return (pos[0], pos[1], pos[0] + 2 * size, pos[1] + size)
    else:  # square, triangle
        return (pos[0], pos[1], pos[0] + size, pos[1] + size)

def is_overlapping(bbox1, bbox2):
    x1, y1, x2, y2 = bbox1
    a1, b1, a2, b2 = bbox2
    return not (x2 < a1 or x1 > a2 or y2 < b1 or y1 > b2)

# ---------------------- Shape Classes (Existing) ---------------------- #
class DraggableShape:
    def __init__(self, shape_type, pos, size, color, target):
        self.shape_type = shape_type
        self.pos = pos
        self.size = size
        self.color = color
        self.matched = False
        self.target = target
        self.original_position = pos

    def update(self, cursor):
        if self.matched:
            return
        if self.shape_type in ['circle', 'star', 'pentagon', 'hexagon', 'oval', 'diamond']:
            cx, cy = self.pos
            if (cursor[0] - cx) ** 2 + (cursor[1] - cy) ** 2 < self.size ** 2:
                self.pos = cursor
        elif self.shape_type in ['square', 'triangle', 'rectangle']:
            x, y = self.pos
            width = self.size * 2 if self.shape_type == 'rectangle' else self.size
            height = self.size
            if x < cursor[0] < x + width and y < cursor[1] < y + height:
                self.pos = (cursor[0] - width // 2, cursor[1] - height // 2)

    def draw(self):
        if self.shape_type == 'circle':
            pygame.draw.circle(screen, self.color, self.pos, self.size)
        elif self.shape_type == 'square':
            pygame.draw.rect(screen, self.color, (self.pos[0], self.pos[1], self.size, self.size))
        elif self.shape_type == 'triangle':
            pygame.draw.polygon(screen, self.color, [(self.pos[0] + self.size // 2, self.pos[1]),
                                                     (self.pos[0], self.pos[1] + self.size),
                                                     (self.pos[0] + self.size, self.pos[1] + self.size)])
        elif self.shape_type == 'star':
            cx, cy = self.pos
            outer = self.size
            inner = int(self.size * 0.5)
            points = []
            for i in range(10):
                angle = i * math.pi / 5 - math.pi / 2
                r = outer if i % 2 == 0 else inner
                x = int(cx + r * math.cos(angle))
                y = int(cy + r * math.sin(angle))
                points.append((x, y))
            pygame.draw.polygon(screen, self.color, points)
        elif self.shape_type == 'pentagon':
            cx, cy = self.pos
            r = self.size
            points = []
            for i in range(5):
                angle = 2 * math.pi * i / 5 - math.pi / 2
                x = int(cx + r * math.cos(angle))
                y = int(cy + r * math.sin(angle))
                points.append((x, y))
            pygame.draw.polygon(screen, self.color, points)
        elif self.shape_type == 'hexagon':
            cx, cy = self.pos
            r = self.size
            points = []
            for i in range(6):
                angle = 2 * math.pi * i / 6 - math.pi / 2
                x = int(cx + r * math.cos(angle))
                y = int(cy + r * math.sin(angle))
                points.append((x, y))
            pygame.draw.polygon(screen, self.color, points)
        elif self.shape_type == 'rectangle':
            pygame.draw.rect(screen, self.color, (self.pos[0], self.pos[1], 2 * self.size, self.size))
        elif self.shape_type == 'oval':
            pygame.draw.ellipse(screen, self.color, (self.pos[0] - self.size - 20, self.pos[1] - self.size, 2 * (self.size + 20), 2 * self.size))
        elif self.shape_type == 'diamond':
            cx, cy = self.pos
            size = self.size
            points = [(cx, cy - size), (cx + size, cy), (cx, cy + size), (cx - size, cy)]
            pygame.draw.polygon(screen, self.color, points)

    def get_center(self):
        if self.shape_type in ['circle', 'star', 'pentagon', 'hexagon', 'oval', 'diamond']:
            return self.pos
        elif self.shape_type == 'rectangle':
            return (self.pos[0] + self.size, self.pos[1] + self.size // 2)
        else:
            return (self.pos[0] + self.size // 2, self.pos[1] + self.size // 2)

class OutlineShape:
    def __init__(self, shape_type, pos, size, color=(255, 255, 255)):
        self.shape_type = shape_type
        self.pos = pos
        self.size = size
        self.color = color

    def draw(self):
        if self.shape_type == 'circle':
            pygame.draw.circle(screen, self.color, self.pos, self.size, 5)
            center = self.pos
        elif self.shape_type == 'square':
            pygame.draw.rect(screen, self.color, (self.pos[0], self.pos[1], self.size, self.size), 5)
            center = (self.pos[0] + self.size // 2, self.pos[1] + self.size // 2)
        elif self.shape_type == 'triangle':
            pygame.draw.polygon(screen, self.color, [(self.pos[0] + self.size // 2, self.pos[1]),
                                                     (self.pos[0], self.pos[1] + self.size),
                                                     (self.pos[0] + self.size, self.pos[1] + self.size)], 5)
            center = (self.pos[0] + self.size // 2, self.pos[1] + self.size // 2)
        elif self.shape_type == 'pentagon':
            cx, cy = self.pos
            r = self.size
            points = []
            for i in range(5):
                angle = 2 * math.pi * i / 5 - math.pi / 2
                x = int(cx + r * math.cos(angle))
                y = int(cy + r * math.sin(angle))
                points.append((x, y))
            pygame.draw.polygon(screen, self.color, points, 5)
            center = self.pos
        elif self.shape_type == 'hexagon':
            cx, cy = self.pos
            r = self.size
            points = []
            for i in range(6):
                angle = 2 * math.pi * i / 6 - math.pi / 2
                x = int(cx + r * math.cos(angle))
                y = int(cy + r * math.sin(angle))
                points.append((x, y))
            pygame.draw.polygon(screen, self.color, points, 5)
            center = self.pos
        elif self.shape_type == 'star':
            cx, cy = self.pos
            outer = self.size
            inner = int(self.size * 0.5)
            points = []
            for i in range(10):
                angle = i * math.pi / 5 - math.pi / 2
                r = outer if i % 2 == 0 else inner
                x = int(cx + r * math.cos(angle))
                y = int(cy + r * math.sin(angle))
                points.append((x, y))
            pygame.draw.polygon(screen, self.color, points, 5)
            center = self.pos
        elif self.shape_type == 'rectangle':
            pygame.draw.rect(screen, self.color, (self.pos[0], self.pos[1], 2 * self.size, self.size), 5)
            center = (self.pos[0] + self.size, self.pos[1] + self.size // 2)
        elif self.shape_type == 'oval':
            pygame.draw.ellipse(screen, self.color, (self.pos[0] - self.size - 20, self.pos[1] - self.size, 2 * (self.size + 20), 2 * self.size), 5)
            center = self.pos
        elif self.shape_type == 'diamond':
            cx, cy = self.pos
            size = self.size
            points = [(cx, cy - size), (cx + size, cy), (cx, cy + size), (cx - size, cy)]
            pygame.draw.polygon(screen, self.color, points, 5)
            center = self.pos

        text_surface = font_small.render(self.shape_type.capitalize(), True, self.color)
        text_rect = text_surface.get_rect(center=center)
        screen.blit(text_surface, text_rect)

    def get_center(self):
        if self.shape_type in ['circle', 'star', 'pentagon', 'hexagon', 'oval', 'diamond']:
            return self.pos
        elif self.shape_type == 'rectangle':
            return (self.pos[0] + self.size, self.pos[1] + self.size // 2)
        else:
            return (self.pos[0] + self.size // 2, self.pos[1] + self.size // 2)

# Helper function to check if a draggable shape is close enough to its target outline
def is_close(draggable, outline, threshold=60): # Increased threshold slightly
    center1 = draggable.get_center()
    center2 = outline.get_center()
    dist = math.sqrt((center1[0] - center2[0]) ** 2 + (center1[1] - center2[1]) ** 2)
    return dist < threshold

# ---------------------- Generate Shapes ---------------------- #
target_shape_name = None
target_color_name = None
correct_match_made = False # Flag to track if the correct match has been made
round_active = False # Flag to indicate if a round is currently active

def generate_shapes(mode="shape_only"):
    global target_shape_name
    global target_color_name
    global correct_match_made
    global round_active
    correct_match_made = False # Reset the flag for a new round
    round_active = True

    draggable_shapes = []
    outline_shapes = []
    placed_draggable_bboxes = []
    placed_outline_bboxes = []
    available_positions_draggable = [(150, 150), (450, 150), (750, 150), (1050, 150)]
    random.shuffle(available_positions_draggable)
    available_positions_outline = [(150, 450), (450, 450), (750, 450), (1050, 450)]
    random.shuffle(available_positions_outline)

    available_main = ["circle", "square", "rectangle", "triangle", "oval", "star", "diamond"]
    base_sizes = {
        "circle": 50,
        "square": 100,
        "rectangle": 100,
        "triangle": 100,
        "oval": 60,
        "star": 60,
        "diamond": 60
    }

    def adjusted_size(shape_type):
        return int(base_sizes[shape_type] * 1.25)

    def get_valid_position(shape_type, size, positions_list, placed_bboxes):
        attempts = 100
        for _ in range(attempts):
            if not positions_list:
                return None
            pos = positions_list.pop()
            bbox = get_bbox(shape_type, pos, size)
            valid = True
            for other_bbox in placed_bboxes:
                if is_overlapping(bbox, other_bbox):
                    valid = False
                    break
            if valid:
                placed_bboxes.append(bbox)
                return pos
        return None

    if mode == "shape_only":
        main_count = random.randint(3, 4)
        main_shapes = random.sample(available_main, main_count)
        used_colors = random.sample(available_colors, main_count)

        for i, shape_type in enumerate(main_shapes):
            size = adjusted_size(shape_type)
            draggable_pos = get_valid_position(shape_type, size, available_positions_draggable, placed_draggable_bboxes)
            if draggable_pos:
                color = used_colors[i]
                outline_pos = get_valid_position(shape_type, size, available_positions_outline, placed_outline_bboxes)
                if outline_pos:
                    outline = OutlineShape(shape_type, outline_pos, size)
                    outline_shapes.append(outline)
                    draggable = DraggableShape(shape_type, draggable_pos, size, color, outline)
                    draggable_shapes.append(draggable)
                else:
                    available_positions_draggable.append(draggable_pos)

    elif mode == "shape_color":
        available_shapes = list(available_main)
        random.shuffle(available_shapes)
        target_shape_type = random.choice(available_shapes)
        target_color = random.choice(available_colors)
        target_shape_name = target_shape_type.capitalize()
        target_color_name = color_names.get(target_color, "Unknown")

        # Create the correct shape and outline
        size = adjusted_size(target_shape_type)
        draggable_pos = get_valid_position(target_shape_type, size, available_positions_draggable, placed_draggable_bboxes)
        outline_pos = get_valid_position(target_shape_type, size, available_positions_outline, placed_outline_bboxes)
        if draggable_pos and outline_pos:
            outline = OutlineShape(target_shape_type, outline_pos, size, color=target_color)
            outline_shapes.append(outline)
            draggable = DraggableShape(target_shape_type, draggable_pos, size, target_color, outline)
            draggable_shapes.append(draggable)

        # Create other incorrect shapes (up to 3 more)
        num_incorrect = random.randint(2, 3)
        placed_count = len(draggable_shapes)
        while placed_count < 4 and len(available_shapes) > 0:
            incorrect_shape_type = random.choice(available_shapes)
            incorrect_color = random.choice(available_colors)
            if incorrect_shape_type == target_shape_type and incorrect_color == target_color:
                continue # Avoid creating the same correct shape again

            size = adjusted_size(incorrect_shape_type)
            draggable_pos = get_valid_position(incorrect_shape_type, size, available_positions_draggable, placed_draggable_bboxes)
            outline_pos = get_valid_position(incorrect_shape_type, size, available_positions_outline, placed_outline_bboxes)
            if draggable_pos and outline_pos:
                outline = OutlineShape(incorrect_shape_type, outline_pos, size) # Outline doesn't need to be colored
                outline_shapes.append(outline)
                draggable = DraggableShape(incorrect_shape_type, draggable_pos, size, incorrect_color, outline)
                draggable_shapes.append(draggable)
                placed_count += 1
            if len(available_shapes) > 1:
                available_shapes.remove(incorrect_shape_type) # Try to have unique incorrect shapes

        random.shuffle(draggable_shapes)
        random.shuffle(outline_shapes)

    return draggable_shapes, outline_shapes

# Initialize game_mode here
game_mode = "shape_only"
# Generate shapes initially
draggable_shapes, outline_shapes = generate_shapes(game_mode)

# ---------------------- Webcam & Hand Detector Setup ---------------------
cap = cv2.VideoCapture(0)
cap.set(3, width)
cap.set(4, height)
detector = HandDetector(detectionCon=0.8)

# --------------------- Game Variables ---------------------
score = 0
lives = 3
dragging_shape = None
try_again_message = ""
try_again_timer = 0
shapes_in_round = 0 # To track the initial number of shapes in the round

# --------------------- Game States ---------------------
game_state = "main_menu"


# Levels & Session Integration for Odd One Out
GAME_ID_ODD = "ShapeSorter"  # Unique game ID for Odd One Out

# Initialize the player's progress record (creates one if it doesn't exist)
levels.init_player_progress(USER_ID, GAME_ID_ODD)
base_progress = levels.get_player_progress(USER_ID, GAME_ID_ODD)
base_level = base_progress["level"] if base_progress and "level" in base_progress else 0

# Start a game session and log the event.
session_id = sessions.start_game_session(USER_ID, GAME_ID_ODD, "shape-sorter")
# (If you have a logs module, you can also log the session start here)
logs.log_event(USER_ID, "game_start", f"Game session {session_id} started for {GAME_ID_ODD}")


def player_quit():
    global running
    sessions.end_game_session(session_id, USER_ID, GAME_ID_ODD, level_increment=0)
    # Log the quit event – adjust the log call as needed.
    # logs.log_event(USER_ID, "quit", f"Game session {session_id} ended by player quit with score {score}")
    running = False  # This will break the main loop.


# --------------------- Main Loop ---------------------
running = True
while running:
    elapsed_time = clock.tick(30) / 1000
    cursor = None
    pinch = False

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
            cap.release()
            pygame.quit()
            sys.exit()

        # --- Main Menu Events ---
        if game_state == "main_menu":
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                pos = pygame.mouse.get_pos()
                for button in get_main_menu_buttons():
                    if button.is_clicked(pos):
                        if button.action == "start":
                            game_state = "game"
                            score = 0
                            lives = 3
                            draggable_shapes.clear()
                            outline_shapes.clear()
                            try_again_message = ""
                            try_again_timer = 0
                            shapes_in_round = 0 # Reset for a new game
                            # Shapes will be generated when the game state is entered
                        elif button.action == "quit":
                            running = False
                            cap.release()
                            pygame.quit()
                            sys.exit()

        # --- Paused Menu Events ---
        elif game_state == "paused":
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                pos = pygame.mouse.get_pos()
                for button in get_pause_menu_buttons():
                    if button.is_clicked(pos):
                        if button.action == "resume":
                            game_state = "game"
                        elif button.action == "quit_menu":
                            game_state = "main_menu"
                            # Clear shapes when returning to the main menu
                            draggable_shapes.clear()
                            outline_shapes.clear()
                            try_again_message = ""
                            try_again_timer = 0
                            shapes_in_round = 0 # Reset if returning to menu

        # --- Game Over Menu Events ---
        elif game_state == "game_over":
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                pos = pygame.mouse.get_pos()
                for button in get_game_over_buttons():
                    if button.is_clicked(pos):
                        if button.action == "start":
                            game_state = "game"
                            score = 0
                            lives = 3
                            draggable_shapes.clear()
                            outline_shapes.clear()
                            try_again_message = ""
                            try_again_timer = 0
                            shapes_in_round = 0 # Reset for a new game
                            # Shapes will be generated when the game state is entered
                        elif button.action == "main_menu":
                            game_state = "main_menu"
                            # Clear shapes when returning to the main menu
                            draggable_shapes.clear()
                            outline_shapes.clear()
                            try_again_message = ""
                            try_again_timer = 0
                            shapes_in_round = 0 # Reset if returning to menu
                        elif button.action == "quit":
                            player_quit()
                            running = False
                            cap.release()
                            pygame.quit()
                            sys.exit()

        # --- Game State Key Handling ---
        if game_state == "game":
            if event.type == pygame.KEYDOWN:
                # Pressing Escape or Space pauses the game.
                if event.key in (pygame.K_ESCAPE, pygame.K_SPACE):
                    game_state = "paused"
                elif event.key == pygame.K_q:
                    running = False
                    cap.release()
                    pygame.quit()
                    sys.exit()

    # --------------------- State-Based Drawing ---------------------
    if game_state == "main_menu":
        screen.fill(THEME_BG)
        title_text = font_large.render("Shape Sorter", True, THEME_TEXT)
        screen.blit(title_text, title_text.get_rect(center=(width // 2, 100)))
        instructions = [
            "Instructions:",
            "1. Use pinch gesture (index & middle finger) to select a shape.",
            "2. Drag the shape to its outline.",
            "3. Correct matches earn points.",
            "4. Press SPACE or ESC to pause the game."
        ]
        for idx, line in enumerate(instructions):
            inst_text = font_small.render(line, True, THEME_TEXT)
            screen.blit(inst_text, (50, 180 + idx * 35))
        for button in get_main_menu_buttons():
            button.draw(screen)

    elif game_state == "paused":
        screen.fill(THEME_BG)
        pause_text = font_large.render("Paused", True, THEME_TEXT)
        screen.blit(pause_text, pause_text.get_rect(center=(width // 2, 100)))
        for button in get_pause_menu_buttons():
            button.draw(screen)

    elif game_state == "game_over":
        screen.fill(THEME_BG)
        game_over_text = font_large.render("Game Over!", True, THEME_TEXT)
        final_score_text = font_medium.render(f"Your final score: {score}", True, THEME_TEXT)
        lives_over_text = font_medium.render(f"You ran out of lives!", True, THEME_TEXT)
        screen.blit(game_over_text, game_over_text.get_rect(center=(width // 2, 200)))
        screen.blit(final_score_text, final_score_text.get_rect(center=(width // 2, 300)))
        screen.blit(lives_over_text, lives_over_text.get_rect(center=(width // 2, 360)))
        for button in get_game_over_buttons():
            button.draw(screen)

    elif game_state == "game":
        screen.fill(THEME_BG) # Fill background with theme color

        if try_again_timer > 0:
            try_again_timer -= elapsed_time
        else:
            try_again_message = ""

        # Generate shapes only when the game state is entered or after a correct match/incorrect drag in mode 2
        if not draggable_shapes and round_active: # Check if a round was active
            # Randomly select game mode for each new round
            game_mode = random.choice(["shape_only", "shape_color"])
            print(f"Current Game Mode: {game_mode}") # Debugging
            draggable_shapes, outline_shapes = generate_shapes(game_mode)
            shapes_in_round = len(draggable_shapes) # Store the initial number of shapes
            round_active = False # Reset round_active after generating new shapes

        ret, frame = cap.read()
        if not ret:
            continue
        frame = cv2.flip(frame, 1)
        hands, frame = detector.findHands(frame, flipType=False)
        if hands:
            lmList = hands[0]['lmList']
            length, info, _ = detector.findDistance(lmList[8][:2], lmList[12][:2], frame)
            pinch = length < 60
            cursor = lmList[8][:2]

            if pinch and cursor is not None:
                if dragging_shape is None:
                    for shape in draggable_shapes:
                        if shape.target is not None and not shape.matched:
                            center_x, center_y = shape.get_center()
                            if (cursor[0] - center_x)**2 + (cursor[1] - center_y)**2 < shape.size**2 * 2: # Increased touch area
                                dragging_shape = shape
                                break
                elif dragging_shape:
                    dragging_shape.update(cursor)
            else:
                if dragging_shape:
                    # Check if the pinch has ended
                    if not pinch:
                        # Check if the dragged shape is close to any outline upon release
                        closest_outline = None
                        min_distance = float('inf')
                        for outline in outline_shapes:
                            distance = math.sqrt((dragging_shape.get_center()[0] - outline.get_center()[0])**2 +
                                                 (dragging_shape.get_center()[1] - outline.get_center()[1])**2)
                            if distance < min_distance:
                                min_distance = distance
                                closest_outline = outline

                        if closest_outline and is_close(dragging_shape, closest_outline):
                            if game_mode == "shape_only":
                                if dragging_shape.shape_type == closest_outline.shape_type and not dragging_shape.matched: # Check if not already matched
                                    dragging_shape.matched = True
                                    dragging_shape.pos = closest_outline.pos
                                    score += 1
                                    # --- LEVEL UPDATE & SCORE LOGGING SNIPPET ---
                                    if USER_ID != 0:
                                        try:
                                            levels.update_player_progress(USER_ID, GAME_ID_ODD, additional_points=1)
                                        except Exception as e:
                                            print("Level update error:", e)
                                        # Log the score event (using your logs module if available)
                                        # logs.log_event(USER_ID, "score", f"Score incremented to {score}")
                                    else:
                                        # For guest users, log with user id 0.
                                        # logs.log_event(0, "score", f"Guest score incremented to {score}")
                                        pass
                                    # --- END SNIPPET ---
                                    dragging_shape = None # Release the shape
                                    if all(shape.matched for shape in draggable_shapes if shape.target is not None) and draggable_shapes:
                                        draggable_shapes.clear()
                                        outline_shapes.clear()
                                        round_active = True # Set round_active to trigger next round
                                else:
                                    lives -= 1
                                    if lives <= 0:
                                        game_state = "game_over"
                                    dragging_shape.pos = dragging_shape.original_position # Reset position
                                    dragging_shape = None # Release the shape
                            elif game_mode == "shape_color":
                                is_correct = (dragging_shape.shape_type == closest_outline.shape_type and
                                              dragging_shape.color == closest_outline.color)
                                if is_correct and not correct_match_made: # Check if the correct match hasn't been made yet
                                    dragging_shape.matched = True
                                    dragging_shape.pos = closest_outline.pos
                                    score += 2
                                    dragging_shape = None # Reset dragging shape
                                    correct_match_made = True # Set the flag
                                    draggable_shapes.clear() # Clear shapes to load the next set
                                    outline_shapes.clear()
                                    round_active = True # Set round_active to trigger next round
                                else:
                                    # Only process incorrect choices if the correct one hasn't been made
                                    if not correct_match_made:
                                        lives -= 1
                                        if lives <= 0:
                                            game_state = "game_over"
                                        try_again_message = "Try Again!"
                                        try_again_timer = 1.5 # Show message for 1.5 seconds
                                        dragging_shape.pos = dragging_shape.original_position # Reset position on incorrect placement in shape_color
                                        dragging_shape = None # Release the shape after incorrect attempt

                        else:
                            dragging_shape.pos = dragging_shape.original_position # Reset position if not close to any outline
                            dragging_shape = None # Release the shape

        # Convert webcam frame for display (no rotation)
        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        frame_surface = pygame.image.frombuffer(frame.tobytes(), (width, height), "RGB")
        screen.blit(frame_surface, (0, 0))

        # Draw outlines and draggable shapes
        for outline in outline_shapes:
            outline.draw()
        for shape in draggable_shapes:
            shape.draw()

        # Draw Instructions with a background box
        instruction_text = ""
        if game_mode == "shape_only":
            instruction_text = "Match the shapes to their outlines."
        elif game_mode == "shape_color":
            instruction_text = f"Sort the {target_color_name} {target_shape_name} to its position."
        instruction_surface = font_medium.render(instruction_text, True, THEME_TEXT)
        instruction_rect = instruction_surface.get_rect(center=(width // 2, 50)) # Centered at the top

        # Background color for the text box (slightly darker than THEME_BG)
        textbox_bg_color = (190, 160, 120)
        padding = 10
        textbox_rect = pygame.Rect(instruction_rect.left - padding,
                                     instruction_rect.top - padding,
                                     instruction_rect.width + 2 * padding,
                                     instruction_rect.height + 2 * padding)
        pygame.draw.rect(screen, textbox_bg_color, textbox_rect, border_radius=5)
        screen.blit(instruction_surface, instruction_rect)

        # Draw Score, Lives, and Mode below the instruction box
        info_y_start = textbox_rect.bottom + 20 # Position below the text box
        score_text = font_small.render(f"Score: {score}", True, THEME_TEXT)
        screen.blit(score_text, (20, info_y_start))
        lives_text = font_small.render(f"Lives: {lives}", True, THEME_TEXT)
        screen.blit(lives_text, (20, info_y_start + 40))
        mode_text = font_small.render(f"Mode: {game_mode.replace('_', ' ').title()}", True, THEME_TEXT)
        screen.blit(mode_text, (20, info_y_start + 80))

        # Display "Try Again" message
        if try_again_message:
            try_again_surface = font_medium.render(try_again_message, True, HINT_COLOR)
            try_again_rect = try_again_surface.get_rect(center=(width // 2, height // 2 + 50))
            screen.blit(try_again_surface, try_again_rect)

        # Check if all shapes are matched (for shape_only mode)
        # This check is now done within the pinch release logic for shape_only

        # Game over condition
        if lives <= 0:
            game_state = "game_over"

    pygame.display.flip()

cap.release()
pygame.quit()
sys.exit()