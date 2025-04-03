import os
import random
import cv2
import numpy as np
import pygame
from cvzone.HandTrackingModule import HandDetector
import json
import sys
import sqlite3
import datetime
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
THEME_BG = (135, 206, 250)      # Light Sky Blue background
THEME_TEXT = (70, 130, 180)     # Steel Blue text
BUTTON_BG = (255, 255, 255)     # White button background
BUTTON_TEXT = (70, 130, 180)    # Steel Blue button text
HIGHLIGHT_COLOR = (255, 165, 0) # Orange highlight
CHOICE_BOX_BG = (255, 255, 224)  # Light Yellow choice box background
CHOICE_BOX_TEXT = (70, 130, 180)  # Steel Blue text
DROP_ZONE_COLOR = (144, 238, 144)  # Light Green drop zone
CORRECT_COLOR = (0, 255, 0)     # Bright Green for correct feedback
INCORRECT_COLOR = (255, 0, 0)   # Bright Red for incorrect feedback

# ---------------------- Initialization ----------------------
pygame.init()
screen_width, screen_height = 1280, 720
screen = pygame.display.set_mode((screen_width, screen_height))
pygame.display.set_caption("Odd One Out Game")
clock = pygame.time.Clock()

# Define fonts for text rendering
font_large = pygame.font.SysFont("Arial", 60)
font_medium = pygame.font.SysFont("Arial", 40)
font_small = pygame.font.SysFont("Arial", 28)
font_feedback = pygame.font.SysFont("Arial", 72, bold=True)

# Colors
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
YELLOW = (255, 255, 0)
LIGHT_BLUE = THEME_BG
LIGHT_GRAY = (200, 200, 200)
DARK_GRAY = (80, 80, 80)
LIGHT_GREEN = DROP_ZONE_COLOR

# Button Colors
BUTTON_NORMAL_COLOR = BUTTON_BG
BUTTON_HOVER_COLOR = HIGHLIGHT_COLOR
BUTTON_PRESSED_COLOR = (220, 220, 220)
BUTTON_TEXT_COLOR = BUTTON_TEXT

# Initialize webcam and hand detector flags
camera_initialized = False
detector_initialized = False
cap = None
detector = None

# ---------------------- Game Variables ----------------------
score = 0
attempts = 0
current_category = None
dragging_item = None
drag_offset = (0, 0)
lives = 3
heart_image = None
heart_scale = 0.12

# Screen flash variables
flash_color = None
flash_alpha = 0
flash_duration = 200  # milliseconds
flash_timer = 0
is_flashing = False

# Load heart image
try:
    script_dir = os.path.dirname(os.path.abspath(__file__))
    heart_path = os.path.join(os.path.dirname(script_dir), 'assets', 'heart.png')
    original_heart = pygame.image.load(heart_path).convert_alpha()
    heart_width = int(original_heart.get_width() * heart_scale)
    heart_height = int(original_heart.get_height() * heart_scale)
    heart_image = pygame.transform.scale(original_heart, (heart_width, heart_height))
except pygame.error as e:
    print(f"Error loading heart image: {e}")
    heart_image = pygame.Surface((50, 50))
    heart_image.fill(INCORRECT_COLOR)

# Define drop-off zones
drop_zone_width = 150
drop_zone_left = pygame.Rect(0, 0, drop_zone_width, screen_height)
drop_zone_right = pygame.Rect(screen_width - drop_zone_width, 0, drop_zone_width, screen_height)

