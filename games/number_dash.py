import sys
import os
import random
import json
import cv2
import pygame
import numpy as np
from cvzone.FaceMeshModule import FaceMeshDetector
import sqlite3
import datetime
from services import sessions, levels, logs, utils

current_user_path = os.path.join(os.getcwd(), "config", "current_user.json")
try:
    with open(current_user_path, "r") as f:
        current_user = json.load(f)
except Exception as e:
    # If no user data is found, default to a guest.
    current_user = {"id": 0, "userName": "Guest", "role": "player", "email": ""}
    print("No current user found; defaulting to Guest.")

USER_ID = current_user["id"]


# --------------------- Theme Settings ---------------------
THEME_BG = (0, 30, 60)           # Dark blue background for menus
THEME_TEXT = (255, 165, 0)       # Vibrant orange text

# --------------------- Pygame Setup ---------------------
pygame.init()
width, height = 1280, 720
screen = pygame.display.set_mode((width, height))
pygame.display.set_caption("Number Dash")
clock = pygame.time.Clock()

# Pre-load the background image so it appears immediately.
script_dir = os.path.dirname(os.path.abspath(__file__))
bg_path = os.path.join(script_dir, "..", "assets", "background", "number_dash.jpeg")
bg_image = pygame.image.load(bg_path).convert()
bg_image = pygame.transform.scale(bg_image, (width, height))

# Playful fonts for a kid-friendly look.
font_large = pygame.font.SysFont("Comic Sans MS", 80)
font_medium = pygame.font.SysFont("Comic Sans MS", 60)
font_small = pygame.font.SysFont("Comic Sans MS", 40)

# --------------------- Button Class ---------------------
class Button:
    def __init__(self, text, x, y, width, height, action=None):
        self.text = text
        self.rect = pygame.Rect(x, y, width, height)
        self.action = action

    def draw(self, surface):
        pygame.draw.rect(surface, THEME_TEXT, self.rect, border_radius=10)
        pygame.draw.rect(surface, THEME_BG, self.rect, 3, border_radius=10)
        text_surface = font_small.render(self.text, True, THEME_BG)
        text_rect = text_surface.get_rect(center=self.rect.center)
        surface.blit(text_surface, text_rect)

    def is_clicked(self, pos):
        return self.rect.collidepoint(pos)

