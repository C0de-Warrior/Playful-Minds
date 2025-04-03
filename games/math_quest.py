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

# Define USER_ID for convenience
USER_ID = current_user["id"]

# --------------------- Theme Settings ---------------------
# Green-dominant palette for the math game.
THEME_BG = (200, 255, 200)
THEME_TEXT = (0, 100, 0)
BUTTON_BG = (240, 255, 240)
BUTTON_TEXT = (0, 100, 0)
HIGHLIGHT_COLOR = (34, 139, 34)
CHOICE_BOX_BG = (230, 255, 230)
CORRECT_COLOR = (0, 255, 0)
INCORRECT_COLOR = (255, 0, 0)
DROP_ZONE_COLOR = (144, 238, 144)

# ---------------------- Initialization ----------------------
pygame.init()
screen_width, screen_height = 1280, 720
screen = pygame.display.set_mode((screen_width, screen_height))
pygame.display.set_caption("Math Quest")
clock = pygame.time.Clock()

# Define fonts for text rendering
font_large = pygame.font.SysFont("Arial", 60)
font_medium = pygame.font.SysFont("Arial", 40)
font_small = pygame.font.SysFont("Arial", 28)
font_feedback = pygame.font.SysFont("Arial", 72, bold=True)

# Colors
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)

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
current_category = ""
current_question = ""
dragging_item = None
drag_offset = (0, 0)
lives = 3
heart_image = None
heart_scale = 0.12
answer_submitted = False  # Flag to track if an answer has been submitted

# Learning measurement metrics (tracked internally but not shown)
questions_answered = 0
correct_answers = 0
total_response_time = 0
question_start_time = 0

# Feedback variables
flash_color = None
flash_alpha = 0
flash_duration = 200
feedback_timer = 0
feedback_active = False
new_question_flag = False  # if True, a new question will be loaded

# ---------------------- Load Heart Image ----------------------
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

# ---------------------- Background Image ----------------------
loading_bg_image = None
try:
    script_dir = os.path.dirname(os.path.abspath(__file__))
    image_path = os.path.join(os.path.dirname(script_dir), 'assets', 'background', 'maths.png')
    loading_bg_image = pygame.image.load(image_path)
    loading_bg_image = pygame.transform.scale(loading_bg_image, (screen_width, screen_height))
except pygame.error as e:
    print(f"Error loading background image: {e}")
    loading_bg_image = pygame.Surface((screen_width, screen_height))
    loading_bg_image.fill(THEME_BG)

# ---------------------- Drop Zones (Green Bars) ----------------------
drop_zone_width = 150
drop_zone_left = pygame.Rect(0, 0, drop_zone_width, screen_height)
drop_zone_right = pygame.Rect(screen_width - drop_zone_width, 0, drop_zone_width, screen_height)