# ---------------------- Game Data ----------------------
game_data = {
    "Fruits": [
        {"items": ["Apple", "Banana", "Orange", "Carrot"], "odd_one_out": "Carrot"},
        {"items": ["Strawberry", "Blueberry", "Raspberry", "Potato"], "odd_one_out": "Potato"},
        {"items": ["Mango", "Pineapple", "Watermelon", "Broccoli"], "odd_one_out": "Broccoli"}
    ],
    "Animals": [
        {"items": ["Cat", "Dog", "Elephant", "Table"], "odd_one_out": "Table"},
        {"items": ["Bird", "Fish", "Snake", "Chair"], "odd_one_out": "Chair"},
        {"items": ["Lion", "Tiger", "Bear", "Spoon"], "odd_one_out": "Spoon"}
    ],
    "Shapes": [
        {"items": ["Circle", "Square", "Triangle", "Book"], "odd_one_out": "Book"},
        {"items": ["Rectangle", "Pentagon", "Hexagon", "Cup"], "odd_one_out": "Cup"},
        {"items": ["Star", "Heart", "Diamond", "Shoe"], "odd_one_out": "Shoe"}
    ],
    "Colors": [
        {"items": ["Red", "Blue", "Green", "Sofa"], "odd_one_out": "Sofa"},
        {"items": ["Yellow", "Purple", "Orange", "Desk"], "odd_one_out": "Desk"},
        {"items": ["Pink", "Brown", "Black", "Cloud"], "odd_one_out": "Cloud"}
    ],
    "Numbers": [
        {"items": ["One", "Two", "Three", "Hat"], "odd_one_out": "Hat"},
        {"items": ["Four", "Five", "Six", "Glove"], "odd_one_out": "Glove"},
        {"items": ["Seven", "Eight", "Nine", "Sock"], "odd_one_out": "Sock"}
    ],
    "Letters": [
        {"items": ["A", "B", "C", "Plate"], "odd_one_out": "Plate"},
        {"items": ["D", "E", "F", "Glass"], "odd_one_out": "Glass"},
        {"items": ["G", "H", "I", "Knife"], "odd_one_out": "Knife"}
    ],
    "Vehicles": [
        {"items": ["Car", "Bus", "Train", "Shirt"], "odd_one_out": "Shirt"},
        {"items": ["Bike", "Scooter", "Motorcycle", "Pants"], "odd_one_out": "Pants"},
        {"items": ["Airplane", "Helicopter", "Jet", "Shoes"], "odd_one_out": "Shoes"}
    ],
    "Clothes": [
        {"items": ["Shirt", "Trousers", "Jacket", "Apple"], "odd_one_out": "Apple"},
        {"items": ["Socks", "Shoes", "Hat", "Banana"], "odd_one_out": "Banana"},
        {"items": ["Dress", "Skirt", "Blouse", "Orange"], "odd_one_out": "Orange"}
    ],
    "Musical Instruments": [
        {"items": ["Guitar", "Piano", "Drums", "Book"], "odd_one_out": "Book"},
        {"items": ["Violin", "Flute", "Trumpet", "Chair"], "odd_one_out": "Chair"},
        {"items": ["Harp", "Saxophone", "Clarinet", "Table"], "odd_one_out": "Table"}
    ],
    "Sports": [
        {"items": ["Football", "Basketball", "Tennis", "Milk"], "odd_one_out": "Milk"},
        {"items": ["Swimming", "Running", "Cycling", "Bread"], "odd_one_out": "Bread"},
        {"items": ["Golf", "Baseball", "Soccer", "Juice"], "odd_one_out": "Juice"}
    ]
}

# ---------------------- Button Class ----------------------
class Button:
    def __init__(self, text, x, y, width, height, normal_color, hover_color, pressed_color, text_color, font, action=None):
        self.text = text
        self.rect = pygame.Rect(x, y, width, height)
        self.normal_color = normal_color
        self.hover_color = hover_color
        self.pressed_color = pressed_color
        self.text_color = text_color
        self.font = font
        self.color = self.normal_color
        self.text_surface = font.render(text, True, text_color)
        self.text_rect = self.text_surface.get_rect(center=self.rect.center)
        self.is_pressed = False
        self.action = action

    def draw(self, surface):
        pygame.draw.rect(surface, self.color, self.rect, border_radius=15)
        surface.blit(self.text_surface, self.text_rect)

    def handle_input(self, event, cursor):
        if event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1 and self.rect.collidepoint(cursor):
                self.color = self.pressed_color
                self.is_pressed = True
        elif event.type == pygame.MOUSEBUTTONUP:
            if event.button == 1:
                self.is_pressed = False
                if self.rect.collidepoint(cursor):
                    self.color = self.hover_color
                    return self.action
                else:
                    self.color = self.normal_color
        elif event.type == pygame.MOUSEMOTION:
            if self.rect.collidepoint(cursor):
                self.color = self.hover_color if not self.is_pressed else self.pressed_color
            else:
                self.color = self.normal_color
        return None

