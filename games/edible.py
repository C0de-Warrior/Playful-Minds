import os
import random
import cv2
import json
from cvzone.FaceMeshModule import FaceMeshDetector
import cvzone
import pygame
import numpy as np
import sys
import sqlite3
import datetime
from services import sessions, levels, logs, utils
# Add this snippet after your imports
current_user_path = os.path.join(os.getcwd(), "config", "current_user.json")
try:
    with open(current_user_path, "r") as f:
        current_user = json.load(f)
except Exception as e:
    # If there is no current user file, default to a guest.
    current_user = {"id": 0, "userName": "Guest", "role": "player", "email": ""}
    print("No current user found; defaulting to Guest.")

# --------------------- Theme Settings ---------------------
THEME_BG = (255, 235, 59)  # Bright yellow background for menus
THEME_TEXT = (75, 0, 130)  # Dark purple text

# --------------------- Global Game Identifier ---------------------
GAME_ID = "EdibleGame"  # Unique identifier for this game

# --------------------- Pygame Setup ---------------------
pygame.init()
pygame.key.set_repeat(0)  # Disable key repeat.
width, height = 1280, 720
screen = pygame.display.set_mode((width, height))
pygame.display.set_caption("Edible Game")
clock = pygame.time.Clock()

# Use a playful font for a kid-friendly look.
font_large = pygame.font.SysFont("Comic Sans MS", 80)
font_medium = pygame.font.SysFont("Comic Sans MS", 60)
font_small = pygame.font.SysFont("Comic Sans MS", 40)

# --------------------- Difficulty ---------------------
difficulty = "easy"  # Default difficulty.

# --------------------- Button Class ---------------------
class Button:
    def __init__(self, text, x, y, width, height, action=None):
        self.text = text
        self.rect = pygame.Rect(x, y, width, height)
        self.action = action

    def draw(self, surface):
        # Draw button background and border
        pygame.draw.rect(surface, THEME_TEXT, self.rect, border_radius=10)
        pygame.draw.rect(surface, THEME_BG, self.rect, 3, border_radius=10)
        # Render text and center it inside the button
        text_surface = font_small.render(self.text, True, THEME_BG)
        text_rect = text_surface.get_rect(center=self.rect.center)
        surface.blit(text_surface, text_rect)

    def is_clicked(self, pos):
        return self.rect.collidepoint(pos)

# --------------------- Button Layout Functions ---------------------
def get_landing_buttons():
    buttons = []
    # Difficulty selection buttons:
    btn_width_diff, btn_height_diff = 200, 70
    diff_buttons_y = 280  # Positioned below the difficulty text.
    easy_btn = Button("Easy", width // 4 - btn_width_diff // 2, diff_buttons_y, btn_width_diff, btn_height_diff,
                      action="easy")
    normal_btn = Button("Normal", 3 * width // 4 - btn_width_diff // 2, diff_buttons_y, btn_width_diff, btn_height_diff,
                        action="normal")
    buttons.extend([easy_btn, normal_btn])
    # Main menu options buttons:
    btn_width_main, btn_height_main = 300, 80
    main_buttons_y_start = 380  # Starting y-position for main menu buttons.
    start_btn = Button("Start Game", width // 2 - btn_width_main // 2, main_buttons_y_start, btn_width_main,
                        btn_height_main, action="start")
    highscore_btn = Button("Highscores", width // 2 - btn_width_main // 2, main_buttons_y_start + 100, btn_width_main,
                            btn_height_main, action="highscores")
    quit_btn = Button("Quit", width // 2 - btn_width_main // 2, main_buttons_y_start + 200, btn_width_main,
                      btn_height_main, action="quit")
    buttons.extend([start_btn, highscore_btn, quit_btn])
    return buttons

