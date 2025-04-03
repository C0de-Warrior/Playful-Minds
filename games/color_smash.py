import os
import random
import cv2
import json
import pygame
import numpy as np
from cvzone.FaceMeshModule import FaceMeshDetector
import cvzone
import sys
import sqlite3
import datetime
from services import sessions, levels, logs, utils

current_user_path = os.path.join(os.getcwd(), "config", "current_user.json")
try:
    with open(current_user_path, "r") as f:
        current_user = json.load(f)
except Exception as e:
    current_user = {"id": 0, "userName": "Guest", "role": "player", "email": ""}
    print("No current user found; defaulting to Guest.")


# --------------------- Theme Settings ---------------------
THEME_BG = (173, 216, 230)  # Light blue background (RGB)
THEME_TEXT = (0, 0, 128)    # Dark blue text (RGB)
BUTTON_COLOR = (135, 206, 235)  # Light sky blue for buttons
BUTTON_TEXT_COLOR = (255, 255, 255)  # White text on buttons

# --------------------- Global Game Identifier ---------------------
GAME_ID = "ColorCatcherGame"

# --------------------- Pygame Setup ---------------------
pygame.init()
pygame.key.set_repeat(0)
width, height = 1280, 720
screen = pygame.display.set_mode((width, height))
pygame.display.set_caption("Color Catcher")
clock = pygame.time.Clock()

# Use a playful font for a kid-friendly look.
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
        pygame.draw.rect(surface, BUTTON_COLOR, self.rect, border_radius=10)
        text_surface = font_small.render(self.text, True, BUTTON_TEXT_COLOR)
        text_rect = text_surface.get_rect(center=self.rect.center)
        surface.blit(text_surface, text_rect)

    def is_clicked(self, pos):
        return self.rect.collidepoint(pos)