# ---------------------- Helper Function ----------------------
def draw_text(surface, text, font, color, pos):
    text_surface = font.render(text, True, color)
    surface.blit(text_surface, pos)

# ---------------------- Draggable Item Class ----------------------
class DraggableItem:
    def __init__(self, text, pos, font, is_wrong=False):
        self.text = text
        self.pos = list(pos)
        self.font = font
        self.is_wrong = is_wrong
        self.original_pos = tuple(pos)
        self.padding = 20
        self.border_thickness = 4
        self.rect_width = 200
        self.rect_height = 120
        self.font_color = CHOICE_BOX_TEXT
        self.bg_color = CHOICE_BOX_BG

        self.text_surface = self.font.render(self.text, True, self.font_color)
        self.text_rect = self.text_surface.get_rect(center=(self.rect_width // 2, self.rect_height // 2))
        self.rect = pygame.Rect(0, 0, self.rect_width, self.rect_height)
        self.rect.center = self.pos

    def draw(self, surface):
        pygame.draw.rect(surface, THEME_TEXT, self.rect, self.border_thickness, border_radius=18)
        pygame.draw.rect(surface, self.bg_color, self.rect.inflate(-self.border_thickness * 2, -self.border_thickness * 2), border_radius=15)
        surface.blit(self.text_surface, (self.rect.centerx - self.text_rect.width // 2, self.rect.centery - self.text_rect.height // 2))

    def reset_position(self):
        self.pos = list(self.original_pos)
        self.rect.center = self.pos

# ---------------------- Function to Draw Category Box ----------------------
def draw_category_box(surface, category_text, font, pos):
    padding = 20
    border_thickness = 4
    text_surface = font.render(category_text, True, THEME_TEXT)
    text_rect = text_surface.get_rect()
    box_width = text_rect.width + 2 * padding
    box_height = text_rect.height + 2 * padding
    box_rect = pygame.Rect(pos[0], pos[1], box_width, box_height)
    box_rect.center = pos

    pygame.draw.rect(surface, THEME_TEXT, box_rect, border_thickness, border_radius=18)
    pygame.draw.rect(surface, BUTTON_BG, box_rect.inflate(-border_thickness * 2, -border_thickness * 2), border_radius=15)
    surface.blit(text_surface, (box_rect.centerx - text_rect.width // 2, box_rect.centery - text_rect.height // 2))

# ---------------------- Function to Draw Hearts and Score ----------------------
def draw_hearts_and_score(surface, lives, score):
    if heart_image:
        heart_x = 20
        heart_y = 20
        for i in range(lives):
            surface.blit(heart_image, (heart_x + (i * (heart_image.get_width() + 10)), heart_y))
        score_text = font_medium.render(f"Score: {score}", True, THEME_TEXT)
        score_x = 20
        score_y = heart_y + heart_image.get_height() + 10
        surface.blit(score_text, (score_x, score_y))

# ---------------------- Generate Game Items ----------------------
def generate_game_items():
    global current_category
    categories = list(game_data.keys())
    current_category = random.choice(categories)
    category_data = game_data[current_category]
    round_data = random.choice(category_data)
    items = round_data["items"]
    odd_one_out = round_data["odd_one_out"]

    random.shuffle(items)
    game_items = []
    vertical_offset = 160
    positions = [
        (screen_width // 4, screen_height // 2 - vertical_offset),
        (3 * screen_width // 4, screen_height // 2 - vertical_offset),
        (screen_width // 4, screen_height // 2 + vertical_offset),
        (3 * screen_width // 4, screen_height // 2 + vertical_offset)
    ]
    random.shuffle(positions)

    for i, item_text in enumerate(items):
        is_wrong = (item_text == odd_one_out)
        obj = DraggableItem(item_text, list(positions[i]), font_medium, is_wrong=is_wrong)
        game_items.append(obj)

    max_attempts = 100
    attempts = 0
    while check_overlap(game_items) and attempts < max_attempts:
        game_items = []
        random.shuffle(positions)
        for i, item_text in enumerate(items):
            is_wrong = (item_text == odd_one_out)
            obj = DraggableItem(item_text, list(positions[i]), font_medium, is_wrong=is_wrong)
            game_items.append(obj)
        attempts += 1

    return game_items

def check_overlap(items):
    for i in range(len(items)):
        for j in range(i + 1, len(items)):
            if items[i].rect.colliderect(items[j].rect):
                return True
    return False

game_items = generate_game_items()


# Levels & Session Integration for Odd One Out
GAME_ID_ODD = "OddOneOut"  # Unique game ID for Odd One Out

# Initialize the player's progress record (creates one if it doesn't exist)
levels.init_player_progress(USER_ID, GAME_ID_ODD)
base_progress = levels.get_player_progress(USER_ID, GAME_ID_ODD)
base_level = base_progress["level"] if base_progress and "level" in base_progress else 0

# Start a game session and log the event.
session_id = sessions.start_game_session(USER_ID, GAME_ID_ODD, "odd_one_out")
logs.log_event(USER_ID, "game_start", f"Game session {session_id} started for {GAME_ID_ODD}")


# ---------------------- Game States ----------------------
state = "loading"  # "loading", "landing", "game", "pause", "game_over"
loading_start_time = pygame.time.get_ticks()
loading_duration = 2000  # 2 seconds
loading_bg_image = None
try:
    script_dir = os.path.dirname(os.path.abspath(__file__))
    image_path = os.path.join(os.path.dirname(script_dir), 'assets', 'background', 'odd_one_out.png')
    loading_bg_image = pygame.image.load(image_path)
    loading_bg_image = pygame.transform.scale(loading_bg_image, (screen_width, screen_height))
except pygame.error as e:
    print(f"Error loading background image: {e}")
    loading_bg_image = pygame.Surface((screen_width, screen_height))
    loading_bg_image.fill(THEME_BG)

success = False
feedback_timer = 0
feedback_active = False
feedback_duration = 2000

# Uniform button sizes for menu
button_width = 300
button_height = 80
start_button_x = screen_width // 2 - button_width // 2
quit_button_x = screen_width // 2 - button_width // 2
resume_button_x = screen_width // 2 - button_width // 2
restart_button_x = screen_width // 2 - button_width // 2
quit_button_gameover_x = screen_width // 2 - button_width // 2
button_y_start = 350
button_spacing = 100

start_button = Button("Start Game", start_button_x, button_y_start, button_width, button_height,
                      BUTTON_NORMAL_COLOR, BUTTON_HOVER_COLOR, BUTTON_PRESSED_COLOR,
                      BUTTON_TEXT_COLOR, font_large, action="start")
quit_button_main = Button("Quit", quit_button_x, button_y_start + button_spacing, button_width, button_height,
                          BUTTON_NORMAL_COLOR, BUTTON_HOVER_COLOR, BUTTON_PRESSED_COLOR,
                          BUTTON_TEXT_COLOR, font_medium, action="quit_app")
resume_button = Button("Resume", resume_button_x, button_y_start, button_width, button_height,
                       BUTTON_NORMAL_COLOR, BUTTON_HOVER_COLOR, BUTTON_PRESSED_COLOR,
                       BUTTON_TEXT_COLOR, font_medium, action="resume")
quit_button_pause = Button("Quit to Menu", quit_button_x, button_y_start + button_spacing, button_width, button_height,
                           BUTTON_NORMAL_COLOR, BUTTON_HOVER_COLOR, BUTTON_PRESSED_COLOR,
                           BUTTON_TEXT_COLOR, font_medium, action="quit_menu")
restart_button = Button("Restart Game", restart_button_x, 350, button_width, button_height,
                        BUTTON_NORMAL_COLOR, BUTTON_HOVER_COLOR, BUTTON_PRESSED_COLOR,
                        BUTTON_TEXT_COLOR, font_medium, action="restart")
quit_button_gameover = Button("Quit to Menu", quit_button_gameover_x, 450, button_width, button_height,
                              BUTTON_NORMAL_COLOR, BUTTON_HOVER_COLOR, BUTTON_PRESSED_COLOR,
                              BUTTON_TEXT_COLOR, font_medium, action="quit_menu")


def player_quit():
    global running
    sessions.end_game_session(session_id, USER_ID, GAME_ID_ODD, level_increment=0)
    # Log the quit event – adjust the log call as needed.
    logs.log_event(USER_ID, "quit", f"Game session {session_id} ended by player quit with score {score}")
    running = False  # This will break the main loop.


# ---------------------- Main Loop ----------------------
running = True
while running:
    current_time = pygame.time.get_ticks()
    events = pygame.event.get()  # Get all events once per frame
    for event in events:
        if event.type == pygame.QUIT:
            running = False

    # Default cursor and pinch state for game mode
    cursor = (0, 0)
    pinch_active = False

    # ---------------------- State: Loading ----------------------
    if state == "loading":
        screen.fill(THEME_BG)
        screen.blit(loading_bg_image, (0, 0))
        if current_time - loading_start_time > loading_duration:
            state = "landing"
        pygame.display.flip()
        clock.tick(30)
        continue  # Skip the rest of the loop for this frame

    # ---------------------- State: Landing ----------------------
    if state == "landing":
        screen.fill(THEME_BG)
        draw_text(screen, "Welcome to Odd One Out!", font_large, THEME_TEXT, (screen_width // 2 - 320, 200))
        start_button.draw(screen)
        quit_button_main.draw(screen)
        for event in events:
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_s:
                    state = "game"
                    game_items = generate_game_items()
                    score = 0
                    attempts = 0
                    success = False
                    feedback_active = False
                    feedback_timer = 0
                    lives = 3
                    camera_initialized = False
                    detector_initialized = False
                elif event.key == pygame.K_q:
                    running = False
            elif event.type in [pygame.MOUSEBUTTONDOWN, pygame.MOUSEBUTTONUP, pygame.MOUSEMOTION]:
                mouse_cursor = pygame.mouse.get_pos()
                clicked = start_button.handle_input(event, mouse_cursor)
                if clicked == "start" and event.type == pygame.MOUSEBUTTONUP:
                    state = "game"
                    game_items = generate_game_items()
                    score = 0
                    attempts = 0
                    success = False
                    feedback_active = False
                    feedback_timer = 0
                    lives = 3
                    camera_initialized = False
                    detector_initialized = False
                clicked = quit_button_main.handle_input(event, mouse_cursor)
                if clicked == "quit_app" and event.type == pygame.MOUSEBUTTONUP:
                    player_quit()
                    #running = False

    # ---------------------- State: Game ----------------------
    elif state == "game":
        # Initialize camera and detector if needed
        if not camera_initialized:
            try:
                cap = cv2.VideoCapture(0)
                cap.set(3, screen_width)
                cap.set(4, screen_height)
                camera_initialized = True
            except Exception as e:
                print(f"Error initializing camera: {e}")
                state = "landing"

        if camera_initialized and not detector_initialized:
            try:
                detector = HandDetector(detectionCon=0.8)
                detector_initialized = True
            except Exception as e:
                print(f"Error initializing hand detector: {e}")
                state = "landing"

        if camera_initialized and detector_initialized:
            ret, frame = cap.read()
            if ret:
                hands, frame = detector.findHands(frame, flipType=False)
                if hands:
                    lmList = hands[0]['lmList']
                    pinch_distance, info, frame = detector.findDistance(lmList[4][:2], lmList[8][:2], frame)
                    if pinch_distance < 50:
                        pinch_active = True
                    cursor_x, cursor_y = lmList[8][:2]
                    cursor = (screen_width - cursor_x, cursor_y)
                frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                frame = np.rot90(frame)
                frame_surface = pygame.surfarray.make_surface(frame)
                screen.blit(frame_surface, (0, 0))
            else:
                print("Error reading frame")
                state = "landing"
        else:
            screen.fill(THEME_BG)
            draw_text(screen, "Camera/Hand Tracking Error", font_large, INCORRECT_COLOR, (screen_width // 2 - 300, screen_height // 2 - 50))
            pygame.display.flip()
            clock.tick(30)
            continue

        # Draw drop-off zones and instructions
        pygame.draw.rect(screen, DROP_ZONE_COLOR, drop_zone_left)
        pygame.draw.rect(screen, DROP_ZONE_COLOR, drop_zone_right)
        draw_text(screen, "Drag Here", font_small, THEME_TEXT, (drop_zone_left.centerx - 50, drop_zone_left.centery - 15))
        draw_text(screen, "Drag Here", font_small, THEME_TEXT, (drop_zone_right.centerx - 50, drop_zone_right.centery - 15))
        draw_text(screen, "Pinch the odd one out and drag it to the green zones.", font_medium, THEME_TEXT, (50, screen_height - 50))

        if current_category:
            draw_category_box(screen, current_category, font_medium, (screen_width // 2, 70))
        draw_hearts_and_score(screen, lives, score)

        # Dragging logic with offset
        if detector_initialized and pinch_active:
            for obj in game_items:
                if obj.rect.collidepoint(cursor):
                    if dragging_item is None:
                        dragging_item = obj
                        drag_offset = (cursor[0] - obj.rect.centerx, cursor[1] - obj.rect.centery)
                    break
            if dragging_item:
                new_center_x = cursor[0] - drag_offset[0]
                new_center_y = cursor[1] - drag_offset[1]
                dragging_item.pos = [new_center_x, new_center_y]
                dragging_item.rect.center = dragging_item.pos
        else:
            dragging_item = None

        for obj in game_items:
            obj.draw(screen)

        # Check drop zones for odd one out
        for obj in game_items:
            if obj.is_wrong:
                if obj.rect.colliderect(drop_zone_left) or obj.rect.colliderect(drop_zone_right):
                    success = True
                    if not feedback_active:
                        feedback_timer = pygame.time.get_ticks()
                        feedback_active = True
                        flash_color = CORRECT_COLOR
                        flash_alpha = 200
                        is_flashing = True
                        attempts += 1
                        score += 1
                        # --- LEVEL UPDATE & SCORE LOGGING SNIPPET ---
                        if USER_ID != 0:
                            try:
                                levels.update_player_progress(USER_ID, GAME_ID_ODD, additional_points=5)
                            except Exception as e:
                                print("Level update error:", e)
                            # Log the score event (using your logs module if available)
                            logs.log_event(USER_ID, "score", f"Score incremented to {score}")
                        else:
                            # For guest users, log with user id 0.
                            logs.log_event(0, "score", f"Guest score incremented to {score}")
                            pass
                        # --- END SNIPPET ---
                    break
            elif obj.rect.colliderect(drop_zone_left) or obj.rect.colliderect(drop_zone_right):
                success = False
                if not feedback_active:
                    feedback_timer = pygame.time.get_ticks()
                    feedback_active = True
                    flash_color = INCORRECT_COLOR
                    flash_alpha = 200
                    is_flashing = True
                    attempts += 1
                    lives -= 1
                break

        if feedback_active:
            feedback_text_pos = (screen_width // 2 - 200, screen_height // 2 - 80)
            if success:
                feedback_text = "Correct! Well done."
                feedback_color = CORRECT_COLOR
                if current_time - feedback_timer > feedback_duration:
                    success = False
                    feedback_active = False
                    feedback_timer = 0
                    game_items = generate_game_items()
            else:
                feedback_text = "Oops! That's not it."
                feedback_color = INCORRECT_COLOR
                for obj in game_items:
                    if obj.rect.colliderect(drop_zone_left) or obj.rect.colliderect(drop_zone_right):
                        obj.reset_position()
                if current_time - feedback_timer > feedback_duration:
                    feedback_active = False
                    feedback_timer = 0
                    success = False
                    if lives <= 0:
                        state = "game_over"
            draw_text(screen, feedback_text, font_feedback, feedback_color, feedback_text_pos)

        if is_flashing:
            flash_surface = pygame.Surface((screen_width, screen_height))
            flash_surface.fill(flash_color)
            flash_surface.set_alpha(flash_alpha)
            screen.blit(flash_surface, (0, 0))
            alpha_reduction_rate = 255 / (flash_duration / (1000 / 30))
            flash_alpha = max(0, flash_alpha - alpha_reduction_rate)
            if flash_alpha <= 0:
                is_flashing = False

        if detector_initialized and pinch_active:
            pygame.draw.circle(screen, HIGHLIGHT_COLOR, cursor, 15)

    # ---------------------- State: Pause ----------------------
    elif state == "pause":
        screen.fill(THEME_BG)
        draw_text(screen, "Game Paused", font_large, THEME_TEXT, (screen_width // 2 - 150, 250))
        resume_button.draw(screen)
        quit_button_pause.draw(screen)
        for event in events:
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_r:
                    state = "game"
                elif event.key == pygame.K_q:
                    state = "landing"
            elif event.type in [pygame.MOUSEBUTTONDOWN, pygame.MOUSEBUTTONUP, pygame.MOUSEMOTION]:
                mouse_cursor = pygame.mouse.get_pos()
                clicked = resume_button.handle_input(event, mouse_cursor)
                if clicked == "resume" and event.type == pygame.MOUSEBUTTONUP:
                    state = "game"
                clicked = quit_button_pause.handle_input(event, mouse_cursor)
                if clicked == "quit_menu" and event.type == pygame.MOUSEBUTTONUP:
                    state = "landing"

    # ---------------------- State: Game Over ----------------------
    elif state == "game_over":
        screen.fill(THEME_BG)
        draw_text(screen, "Game Over!", font_large, THEME_TEXT, (screen_width // 2 - 150, 200))
        draw_text(screen, f"Final Score: {score}", font_medium, THEME_TEXT, (screen_width // 2 - 150, 280))
        restart_button.draw(screen)
        quit_button_gameover.draw(screen)
        for event in events:
            if event.type in [pygame.MOUSEBUTTONDOWN, pygame.MOUSEBUTTONUP, pygame.MOUSEMOTION]:
                mouse_cursor = pygame.mouse.get_pos()
                clicked_restart = restart_button.handle_input(event, mouse_cursor)
                if clicked_restart == "restart" and event.type == pygame.MOUSEBUTTONUP:
                    state = "game"
                    game_items = generate_game_items()
                    score = 0
                    attempts = 0
                    lives = 3
                    success = False
                    feedback_active = False
                    feedback_timer = 0
                    camera_initialized = False
                    detector_initialized = False
                clicked_quit = quit_button_gameover.handle_input(event, mouse_cursor)
                if clicked_quit == "quit_menu" and event.type == pygame.MOUSEBUTTONUP:
                    state = "landing"

    pygame.display.update()
    clock.tick(30)

if cap and cap.isOpened():
    cap.release()
pygame.quit()