# --------------------- Menu Layout Functions ---------------------
def get_main_menu_buttons():
    btn_width, btn_height = 400, 100
    toggle_diff_btn = Button("Difficulty: " + difficulty.capitalize(), width // 2 - btn_width // 2, 150, btn_width, btn_height, action="toggle_difficulty")
    start_btn = Button("Start Game", width // 2 - btn_width // 2, 270, btn_width, btn_height, action="start")
    highscore_btn = Button("Highscores", width // 2 - btn_width // 2, 390, btn_width, btn_height, action="highscores")
    quit_btn = Button("Quit", width // 2 - btn_width // 2, 510, btn_width, btn_height, action="quit")
    return [toggle_diff_btn, start_btn, highscore_btn, quit_btn]

def get_pause_menu_buttons():
    btn_width, btn_height = 400, 100
    resume_btn = Button("Resume", width // 2 - btn_width // 2, 300, btn_width, btn_height, action="resume")
    quit_menu_btn = Button("Quit to Menu", width // 2 - btn_width // 2, 420, btn_width, btn_height, action="quit_menu")
    return [resume_btn, quit_menu_btn]

def get_gameover_menu_buttons():
    btn_width, btn_height = 400, 100
    restart_btn = Button("Restart", width // 2 - btn_width // 2, 300, btn_width, btn_height, action="restart")
    quit_menu_btn = Button("Quit to Menu", width // 2 - btn_width // 2, 420, btn_width, btn_height, action="quit_menu")
    return [restart_btn, quit_menu_btn]

def get_highscore_menu_buttons():
    btn_width, btn_height = 400, 100
    back_btn = Button("Back", width // 2 - btn_width // 2, 600, btn_width, btn_height, action="back")
    return [back_btn]

# --------------------- Loading Screen Function ---------------------
def draw_loading_screen():
    screen.blit(bg_image, (0, 0))
    overlay = pygame.Surface((width, height), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, 100))
    screen.blit(overlay, (0, 0))
    loading_title = font_large.render("Number Dash", True, THEME_TEXT)
    loading_message = font_small.render("Loading... Please wait.", True, THEME_TEXT)
    screen.blit(loading_title, loading_title.get_rect(center=(width // 2, height // 2 - 50)))
    screen.blit(loading_message, loading_message.get_rect(center=(width // 2, height // 2 + 20)))
    pygame.display.update()

# --------------------- Highscore Functions ---------------------
HIGHSCORE_FILE = os.path.join(script_dir, "..", "config", "number_dash_highscores.json")

def load_highscores():
    highscores = []
    if os.path.exists(HIGHSCORE_FILE):
        try:
            with open(HIGHSCORE_FILE, "r") as f:
                data = json.load(f)
                if isinstance(data, list):
                    highscores = data
        except (FileNotFoundError, json.JSONDecodeError):
            highscores = []
    return highscores

def save_highscores(highscores):
    config_dir = os.path.dirname(HIGHSCORE_FILE)
    if not os.path.exists(config_dir):
        os.makedirs(config_dir)
    with open(HIGHSCORE_FILE, "w") as f:
        json.dump(highscores, f, indent=4)

def add_highscore(name, score_val):
    highscores = load_highscores()
    highscores.append({"name": name, "score": score_val})
    highscores.sort(key=lambda x: x["score"], reverse=True)
    save_highscores(highscores[:10])

# --------------------- Level Display Function ---------------------
def draw_level_display(surface, level):
    global width
    padding = 10
    level_text = f"Level: {level}"
    level_surface = font_small.render(level_text, True, (255, 255, 255))
    rect = level_surface.get_rect()
    rect.width += 2 * padding
    rect.height += 2 * padding
    rect.topright = (width - 20, 20)
    pygame.draw.rect(surface, THEME_TEXT, rect, border_radius=10)
    inner_rect = rect.inflate(-padding*2, -padding*2)
    pygame.draw.rect(surface, THEME_BG, inner_rect, border_radius=10)
    surface.blit(level_surface, level_surface.get_rect(center=rect.center))

# --------------------- Game Variables & Assets ---------------------
difficulty = "easy"  # "easy" or "normal" (set via main menu toggle)
lives = 3
score = 0
speed = 5

heart_path = os.path.join(script_dir, "..", "assets", "heart.png")
heart_image = pygame.image.load(heart_path).convert_alpha()
heart_width = heart_image.get_width()

# --------------------- Camera Setup ---------------------
cap = cv2.VideoCapture(0)
cap.set(3, width)
cap.set(4, height)
detector = FaceMeshDetector(maxFaces=1)
idList = [0, 17, 78, 292]

# --------------------- Number Generation ---------------------
def generate_number_object():
    number = random.randint(1, 20)
    is_odd = (number % 2 != 0)
    num_surface = font_large.render(str(number), True, (255, 255, 255))
    rect = num_surface.get_rect()
    x_pos = random.randint(50, width - rect.width - 50)
    rect.topleft = (x_pos, 0)
    return number, is_odd, num_surface, rect

def reset_number_object():
    global currentNumber, currentIsOdd, currentNumSurface, currentRect, current_prompt
    currentNumber, currentIsOdd, currentNumSurface, currentRect = generate_number_object()
    current_prompt = random.choice(["Odd", "Even"])

reset_number_object()
highscore_name_input = ""

# --------------------- Levels and Session Integration ---------------------
GAME_ID_NUMDASH = "NumberDash"  # Unique identifier for Number Dash
levels.init_player_progress(USER_ID, GAME_ID_NUMDASH)
base_progress = levels.get_player_progress(USER_ID, GAME_ID_NUMDASH)
base_level = base_progress["level"] if base_progress else 0
session_id = sessions.start_game_session(USER_ID, GAME_ID_NUMDASH, "NumberDash")
logs.log_event(USER_ID, "game_start", f"Game session {session_id} started for {GAME_ID_NUMDASH}")

# --------------------- State Management ---------------------
game_state = "loading"  # Allowed states: "loading", "main_menu", "playing", "paused", "gameover", "enter_highscore", "highscore"
loading_start_time = pygame.time.get_ticks()

# --------------------- Main Loop ---------------------
while True:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            pygame.quit()
            sys.exit()

        if game_state == "main_menu":
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                pos_mouse = pygame.mouse.get_pos()
                for button in get_main_menu_buttons():
                    if button.is_clicked(pos_mouse):
                        if button.action == "toggle_difficulty":
                            difficulty = "normal" if difficulty == "easy" else "easy"
                        elif button.action == "start":
                            game_state = "playing"
                            lives = 3
                            score = 0
                            speed = 5
                            reset_number_object()
                        elif button.action == "highscores":
                            game_state = "highscore"
                        elif button.action == "quit":
                            pygame.quit()
                            sys.exit()

        elif game_state == "paused":
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                pos_mouse = pygame.mouse.get_pos()
                for button in get_pause_menu_buttons():
                    if button.is_clicked(pos_mouse):
                        if button.action == "resume":
                            game_state = "playing"
                        elif button.action == "quit_menu":
                            game_state = "main_menu"
            if event.type == pygame.KEYDOWN:
                if event.key in (pygame.K_ESCAPE, pygame.K_SPACE):
                    game_state = "playing"

        elif game_state == "gameover":
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                pos_mouse = pygame.mouse.get_pos()
                for button in get_gameover_menu_buttons():
                    if button.is_clicked(pos_mouse):
                        if button.action == "restart":
                            game_state = "playing"
                            lives = 3
                            score = 0
                            speed = 5
                            reset_number_object()
                        elif button.action == "quit_menu":
                            game_state = "main_menu"
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    game_state = "gameover"

        elif game_state == "enter_highscore":
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    game_state = "gameover"
                    highscore_name_input = ""
                elif event.key == pygame.K_BACKSPACE:
                    highscore_name_input = highscore_name_input[:-1]
                elif event.key == pygame.K_RETURN:
                    if highscore_name_input.strip() != "":
                        add_highscore(highscore_name_input.strip(), score)
                    highscore_name_input = ""
                    game_state = "gameover"
                else:
                    if event.unicode.isalnum() or event.unicode in " _-":
                        highscore_name_input += event.unicode

        elif game_state == "highscore":
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                pos_mouse = pygame.mouse.get_pos()
                for button in get_highscore_menu_buttons():
                    if button.is_clicked(pos_mouse):
                        if button.action == "back":
                            game_state = "main_menu"
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    game_state = "main_menu"

        elif game_state == "playing":
            if event.type == pygame.KEYDOWN:
                if event.key in (pygame.K_ESCAPE, pygame.K_SPACE, pygame.K_p):
                    game_state = "paused"

    # --------------------- State-based Drawing ---------------------
    if game_state == "loading":
        draw_loading_screen()
        if pygame.time.get_ticks() - loading_start_time > 2000:
            game_state = "main_menu"

    elif game_state == "main_menu":
        screen.fill(THEME_BG)
        title_text = font_large.render("Main Menu", True, THEME_TEXT)
        screen.blit(title_text, title_text.get_rect(center=(width // 2, 80)))
        for button in get_main_menu_buttons():
            button.draw(screen)

    elif game_state == "highscore":
        screen.fill(THEME_BG)
        title_text = font_large.render("Highscores", True, THEME_TEXT)
        screen.blit(title_text, title_text.get_rect(center=(width // 2, 80)))
        highscores = load_highscores()
        y_offset = 160
        for idx, entry in enumerate(highscores[:10], start=1):
            hs_text = font_medium.render(f"{idx}. {entry['name']} - {entry['score']}", True, THEME_TEXT)
            screen.blit(hs_text, (width // 2 - hs_text.get_width() // 2, y_offset))
            y_offset += 60
        for button in get_highscore_menu_buttons():
            button.draw(screen)

    elif game_state == "playing":
        screen.fill((0, 0, 0))
        success, img = cap.read()
        if not success:
            break
        img = cv2.flip(img, 1)
        img, faces = detector.findFaceMesh(img, draw=False)
        frameRGB = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        frame_surface = pygame.image.frombuffer(frameRGB.tobytes(), (frameRGB.shape[1], frameRGB.shape[0]), "RGB")
        screen.blit(frame_surface, (0, 0))

        currentRect.y += speed
        screen.blit(currentNumSurface, currentRect)

        if difficulty == "easy":
            correct = (currentIsOdd and current_prompt == "Odd") or (not currentIsOdd and current_prompt == "Even")
            if correct:
                outline_color = (0, 255, 0)
                if faces:
                    face = faces[0]
                    face_x, face_y = np.mean([face[i][0:2] for i in idList], axis=0)
                    pygame.draw.line(screen, (0, 255, 0), (face_x, face_y), currentRect.center, 3)
            else:
                outline_color = (255, 0, 0)
            pygame.draw.rect(screen, outline_color, currentRect, 3)

        for i in range(lives):
            screen.blit(heart_image, (10 + i * (heart_width + 5), 10))

        score_display = font_medium.render(f"Score: {score}", True, (240, 240, 255))
        screen.blit(score_display, (width - 250, 10))
        prompt_display = font_medium.render(current_prompt, True, (0, 191, 255))
        screen.blit(prompt_display, (width // 2 - 50, 10))

        if faces:
            face = faces[0]
            face_x, face_y = np.mean([face[i][0:2] for i in idList], axis=0)
            if currentRect.collidepoint(face_x, face_y):
                if (currentIsOdd and current_prompt == "Odd") or (not currentIsOdd and current_prompt == "Even"):
                    score += 1
                    # Update level progress: add 5 points per correct answer.
                    levels.update_player_progress(USER_ID, GAME_ID_NUMDASH, 5)
                    logs.log_event(USER_ID, "score", f"Score incremented to {score}")
                else:
                    lives -= 1
                reset_number_object()

        if currentRect.y > height:
            if difficulty == "normal":
                if (currentIsOdd and current_prompt == "Odd") or (not currentIsOdd and current_prompt == "Even"):
                    lives -= 1
            reset_number_object()

        if lives <= 0:
            if score > 0:
                highs = load_highscores()
                if len(highs) < 10 or score > highs[-1]["score"]:
                    game_state = "enter_highscore"
                else:
                    game_state = "gameover"
            else:
                game_state = "gameover"

        # --------------------- Draw Level Display ---------------------
        current_progress = levels.get_player_progress(USER_ID, GAME_ID_NUMDASH)
        current_level = current_progress["level"] if current_progress else base_level
        draw_level_display(screen, current_level)

    elif game_state == "paused":
        screen.fill(THEME_BG)
        pause_text = font_large.render("Paused", True, THEME_TEXT)
        screen.blit(pause_text, pause_text.get_rect(center=(width // 2, 100)))
        for button in get_pause_menu_buttons():
            button.draw(screen)

    elif game_state == "gameover":
        screen.fill(THEME_BG)
        gameover_text = font_large.render("Game Over", True, THEME_TEXT)
        final_score_text = font_medium.render(f"Final Score: {score}", True, THEME_TEXT)
        screen.blit(gameover_text, gameover_text.get_rect(center=(width // 2, 100)))
        screen.blit(final_score_text, final_score_text.get_rect(center=(width // 2, 200)))
        for button in get_gameover_menu_buttons():
            button.draw(screen)

    elif game_state == "enter_highscore":
        screen.fill(THEME_BG)
        prompt_text = font_medium.render("Enter your name:", True, THEME_TEXT)
        screen.blit(prompt_text, prompt_text.get_rect(center=(width // 2, 200)))
        input_box = pygame.Rect(width // 2 - 200, 260, 400, 60)
        pygame.draw.rect(screen, THEME_TEXT, input_box, 3)
        name_surface = font_medium.render(highscore_name_input, True, THEME_TEXT)
        screen.blit(name_surface, (input_box.x + 10, input_box.y + 10))
        instructions = font_small.render("Press Enter to submit, Esc to cancel", True, THEME_TEXT)
        screen.blit(instructions, instructions.get_rect(center=(width // 2, 350)))

    pygame.display.update()
    clock.tick(30)

pygame.quit()
cap.release()