# --------------------- Button Layout Functions ---------------------
def get_landing_buttons():
    buttons = []
    btn_width_diff, btn_height_diff = 200, 70
    diff_buttons_y = 260
    easy_btn = Button("Easy", width // 4 - btn_width_diff // 2, diff_buttons_y, btn_width_diff, btn_height_diff, action="easy")
    normal_btn = Button("Normal", 3 * width // 4 - btn_width_diff // 2, diff_buttons_y, btn_width_diff, btn_height_diff, action="normal")
    buttons.extend([easy_btn, normal_btn])
    btn_width_main, btn_height_main = 300, 80
    main_buttons_y_start = 400
    start_btn = Button("Start Game", width // 2 - btn_width_main // 2, main_buttons_y_start, btn_width_main, btn_height_main, action="start")
    highscore_btn = Button("Highscores", width // 2 - btn_width_main // 2, main_buttons_y_start + 100, btn_width_main, btn_height_main, action="highscores")
    quit_btn = Button("Quit", width // 2 - btn_width_main // 2, main_buttons_y_start + 200, btn_width_main, btn_height_main, action="quit")
    buttons.extend([start_btn, highscore_btn, quit_btn])
    return buttons

def get_pause_buttons():
    btn_width, btn_height = 300, 80
    resume_btn = Button("Resume", width // 2 - btn_width // 2, height // 2 - 100, btn_width, btn_height, action="resume")
    restart_btn = Button("Restart", width // 2 - btn_width // 2, height // 2, btn_width, btn_height, action="restart")
    quit_menu_btn = Button("Quit to Menu", width // 2 - btn_width // 2, height // 2 + 100, btn_width, btn_height, action="quit_menu")
    return [resume_btn, restart_btn, quit_menu_btn]

def get_gameover_buttons():
    btn_width, btn_height = 300, 80
    restart_btn = Button("Restart", width // 2 - btn_width // 2, height // 2 + 20, btn_width, btn_height, action="restart")
    quit_menu_btn = Button("Quit to Menu", width // 2 - btn_width // 2, height // 2 + 120, btn_width, btn_height, action="quit_menu")
    highscore_btn = Button("Enter Highscore", width // 2 - btn_width // 2, height // 2 + 220, btn_width, btn_height, action="enter_highscore")
    return [restart_btn, quit_menu_btn, highscore_btn]

def get_highscore_buttons():
    btn_width, btn_height = 300, 80
    return [Button("Return to Menu", width // 2 - btn_width // 2, height - 120, btn_width, btn_height, action="return_menu")]

def get_posthighscore_buttons():
    btn_width, btn_height = 300, 80
    return [Button("Return to Game Over", width // 2 - btn_width // 2, height // 2 + 100, btn_width, btn_height, action="return_gameover")]

# --------------------- Load Heart Image for Lives ---------------------
script_dir = os.path.dirname(os.path.abspath(__file__))
heart_path = os.path.join(script_dir, "..", "assets", "heart.png")
heart_image = pygame.image.load(heart_path).convert_alpha()
heart_width = heart_image.get_width()
heart_height = heart_image.get_height()

# --------------------- Difficulty and Game Variables ---------------------
difficulty = "easy"
lives = 3
score = 0

target_colors = {
    "Red": (0, 0, 255),
    "Green": (0, 255, 0),
    "Blue": (255, 0, 0),
    "Yellow": (0, 255, 255)
}
target_color_name, target_color_value = random.choice(list(target_colors.items()))

# --------------------- Camera Setup ---------------------
config_path = os.path.join(script_dir, "..", "config", "settings.json")
with open(config_path) as f:
    config = json.load(f)
cam_index = config.get('camera_index', 0)
cap = cv2.VideoCapture(cam_index)
cap.set(3, width)
cap.set(4, height)

# --------------------- FaceMesh Detector ---------------------
detector = FaceMeshDetector(maxFaces=1)
idList = [0, 17, 78, 292]

# --------------------- Falling Object Setup ---------------------
pos = [random.randint(100, width - 100), 0]
radius = 40
isTarget = True
currentColor = target_color_value

def resetObject(current_target_color):
    global pos, isTarget, currentColor
    pos[0] = random.randint(100, width - 100)
    pos[1] = 0
    if random.random() < 0.5:
        isTarget = True
        currentColor = current_target_color
    else:
        isTarget = False
        non_target_list = [color for name, color in target_colors.items() if color != current_target_color]
        currentColor = random.choice(non_target_list) if non_target_list else current_target_color
    return currentColor

currentColor = resetObject(target_color_value)
speed = 5

# --------------------- Highscore Handling ---------------------
def update_highscores(score):
    config_dir = os.path.join(script_dir, "..", "config")
    if not os.path.exists(config_dir):
        os.makedirs(config_dir)
    filename = os.path.join(config_dir, "highscores.json")
    if os.path.exists(filename):
        try:
            with open(filename, "r") as f:
                data = json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            data = {}
    else:
        data = {}
    if GAME_ID not in data or not isinstance(data[GAME_ID], list):
        data[GAME_ID] = []
    highscores = data[GAME_ID]
    qualifies = False
    if len(highscores) < 10:
        qualifies = True
    else:
        min_score = min(entry["score"] for entry in highscores)
        if score > min_score:
            qualifies = True
    if not qualifies:
        return (False, "Score did not qualify for highscore entry.")
    name = ""
    input_active = True
    prompt = "Enter your name for highscore (ESC to cancel):"
    while input_active:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                input_active = False
                return (False, "Quit during highscore entry.")
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_RETURN:
                    input_active = False
                elif event.key == pygame.K_ESCAPE:
                    return (False, "Highscore entry cancelled.")
                else:
                    name += event.unicode
        screen.fill(THEME_BG)
        prompt_text = font_small.render(prompt, True, THEME_TEXT)
        name_text = font_medium.render(name, True, THEME_TEXT)
        screen.blit(prompt_text, prompt_text.get_rect(center=(width // 2, height // 2 - 50)))
        screen.blit(name_text, name_text.get_rect(center=(width // 2, height // 2 + 20)))
        pygame.display.update()
        clock.tick(30)
    new_entry = {"name": name.strip() if name.strip() != "" else "Anonymous", "score": score}
    highscores.append(new_entry)
    highscores = sorted(highscores, key=lambda x: x["score"], reverse=True)[:10]
    data[GAME_ID] = highscores
    with open(filename, "w") as f:
        json.dump(data, f, indent=4)
    return (True, "Highscore updated!")

def load_highscores_for_game():
    config_dir = os.path.join(script_dir, "..", "config")
    filename = os.path.join(config_dir, "highscores.json")
    try:
        with open(filename, "r") as f:
            data = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        data = {}
    if GAME_ID not in data or not isinstance(data[GAME_ID], list):
        return [{"name": "Default", "score": 0}]
    return data[GAME_ID]

# --------------------- Loading Screen ---------------------
background_path = os.path.join(script_dir, "..", "assets", "background", "color_smash.png")
if os.path.exists(background_path):
    loading_background = pygame.image.load(background_path).convert()
    loading_background = pygame.transform.scale(loading_background, (width, height))
    screen.blit(loading_background, (0, 0))
else:
    screen.fill(THEME_BG)
    print(f"Warning: Background image not found at {background_path}")
loading_title = font_large.render("Color Catcher", True, THEME_TEXT)
loading_message = font_small.render("Loading... Please wait.", True, THEME_TEXT)
screen.blit(loading_title, loading_title.get_rect(center=(width // 2, height // 2 - 50)))
screen.blit(loading_message, loading_message.get_rect(center=(width // 2, height // 2 + 20)))
pygame.display.flip()
pygame.time.delay(1000)

# --------------------- Game State Setup ---------------------
gameState = "landing"
pause_cooldown = 300
last_toggle_time = 0
hs_message = ""

# --------------------- Session & Level Tracking ---------------------
# try:
#     current_user
# except NameError:
#     current_user = {"id": 0, "firstName": "Guest"}
# base_level = db.get_player_level(current_user["id"], GAME_ID)
# session_id = sessions.start_game_session(current_user["id"], GAME_ID, "color_smash")

game_session_id = sessions.start_game_session(current_user["id"], GAME_ID, "game_play")
logs.log_event(current_user["id"], "game_start", f"Game session {game_session_id} started for {GAME_ID}")


# --------------------- Level Display ---------------------
def draw_level_display(current_level):
    level_text = f"Level: {current_level}"
    text_surface = font_small.render(level_text, True, THEME_BG)
    padding_x, padding_y = 10, 5
    rect_width = text_surface.get_width() + 2 * padding_x
    rect_height = text_surface.get_height() + 2 * padding_y
    rect_x = width - rect_width - 20
    rect_y = 20
    pygame.draw.rect(screen, THEME_TEXT, (rect_x, rect_y, rect_width, rect_height), border_radius=10)
    text_rect = text_surface.get_rect(center=(rect_x + rect_width // 2, rect_y + rect_height // 2))
    screen.blit(text_surface, text_rect)

# --------------------- Flash Effect ---------------------
flash_active = False
flash_start_time = 0
flash_duration = 300
flash_corner_width = 300
flash_corner_height = 300
tl_x, tl_y = np.meshgrid(np.arange(flash_corner_width), np.arange(flash_corner_height))
gradient_tl = 1 - np.maximum(tl_x / flash_corner_width, tl_y / flash_corner_height)
gradient_tr = 1 - np.maximum((flash_corner_width - 1 - tl_x) / flash_corner_width, tl_y / flash_corner_height)
gradient_bl = 1 - np.maximum(tl_x / flash_corner_width, (flash_corner_height - 1 - tl_y) / flash_corner_height)
gradient_br = 1 - np.maximum((flash_corner_width - 1 - tl_x) / flash_corner_width, (flash_corner_height - 1 - tl_y) / flash_corner_height)
def trigger_flash():
    global flash_active, flash_start_time
    flash_active = True
    flash_start_time = pygame.time.get_ticks()
def draw_flash_effect():
    global flash_active
    current_time = pygame.time.get_ticks()
    elapsed = current_time - flash_start_time
    if elapsed < flash_duration:
        overall_alpha = int(255 * (1 - elapsed / flash_duration))
        def create_corner_surf(gradient_array):
            surf = pygame.Surface((flash_corner_width, flash_corner_height), pygame.SRCALPHA)
            surf.fill((255, 0, 0))
            alpha_array = pygame.surfarray.pixels_alpha(surf)
            alpha_array[:] = (overall_alpha * gradient_array).astype(np.uint8)
            del alpha_array
            return surf
        tl_surf = create_corner_surf(gradient_tl)
        tr_surf = create_corner_surf(gradient_tr)
        bl_surf = create_corner_surf(gradient_bl)
        br_surf = create_corner_surf(gradient_br)
        screen.blit(tl_surf, (0, 0))
        screen.blit(tr_surf, (width - flash_corner_width, 0))
        screen.blit(bl_surf, (0, height - flash_corner_height))
        screen.blit(br_surf, (width - flash_corner_width, height - flash_corner_height))
    else:
        flash_active = False

# --------------------- Main Loop ---------------------
running = True
while running:
    current_time = pygame.time.get_ticks()
    events = pygame.event.get()
    for event in events:
        if event.type == pygame.QUIT:
            running = False
        if gameState == "playing" and event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_ESCAPE, pygame.K_SPACE):
                if current_time - last_toggle_time > pause_cooldown:
                    gameState = "paused"
                    last_toggle_time = current_time

    mouse_pos = pygame.mouse.get_pos()

    # --------------------- Landing Screen ---------------------
    if gameState == "landing":
        screen.fill(THEME_BG)
        title_text = font_large.render("Welcome to Color Catcher!", True, THEME_TEXT)
        instruct_text = font_small.render("Catch objects of the TARGET color and avoid others.", True, THEME_TEXT)
        diff_text = font_small.render("Select Difficulty:", True, THEME_TEXT)
        screen.blit(title_text, title_text.get_rect(center=(width // 2, 80)))
        screen.blit(instruct_text, instruct_text.get_rect(center=(width // 2, 160)))
        screen.blit(diff_text, diff_text.get_rect(center=(width // 2, 230)))
        landing_buttons = get_landing_buttons()
        for button in landing_buttons:
            button.draw(screen)
        pygame.display.update()
        clock.tick(30)
        for event in events:
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                for button in landing_buttons:
                    if button.is_clicked(mouse_pos):
                        if button.action == "easy":
                            difficulty = "easy"
                            gameState = "playing"
                            resetObject(target_color_value)
                            lives = 3
                            score = 0
                        elif button.action == "normal":
                            difficulty = "normal"
                            gameState = "playing"
                            resetObject(target_color_value)
                            lives = 3
                            score = 0
                        elif button.action == "start":
                            gameState = "playing"
                            resetObject(target_color_value)
                            lives = 3
                            score = 0
                        elif button.action == "highscores":
                            gameState = "view_highscores"
                        elif button.action == "quit":
                            running = False
        continue

    # --------------------- View Highscores Screen ---------------------
    if gameState == "view_highscores":
        screen.fill(THEME_BG)
        hs_list = load_highscores_for_game()
        title_text = font_large.render("Highscores", True, THEME_TEXT)
        screen.blit(title_text, title_text.get_rect(center=(width // 2, 80)))
        for i, entry in enumerate(hs_list):
            rank = i + 1
            line = f"{rank}. {entry['name']} - {entry['score']}"
            line_text = font_small.render(line, True, THEME_TEXT)
            screen.blit(line_text, (width // 4, 150 + i * 40))
        hs_buttons = get_highscore_buttons()
        for button in hs_buttons:
            button.draw(screen)
        pygame.display.update()
        clock.tick(30)
        for event in events:
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                for button in hs_buttons:
                    if button.is_clicked(mouse_pos):
                        if button.action == "return_menu":
                            gameState = "landing"
        continue

    # --------------------- Pause Screen ---------------------
    if gameState == "paused":
        screen.fill(THEME_BG)
        pause_text = font_large.render("Paused", True, THEME_TEXT)
        screen.blit(pause_text, pause_text.get_rect(center=(width // 2, height // 2 - 160)))
        pause_buttons = get_pause_buttons()
        for button in pause_buttons:
            button.draw(screen)
        pygame.display.update()
        clock.tick(30)
        for event in events:
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                for button in pause_buttons:
                    if button.is_clicked(mouse_pos):
                        if button.action == "resume":
                            gameState = "playing"
                            last_toggle_time = current_time
                        elif button.action == "restart":
                            resetObject(target_color_value)
                            gameState = "playing"
                            score = 0
                            lives = 3
                            last_toggle_time = current_time
                        elif button.action == "quit_menu":
                            gameState = "landing"
        continue

    # --------------------- Gameover Screen ---------------------
    if gameState == "playing" and lives <= 0:
        gameState = "gameover"
        continue

    if gameState == "gameover":
        screen.fill(THEME_BG)
        gameover_text = font_large.render("Game Over!", True, THEME_TEXT)
        score_text = font_medium.render(f"Score: {score}", True, THEME_TEXT)
        screen.blit(gameover_text, gameover_text.get_rect(center=(width // 2, height // 2 - 120)))
        screen.blit(score_text, score_text.get_rect(center=(width // 2, height // 2 - 40)))
        gameover_buttons = get_gameover_buttons()
        for button in gameover_buttons:
            button.draw(screen)
        pygame.display.update()
        clock.tick(30)
        for event in events:
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                for button in gameover_buttons:
                    if button.is_clicked(mouse_pos):
                        if button.action == "restart":
                            resetObject(target_color_value)
                            gameState = "playing"
                            score = 0
                            lives = 3
                        elif button.action == "quit_menu":
                            gameState = "landing"
                        elif button.action == "enter_highscore":
                            gameState = "enter_highscore"
        continue

    # --------------------- Post Highscore State ---------------------
    if gameState == "post_highscore":
        screen.fill(THEME_BG)
        msg_text = font_large.render(hs_message, True, THEME_TEXT)
        posths_buttons = get_posthighscore_buttons()
        for button in posths_buttons:
            button.draw(screen)
        screen.blit(msg_text, msg_text.get_rect(center=(width // 2, height // 2 - 50)))
        pygame.display.update()
        clock.tick(30)
        for event in events:
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                for button in posths_buttons:
                    if button.is_clicked(mouse_pos):
                        if button.action == "return_gameover":
                            gameState = "gameover"
        continue

    # --------------------- Enter Highscore State ---------------------
    if gameState == "enter_highscore":
        updated, hs_message = update_highscores(score)
        gameState = "post_highscore"
        continue

    # --------------------- Playing State ---------------------
    for event in events:
        if gameState == "playing" and not (lives <= 0) and event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_ESCAPE, pygame.K_SPACE):
                gameState = "paused"
            elif event.key == pygame.K_r:
                resetObject(target_color_value)
                gameState = "playing"
                score = 0
                lives = 3

    # --------------------- Game Screen (Playing State) ---------------------
    success, img = cap.read()
    if not success:
        break
    img = cv2.flip(img, 1)
    img, faces = detector.findFaceMesh(img, draw=False)
    center_object = (pos[0] + radius, pos[1] + radius)
    cv2.circle(img, center_object, radius, currentColor, -1)
    if difficulty == "easy":
        outline_color = (0, 255, 0) if isTarget else (0, 0, 255)
        cv2.circle(img, center_object, radius, outline_color, 3)
    indicator_width = 70
    indicator_height = 60
    indicator_x = width // 2 - indicator_width // 2
    indicator_y = 10
    b, g, r = target_color_value
    pygame_color = (r, g, b)
    target_color_name_str = list(target_colors.keys())[list(target_colors.values()).index(target_color_value)]
    text_surface = font_small.render(target_color_name_str, True, pygame_color)
    text_rect = text_surface.get_rect(center=(indicator_x + indicator_width // 2, indicator_y + indicator_height + 20))
    imgRGB = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    surface = pygame.image.frombuffer(imgRGB.tobytes(), (imgRGB.shape[1], imgRGB.shape[0]), "RGB")
    screen.blit(surface, (0, 0))
    if difficulty == "easy":
        b, g, r = target_color_value
        pygame_color_rect = (r, g, b)
        pygame.draw.rect(screen, pygame_color_rect, (indicator_x, indicator_y, indicator_width, indicator_height))
        screen.blit(text_surface, (width // 2 - text_surface.get_width() // 2, indicator_y + indicator_height + 10))
    elif difficulty == "normal":
        screen.blit(text_surface, (width // 2 - text_surface.get_width() // 2, indicator_y + indicator_height // 2))
    score_surface = font_medium.render("Score: " + str(score), True, THEME_TEXT)
    screen.blit(score_surface, (20, 20))
    for i in range(lives):
        screen.blit(heart_image, (20 + i * (heart_width + 5), 80))
    pos[1] += speed
    if pos[1] > height - 200:
        if isTarget and difficulty != "easy":
            lives -= 1
            trigger_flash()
        resetObject(target_color_value)
    if faces:
        face = faces[0]
        up = face[idList[0]]
        down = face[idList[1]]
        upDown, _ = detector.findDistance(face[idList[0]], face[idList[1]])
        leftRight, _ = detector.findDistance(face[idList[2]], face[idList[3]])
        cx, cy = (up[0] + down[0]) // 2, (up[1] + down[1]) // 2
        ratio = int((upDown / leftRight) * 100)
        distMouthObject, _ = detector.findDistance((cx, cy), (pos[0] + 50, pos[1] + 50))
        if distMouthObject < 100 and ratio > 60:
            if isTarget:
                score += 1
                # Update level progress and log the score event for non-guests.
                if current_user.get("id", 0) != 0:
                    levels.update_player_progress(current_user["id"], GAME_ID, additional_points=5)
                    logs.log_event(current_user["id"], "score", f"Score incremented to {score}")
                else:
                    logs.log_event(0, "score", f"Guest score incremented to {score}")
                target_color_name, target_color_value = random.choice(list(target_colors.items()))
                resetObject(target_color_value)
            else:
                lives -= 1
                resetObject(target_color_value)
    # --------------------- Draw Level Display ---------------------
    # Calculate current level: here, 1 level per 5 points.
    # current_level = base_level + (score // 5)
    # draw_level_display(current_level)
    if flash_active:
        draw_flash_effect()
    pygame.display.update()
    clock.tick(30)

cap.release()
pygame.quit()

# --------------------- End Session ---------------------
sessions.end_game_session(game_session_id, current_user["id"], GAME_ID, level_increment=0)
logs.log_event(current_user["id"], "game_over", f"Game session {game_session_id} ended with score {score}")

# level_increment = (base_level + (score // 5)) - base_level
# if session_id is not None:
#     sessions.end_game_session(session_id, current_user["id"], GAME_ID, level_increment)