# ---------------------- Game Data ----------------------
game_data = {
    "Addition": [
        {"question": "1 + 2", "correct": "3", "wrong": ["2", "4", "5"]},
        {"question": "2 + 3", "correct": "5", "wrong": ["4", "6", "7"]},
        {"question": "3 + 4", "correct": "7", "wrong": ["6", "8", "9"]}
    ],
    "Subtraction": [
        {"question": "5 - 2", "correct": "3", "wrong": ["2", "4", "5"]},
        {"question": "6 - 3", "correct": "3", "wrong": ["2", "4", "5"]},
        {"question": "8 - 3", "correct": "5", "wrong": ["4", "6", "7"]}
    ],
    "Numbers to Words": [
        {"question": "3", "correct": "Three", "wrong": ["Two", "Four", "Five"]},
        {"question": "7", "correct": "Seven", "wrong": ["Six", "Eight", "Nine"]},
        {"question": "5", "correct": "Five", "wrong": ["Four", "Six", "Seven"]}
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
    def __init__(self, text, pos, font, is_correct=False):
        self.text = text
        self.pos = list(pos)
        self.font = font
        self.is_correct = is_correct
        self.original_pos = tuple(pos)
        self.padding = 20
        self.border_thickness = 4
        self.rect_width = 200
        self.rect_height = 120
        self.bg_color = CHOICE_BOX_BG

        self.text_surface = self.font.render(self.text, True, THEME_TEXT)
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

# ---------------------- Function to Draw Question Box ----------------------
def draw_question_box(surface, question_text, font, pos):
    padding = 20
    border_thickness = 4
    text_surface = font.render(question_text, True, THEME_TEXT)
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

# ---------------------- Level Display ----------------------
def draw_level_display(current_level):
    level_text = f"Level: {current_level}"
    text_surface = font_small.render(level_text, True, THEME_BG)
    padding_x, padding_y = 10, 5
    rect_width = text_surface.get_width() + 2 * padding_x
    rect_height = text_surface.get_height() + 2 * padding_y
    rect_x = screen_width - rect_width - 20
    rect_y = 20
    pygame.draw.rect(screen, THEME_TEXT, (rect_x, rect_y, rect_width, rect_height), border_radius=10)
    text_rect = text_surface.get_rect(center=(rect_x + rect_width // 2, rect_y + rect_height // 2))
    screen.blit(text_surface, text_rect)

# ---------------------- Generate Game Items ----------------------
def generate_game_items():
    global current_category, current_question, question_start_time, answer_submitted
    categories = list(game_data.keys())
    current_category = random.choice(categories)
    question_data = random.choice(game_data[current_category])
    current_question = question_data["question"]
    answers = []
    answers.append((question_data["correct"], True))
    for wrong_ans in question_data["wrong"]:
        answers.append((wrong_ans, False))
    random.shuffle(answers)
    positions = [
        (screen_width // 4, screen_height // 2 - 150),
        (3 * screen_width // 4, screen_height // 2 - 150),
        (screen_width // 4, screen_height // 2 + 150),
        (3 * screen_width // 4, screen_height // 2 + 150)
    ]
    items = []
    for i, (ans_text, is_correct) in enumerate(answers):
        obj = DraggableItem(ans_text, list(positions[i]), font_medium, is_correct=is_correct)
        items.append(obj)
    question_start_time = pygame.time.get_ticks()
    answer_submitted = False
    return items

game_items = generate_game_items()

# ---------------------- Levels & Session Integration ----------------------
GAME_ID_MATH = "MathQuest"  # Unique identifier for Math Quest
levels.init_player_progress(USER_ID, GAME_ID_MATH)
base_progress = levels.get_player_progress(USER_ID, GAME_ID_MATH)
base_level = base_progress["level"] if base_progress and "level" in base_progress else 0
session_id = sessions.start_game_session(USER_ID, GAME_ID_MATH, "math_quest")
logs.log_event(USER_ID, "game_start", f"Game session {session_id} started for {GAME_ID_MATH}")
# ---------------------- Game States ----------------------
state = "loading"  # "loading", "landing", "game", "pause", "game_over"
loading_start_time = pygame.time.get_ticks()
loading_duration = 2000

# ---------------------- Menu Buttons ----------------------
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
    sessions.end_game_session(session_id, USER_ID, GAME_ID_MATH, level_increment=0)
    logs.log_event(USER_ID, "quit", f"Game session {session_id} ended by player quit with score {score}")
    running = False  # This will break the main loop


# ---------------------- Main Loop ----------------------
running = True
while running:
    current_time = pygame.time.get_ticks()
    events = pygame.event.get()
    for event in events:
        if event.type == pygame.QUIT:
            running = False

    # Default cursor and pinch state.
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
        continue

    # ---------------------- State: Landing ----------------------
    if state == "landing":
        screen.fill(THEME_BG)
        draw_text(screen, "Welcome to Maths Quest!", font_large, THEME_TEXT, (screen_width//2 - 400, 200))
        start_button.draw(screen)
        quit_button_main.draw(screen)
        for event in events:
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_s:
                    state = "game"
                    game_items = generate_game_items()
                    score = 0
                    feedback_active = False
                    feedback_timer = 0
                    lives = 3
                    camera_initialized = False
                    detector_initialized = False
                    questions_answered = 0
                    correct_answers = 0
                    total_response_time = 0
                elif event.key == pygame.K_q:
                    running = False
            elif event.type in [pygame.MOUSEBUTTONDOWN, pygame.MOUSEBUTTONUP, pygame.MOUSEMOTION]:
                mouse_cursor = pygame.mouse.get_pos()
                clicked = start_button.handle_input(event, mouse_cursor)
                if clicked == "start" and event.type == pygame.MOUSEBUTTONUP:
                    state = "game"
                    game_items = generate_game_items()
                    score = 0
                    feedback_active = False
                    feedback_timer = 0
                    lives = 3
                    camera_initialized = False
                    detector_initialized = False
                    questions_answered = 0
                    correct_answers = 0
                    total_response_time = 0
                clicked = quit_button_main.handle_input(event, mouse_cursor)
                if clicked == "quit_app" and event.type == pygame.MOUSEBUTTONUP:
                    player_quit()
                    running = False
        pygame.display.update()
        clock.tick(30)

    # ---------------------- State: Game ----------------------
    elif state == "game":
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
            draw_text(screen, "Camera/Hand Tracking Error", font_large, INCORRECT_COLOR, (screen_width//2 - 300, screen_height//2 - 50))
            pygame.display.update()
            clock.tick(30)
            continue

        pygame.draw.rect(screen, DROP_ZONE_COLOR, drop_zone_left)
        pygame.draw.rect(screen, DROP_ZONE_COLOR, drop_zone_right)
        draw_question_box(screen, f"{current_category}: {current_question}", font_medium, (screen_width//2, 100))
        draw_text(screen, "Drag the CORRECT answer into the green zones!", font_medium, THEME_TEXT, (50, screen_height - 50))
        draw_hearts_and_score(screen, lives, score)

        if detector_initialized:
            if pinch_active:
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
                if dragging_item:
                    collides_left = dragging_item.rect.colliderect(drop_zone_left)
                    collides_right = dragging_item.rect.colliderect(drop_zone_right)
                    in_drop_zone = collides_left or collides_right
                    if in_drop_zone:
                        if not answer_submitted:
                            answer_submitted = True
                            questions_answered += 1
                            response_time = current_time - question_start_time
                            total_response_time += response_time
                            if dragging_item.is_correct:
                                success = True
                                correct_answers += 1
                                score += 1
                                # --- LEVEL UPDATE & LOGGING SNIPPET ---
                                # (Assumes USER_ID and GAME_ID_SPELL are defined earlier in the file.)
                                if USER_ID != 0:
                                    try:
                                        levels.update_player_progress(USER_ID, GAME_ID_MATH, additional_points=1)
                                    except Exception as e:
                                        print("Level update error:", e)
                                    logs.log_event(USER_ID, "score", f"Score incremented to {score}")
                                else:
                                    logs.log_event(0, "score", f"Guest score incremented to {score}")
                                # --- END LEVEL UPDATE & LOGGING SNIPPET ---

                                flash_color = CORRECT_COLOR
                                new_question_flag = True
                            else:
                                success = False
                                lives -= 1
                                flash_color = INCORRECT_COLOR
                                new_question_flag = False
                            feedback_timer = current_time
                            feedback_active = True
                            dragging_item = None
                        else:
                            pass
                    else:
                        dragging_item.reset_position()
                        dragging_item = None
                else:
                    dragging_item = None
        else:
            dragging_item = None

        for obj in game_items:
            obj.draw(screen)

        if feedback_active:
            feedback_text_pos = (screen_width//2 - 200, screen_height//2 - 80)
            if success:
                feedback_text = "Correct! Well done."
            else:
                feedback_text = "Oops! That's incorrect. Try again."
            draw_text(screen, feedback_text, font_feedback, flash_color, feedback_text_pos)
            if current_time - feedback_timer > flash_duration:
                feedback_active = False
                if new_question_flag:
                    game_items = generate_game_items()
                else:
                    for obj in game_items:
                        obj.reset_position()
                flash_alpha = 200
                answer_submitted = False

        if feedback_active:
            flash_surface = pygame.Surface((screen_width, screen_height))
            flash_surface.fill(flash_color)
            flash_surface.set_alpha(flash_alpha)
            screen.blit(flash_surface, (0, 0))
            alpha_reduction_rate = 255 / (flash_duration / (1000 / 30))
            flash_alpha = max(0, flash_alpha - alpha_reduction_rate)
            if flash_alpha <= 0:
                flash_alpha = 0

        if detector_initialized and pinch_active:
            pygame.draw.circle(screen, HIGHLIGHT_COLOR, cursor, 15)

        # --------------------- Draw Level Display ---------------------
        # Get current progress for Math Quest.
        current_progress = levels.get_player_progress(current_user["id"], GAME_ID_MATH)
        current_level = current_progress["level"] if current_progress else base_level
        draw_level_display(current_level)

        if lives <= 0:
            state = "game_over"

        for event in events:
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    state = "pause"

        pygame.display.update()
        clock.tick(30)

    # ---------------------- State: Pause ----------------------
    elif state == "pause":
        screen.fill(THEME_BG)
        draw_text(screen, "Game Paused", font_large, THEME_TEXT, (screen_width//2 - 150, 250))
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
        draw_text(screen, "Game Over!", font_large, THEME_TEXT, (screen_width//2 - 150, 200))
        draw_text(screen, f"Final Score: {score}", font_medium, THEME_TEXT, (screen_width//2 - 150, 280))
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
                    feedback_active = False
                    feedback_timer = 0
                    camera_initialized = False
                    detector_initialized = False
                    questions_answered = 0
                    correct_answers = 0
                    total_response_time = 0
                clicked_quit = quit_button_gameover.handle_input(event, mouse_cursor)
                if clicked_quit == "quit_menu" and event.type == pygame.MOUSEBUTTONUP:
                    state = "landing"

    pygame.display.update()
    clock.tick(30)

if cap and cap.isOpened():
    cap.release()
pygame.quit()