def get_pause_buttons():
    btn_width, btn_height = 300, 80
    resume_btn = Button("Resume", width // 2 - btn_width // 2, height // 2 - 100, btn_width, btn_height,
                        action="resume")
    restart_btn = Button("Restart", width // 2 - btn_width // 2, height // 2, btn_width, btn_height, action="restart")
    quit_menu_btn = Button("Quit to Menu", width // 2 - btn_width // 2, height // 2 + 100, btn_width, btn_height,
                            action="quit_menu")
    return [resume_btn, restart_btn, quit_menu_btn]

def get_gameover_buttons():
    btn_width, btn_height = 300, 80
    restart_btn = Button("Restart", width // 2 - btn_width // 2, height // 2 + 20, btn_width, btn_height,
                        action="restart")
    quit_menu_btn = Button("Quit to Menu", width // 2 - btn_width // 2, height // 2 + 120, btn_width, btn_height,
                            action="quit_menu")
    highscore_btn = Button("Enter Highscore", width // 2 - btn_width // 2, height // 2 + 220, btn_width, btn_height,
                            action="enter_highscore")
    return [restart_btn, quit_menu_btn, highscore_btn]

def get_highscore_buttons():
    btn_width, btn_height = 300, 80
    return [Button("Return", width // 2 - btn_width // 2, height - 120, btn_width, btn_height, action="return")]

def get_posthighscore_buttons():
    btn_width, btn_height = 300, 80
    return [Button("Return", width // 2 - btn_width // 2, height // 2 + 100, btn_width, btn_height, action="return")]

# --------------------- Loading Screen ---------------------
script_dir = os.path.dirname(os.path.abspath(__file__))
background_path = os.path.join(script_dir, "..", "assets", "background", "food.jpg")
if os.path.exists(background_path):
    background_img = pygame.image.load(background_path).convert()
    background_img = pygame.transform.scale(background_img, (width, height))
    screen.blit(background_img, (0, 0))
else:
    screen.fill((0, 0, 0))

loading_title = font_large.render("Edible Game", True, THEME_TEXT)
loading_message = font_small.render("Loading... Please wait.", True, THEME_TEXT)
screen.blit(loading_title, loading_title.get_rect(center=(width // 2, height // 2 - 50)))
screen.blit(loading_message, loading_message.get_rect(center=(width // 2, height // 2 + 20)))
pygame.display.update()

# --------------------- Load Heart Image for Health Feature ---------------------
lives = 3  # Player starts with 3 lives.
heart_path = os.path.join(script_dir, "..", "assets", "heart.png")
heart_image = pygame.image.load(heart_path).convert_alpha()
heart_width = heart_image.get_width()
heart_height = heart_image.get_height()

# --------------------- Camera Setup ---------------------
# Read camera configuration from file:
with open(os.path.join(script_dir, "..", "config", "settings.json")) as f:
    config = json.load(f)
cam_index = config.get('camera_index', 0)
cap = cv2.VideoCapture(cam_index)
cap.set(3, width)
cap.set(4, height)

# --------------------- FaceMesh Detector ---------------------
detector = FaceMeshDetector(maxFaces=1)
idList = [0, 17, 78, 292]

# --------------------- Helper Function to Load Images ---------------------
def loadImageWithAlpha(path):
    img = cv2.imread(path, cv2.IMREAD_UNCHANGED)
    if img is None:
        print("Error loading image:", path)
        return None
    if len(img.shape) < 3 or img.shape[2] != 4:
        img = cv2.cvtColor(img, cv2.COLOR_BGR2BGRA)
    return img

# --------------------- Load Game Object Images ---------------------
folderEatable = os.path.join(script_dir, "..", "assets", "edible", "objects", "eatable")
folderNonEatable = os.path.join(script_dir, "..", "assets", "edible", "objects", "noneatable")

eatables = []
if os.path.exists(folderEatable):
    for file in os.listdir(folderEatable):
        pathImage = os.path.join(folderEatable, file)
        img = loadImageWithAlpha(pathImage)
        if img is not None:
            eatables.append(img)
else:
    print("Warning: Folder", folderEatable, "not found.")

nonEatables = []
if os.path.exists(folderNonEatable):
    for file in os.listdir(folderNonEatable):
        pathImage = os.path.join(folderNonEatable, file)
        img = loadImageWithAlpha(pathImage)
        if img is not None:
            nonEatables.append(img)
else:
    print("Warning: Folder", folderNonEatable, "not found.")

# --------------------- Highscore Handling ---------------------
def update_highscores(score):
    filename = os.path.join(script_dir, "..", "config", "highscores.json")
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
    filename = os.path.join(script_dir, "..", "config", "highscores.json")
    try:
        with open(filename, "r") as f:
            data = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        data = {}
    if GAME_ID not in data or not isinstance(data[GAME_ID], list):
        return [{"name": "Default", "score": 0}]
    return data[GAME_ID]

# --------------------- Flash Effect Variables and Precomputed Gradients ---------------------
flash_active = False
flash_start_time = 0
flash_duration = 300  # milliseconds

flash_corner_width = 300
flash_corner_height = 300

tl_x, tl_y = np.meshgrid(np.arange(flash_corner_width), np.arange(flash_corner_height))
gradient_tl = 1 - np.maximum(tl_x / flash_corner_width, tl_y / flash_corner_height)
gradient_tr = 1 - np.maximum((flash_corner_width - 1 - tl_x) / flash_corner_width, tl_y / flash_corner_height)
gradient_bl = 1 - np.maximum(tl_x / flash_corner_width, (flash_corner_height - 1 - tl_y) / flash_corner_height)
gradient_br = 1 - np.maximum((flash_corner_width - 1 - tl_x) / flash_corner_width,
                            (flash_corner_height - 1 - tl_y) / flash_corner_height)

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

# --------------------- Game Variables ---------------------
currentObject = eatables[0] if eatables else None
pos = [300, 0]
speed = 5
count = 0
isEatable = True
gameOver = False

def resetObject():
    global isEatable
    pos[0] = random.randint(100, 1180)
    pos[1] = 0
    randNo = random.randint(0, 2)
    if randNo == 0 and nonEatables:
        currentObject = nonEatables[random.randint(0, len(nonEatables) - 1)]
        isEatable = False
    elif eatables:
        currentObject = eatables[random.randint(0, len(eatables) - 1)]
        isEatable = True
    else:
        currentObject = None
    return currentObject

# --------------------- Game State ---------------------
gameState = "landing"
pause_cooldown = 300
last_toggle_time = 0
hs_message = ""

pygame.time.delay(1000)  # Ensure loading screen shows at least 1 sec.

# --------------------- Session Initialization ---------------------
game_session_id = sessions.start_game_session(current_user["id"], GAME_ID, "game_play")
logs.log_event(current_user["id"], "game_start", f"Game session {game_session_id} started for {GAME_ID}")


# --------------------- Main Loop ---------------------
running = True
while running:
    current_time = pygame.time.get_ticks()
    events = pygame.event.get()

    for event in events:
        if event.type == pygame.QUIT:
            running = False

    # --------------------- Landing Screen ---------------------
    if gameState == "landing":
        screen.fill(THEME_BG)
        title_text = font_large.render("Welcome to the Edible Game!", True, THEME_TEXT)
        instruct_text = font_small.render("Bite edible objects and avoid non-edible ones.", True, THEME_TEXT)
        screen.blit(title_text, title_text.get_rect(center=(width // 2, 80)))
        screen.blit(instruct_text, instruct_text.get_rect(center=(width // 2, 140)))
        diff_display = font_medium.render(f"Difficulty: {difficulty.capitalize()}", True, THEME_TEXT)
        screen.blit(diff_display, diff_display.get_rect(center=(width // 2, 220)))
        landing_buttons = get_landing_buttons()
        for button in landing_buttons:
            button.draw(screen)
        pygame.display.update()

        for event in events:
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                for button in landing_buttons:
                    if button.is_clicked(event.pos):
                        if button.action == "easy":
                            difficulty = "easy"
                        elif button.action == "normal":
                            difficulty = "normal"
                        elif button.action == "start":
                            gameState = "playing"
                        elif button.action == "highscores":
                            gameState = "view_highscores"
                        elif button.action == "quit":
                            running = False
        clock.tick(30)
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

        for event in events:
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                for button in hs_buttons:
                    if button.is_clicked(event.pos):
                        if button.action == "return":
                            gameState = "landing"
        clock.tick(30)
        continue

    # --------------------- Pause Screen ---------------------
    if gameState == "paused":
        screen.fill(THEME_BG)
        pause_text = font_large.render("Paused", True, THEME_TEXT)
        screen.blit(pause_text, pause_text.get_rect(center=(width // 2, 80)))
        pause_buttons = get_pause_buttons()
        for button in pause_buttons:
            button.draw(screen)
        pygame.display.update()

        for event in events:
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                for button in pause_buttons:
                    if button.is_clicked(event.pos):
                        if button.action == "resume":
                            gameState = "playing"
                        elif button.action == "restart":
                            resetObject()
                            gameOver = False
                            count = 0
                            currentObject = eatables[0] if eatables else None
                            isEatable = True
                            lives = 3
                            gameState = "playing"
                        elif button.action == "quit_menu":
                            gameState = "landing"
        clock.tick(30)
        continue

    # --------------------- Gameover Screen ---------------------
    if gameState == "playing" and gameOver:
        gameState = "gameover"
        continue

    if gameState == "gameover":
        screen.fill(THEME_BG)
        gameover_text = font_large.render("Game Over!", True, THEME_TEXT)
        score_text = font_medium.render(f"Score: {count}", True, THEME_TEXT)
        screen.blit(gameover_text, gameover_text.get_rect(center=(width // 2, 80)))
        screen.blit(score_text, score_text.get_rect(center=(width // 2, 160)))
        gameover_buttons = get_gameover_buttons()
        for button in gameover_buttons:
            button.draw(screen)
        pygame.display.update()

        for event in events:
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                for button in gameover_buttons:
                    if button.is_clicked(event.pos):
                        if button.action == "restart":
                            resetObject()
                            gameOver = False
                            count = 0
                            currentObject = eatables[0] if eatables else None
                            isEatable = True
                            lives = 3
                            gameState = "playing"
                        elif button.action == "quit_menu":
                            gameState = "landing"
                        elif button.action == "enter_highscore":
                            gameState = "enter_highscore"
        clock.tick(30)
        continue

    # --------------------- Post Highscore Message Screen ---------------------
    if gameState == "post_highscore":
        screen.fill(THEME_BG)
        msg_text = font_large.render(hs_message, True, THEME_TEXT)
        screen.blit(msg_text, msg_text.get_rect(center=(width // 2, height // 2 - 50)))
        posths_buttons = get_posthighscore_buttons()
        for button in posths_buttons:
            button.draw(screen)
        pygame.display.update()

        for event in events:
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                for button in posths_buttons:
                    if button.is_clicked(event.pos):
                        if button.action == "return":
                            gameState = "gameover"
        clock.tick(30)
        continue

    # --------------------- Enter Highscore State ---------------------
    if gameState == "enter_highscore":
        updated, hs_message = update_highscores(count)
        gameState = "post_highscore"
        continue

    # --------------------- Playing State ---------------------
    for event in events:
        if gameState == "playing" and not gameOver and event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_ESCAPE, pygame.K_SPACE):
                if current_time - last_toggle_time > pause_cooldown:
                    gameState = "paused"
                    last_toggle_time = current_time
            elif event.key == pygame.K_r:
                resetObject()
                gameOver = False
                count = 0
                currentObject = eatables[0] if eatables else None
                isEatable = True
                lives = 3

    # --------------------- Game Screen (Playing State) ---------------------
    success, img = cap.read()
    if not success:
        break
    img = cv2.flip(img, 1)
    img, faces = detector.findFaceMesh(img, draw=False)
    drawPos = (pos[0], pos[1])
    img = cvzone.overlayPNG(img, currentObject, pos)
    if difficulty == "easy":
        height_obj, width_obj = currentObject.shape[:2]
        outline_color = (0, 255, 0) if isEatable else (0, 0, 255)
        cv2.rectangle(img, drawPos, (drawPos[0] + width_obj, drawPos[1] + height_obj), outline_color, thickness=3)
        if faces:
            face = faces[0]
            up = face[idList[0]]
            down = face[idList[1]]
            cx, cy = (up[0] + down[0]) // 2, (up[1] + down[1]) // 2
            cv2.line(img, (cx, cy), (pos[0] + 50, pos[1] + 50), (0, 255, 0), 3)
    pos[1] += speed
    if pos[1] > 520:
        if isEatable and difficulty == "normal":
            lives -= 1
            trigger_flash()
            if lives <= 0:
                gameOver = True
        currentObject = resetObject()
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
            if isEatable:
                currentObject = resetObject()
                count += 1
                #Added Code for Calculating Level
                if current_user.get("id", 0) != 0:
                    levels.update_player_progress(current_user["id"], GAME_ID, additional_points=5)
                    logs.log_event(current_user["id"], "score", f"Score incremented to {count}")
                else:
                    logs.log_event(0, "score", f"Guest score incremented to {count}")

            else:
                lives -= 1
                trigger_flash()
                currentObject = resetObject()
                if lives <= 0:
                    gameOver = True
    imgRGB = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    surface = pygame.image.frombuffer(imgRGB.tobytes(), (imgRGB.shape[1], imgRGB.shape[0]), "RGB")
    screen.blit(surface, (0, 0))
    score_surface = font_medium.render("Score: " + str(count), True, THEME_TEXT)
    screen.blit(score_surface, (width - score_surface.get_width() - 20, 20))
    for i in range(lives):
        screen.blit(heart_image, (10 + i * (heart_width + 5), 10))
    if flash_active:
        draw_flash_effect()
    pygame.display.update()
    clock.tick(30)

cap.release()
# At game over, end the session and log the final score.
sessions.end_game_session(game_session_id, current_user["id"], GAME_ID, level_increment=0)
logs.log_event(current_user["id"], "game_over", f"Game session {game_session_id} ended with score {count}")

pygame.quit()