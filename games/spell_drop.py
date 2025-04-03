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

# --------------------- Global Game Identifier ---------------------
GAME_ID = "SpellDrop"  # Unique identifier for this game
current_user_path = os.path.join(os.getcwd(), "config", "current_user.json")
try:
    with open(current_user_path, "r") as f:
        current_user = json.load(f)
except Exception as e:
    current_user = {"id": 0, "userName": "Guest", "role": "player", "email": ""}
    print("No current user found; defaulting to Guest.")

# Define USER_ID based on the loaded user.
USER_ID = current_user["id"]

# --------------------- Theme Settings ---------------------
THEME_BG = (0, 30, 60)  # Dark blue background for menus and UI
THEME_TEXT = (255, 165, 0)  # Vibrant orange text (RGB)
# OpenCV uses BGR, so convert THEME_TEXT to BGR:
THEME_TEXT_BGR = (THEME_TEXT[2], THEME_TEXT[1], THEME_TEXT[0])  # (0, 165, 255)

# --------------------- Pygame Setup ---------------------
pygame.init()
pygame.key.set_repeat(0)
width, height = 1280, 720
screen = pygame.display.set_mode((width, height))
pygame.display.set_caption("Spell Drop")
clock = pygame.time.Clock()

# Playful fonts for a kid-friendly look.
font_large = pygame.font.SysFont("Comic Sans MS", 80)
font_medium = pygame.font.SysFont("Comic Sans MS", 60)
font_small = pygame.font.SysFont("Comic Sans MS", 40)


# --------------------- Button and Menu Classes ---------------------
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


class Menu:
    def __init__(self, title, buttons):
        self.title = title
        self.buttons = buttons

    def draw(self, surface):
        surface.fill(THEME_BG)
        if self.title:
            title_text = font_large.render(self.title, True, THEME_TEXT)
            surface.blit(title_text, title_text.get_rect(center=(width // 2, 80)))
        for button in self.buttons:
            button.draw(surface)
        pygame.display.update()

    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            pos = pygame.mouse.get_pos()
            for button in self.buttons:
                if button.is_clicked(pos):
                    return button.action
        return None


def create_main_menu(difficulty="easy"):
    btn_width, btn_height = 400, 100
    buttons = [
        Button("Difficulty: " + difficulty.capitalize(), width // 2 - btn_width // 2, 150, btn_width, btn_height,
               action="toggle_difficulty"),
        Button("Start Game", width // 2 - btn_width // 2, 270, btn_width, btn_height, action="start"),
        Button("Highscores", width // 2 - btn_width // 2, 390, btn_width, btn_height, action="highscores"),
        Button("Quit", width // 2 - btn_width // 2, 510, btn_width, btn_height, action="quit")
    ]
    return Menu("Main Menu", buttons)


def create_pause_menu():
    btn_width, btn_height = 400, 100
    buttons = [
        Button("Resume", width // 2 - btn_width // 2, 300, btn_width, btn_height, action="resume"),
        Button("Quit to Menu", width // 2 - btn_width // 2, 420, btn_width, btn_height, action="quit_menu")
    ]
    return Menu("Paused", buttons)


def create_gameover_menu():
    btn_width, btn_height = 400, 100
    buttons = [
        Button("Restart", width // 2 - btn_width // 2, 300, btn_width, btn_height, action="restart"),
        Button("Quit to Menu", width // 2 - btn_width // 2, 420, btn_width, btn_height, action="quit_menu")
    ]
    return Menu("Game Over", buttons)


def create_highscore_menu():
    btn_width, btn_height = 400, 100
    buttons = [
        Button("Back", width // 2 - btn_width // 2, 600, btn_width, btn_height, action="back")
    ]
    return Menu("Enter Highscore", buttons)


# --------------------- Loading Screen ---------------------
script_dir = os.path.dirname(os.path.abspath(__file__))
loading_bg_path = os.path.join(script_dir, "..", "assets", "background", "spell_drop.png")
if os.path.exists(loading_bg_path):
    loading_bg = pygame.image.load(loading_bg_path).convert()
    loading_bg = pygame.transform.scale(loading_bg, (width, height))
else:
    loading_bg = None

if loading_bg is not None:
    screen.blit(loading_bg, (0, 0))
else:
    screen.fill(THEME_BG)
loading_title = font_large.render("Spell Drop", True, THEME_TEXT)
loading_message = font_small.render("Loading... Please wait.", True, THEME_TEXT)
screen.blit(loading_title, loading_title.get_rect(center=(width // 2, height // 2 - 50)))
screen.blit(loading_message, loading_message.get_rect(center=(width // 2, height // 2 + 20)))
pygame.display.update()
pygame.time.delay(1000)

# --------------------- Load Heart Image ---------------------
lives = 3
heart_path = os.path.join(script_dir, "..", "assets", "heart.png")
heart_image = pygame.image.load(heart_path).convert_alpha()
heart_width = heart_image.get_width()
heart_height = heart_image.get_height()

# --------------------- Camera and FaceMesh ---------------------
cap = cv2.VideoCapture(0)
cap.set(3, width)
cap.set(4, height)
detector = FaceMeshDetector(maxFaces=1)
idList = [0, 17, 78, 292]


# --------------------- Highscore Handling ---------------------
# (Highscore functions remain here, but note that Spell Drop now uses an "enter_highscore" state.)
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
    new_entry = {"name": highscore_name_input.strip() if highscore_name_input.strip() != "" else "Anonymous",
                 "score": score}
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


def qualifies_for_highscore(score):
    if score == 0:
        return False
    filename = os.path.join(script_dir, "..", "config", "highscores.json")
    if not os.path.exists(filename):
        return True
    try:
        with open(filename, "r") as f:
            data = json.load(f)
    except (json.JSONDecodeError, FileNotFoundError):
        data = {}
    if GAME_ID not in data or not isinstance(data[GAME_ID], list):
        return True
    highscores = data[GAME_ID]
    if len(highscores) < 10:
        return True
    min_score = min(entry["score"] for entry in highscores)
    return score > min_score


# --------------------- Word and Letter Setup ---------------------
word_list = ["cat", "dog", "sun", "car", "bee", "pig", "hat", "cup", "ball", "fox"]
target_word = random.choice(word_list).upper()
collected_positions = [False] * len(target_word)
score = 0
word_complete = False
word_complete_time = 0


# --------------------- Letter Generation ---------------------
def generate_letter_image(letter, width_img=100, height_img=100, font_scale=2, thickness=3, color=THEME_TEXT_BGR):
    img = np.zeros((height_img, width_img, 4), dtype=np.uint8)
    text_size, _ = cv2.getTextSize(letter, cv2.FONT_HERSHEY_SIMPLEX, font_scale, thickness)
    text_width, text_height = text_size
    text_x = (width_img - text_width) // 2
    text_y = (height_img + text_height) // 2
    cv2.putText(img, letter, (text_x, text_y), cv2.FONT_HERSHEY_SIMPLEX, font_scale, color, thickness, cv2.LINE_AA)
    mask = (img[:, :, 0] > 0) | (img[:, :, 1] > 0) | (img[:, :, 2] > 0)
    img[:, :, 3] = np.where(mask, 255, 0)
    return img


def resetLetter():
    pos_letter = [random.randint(100, width - 100), 0]
    unfulfilled = [target_word[i] for i, collected in enumerate(collected_positions) if not collected]
    if unfulfilled and random.random() < 0.7:
        letter = random.choice(unfulfilled)
        isCorrect = True
    else:
        alphabet = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
        distractors = []
        for l in alphabet:
            required = target_word.count(l)
            collected_count = sum(1 for i, ch in enumerate(target_word) if ch == l and collected_positions[i])
            if collected_count >= required:
                distractors.append(l)
        if distractors:
            letter = random.choice(distractors)
        else:
            letter = random.choice(alphabet)
        isCorrect = False
    letter_img = generate_letter_image(letter)
    return {"letter": letter, "image": letter_img, "pos": pos_letter, "isCorrect": isCorrect}


currentLetter = resetLetter()
speed = 5


# --------------------- Draw Target Word ---------------------
def draw_target_word():
    box_size = 80
    margin = 10
    total_width = len(target_word) * box_size + (len(target_word) - 1) * margin
    start_x = (width - total_width) // 2
    y = 20
    for i, letter in enumerate(target_word):
        rect = pygame.Rect(start_x + i * (box_size + margin), y, box_size, box_size)
        if collected_positions[i]:
            pygame.draw.rect(screen, (0, 255, 0), rect)
        else:
            pygame.draw.rect(screen, (50, 50, 50), rect)
        border_color = (0, 255, 0) if collected_positions[i] else (150, 150, 150)
        pygame.draw.rect(screen, border_color, rect, 4)
        letter_surface = font_medium.render(letter, True, THEME_TEXT)
        letter_rect = letter_surface.get_rect(center=rect.center)
        screen.blit(letter_surface, letter_rect)


# --------------------- LEVELS & SESSIONS INTEGRATION (ADDED) ---------------------
GAME_ID_SPELL = "SpellDrop"  # Unique game ID for Spell Drop
levels.init_player_progress(USER_ID, GAME_ID_SPELL)
base_progress = levels.get_player_progress(USER_ID, GAME_ID_SPELL)
base_level = base_progress["level"] if base_progress and "level" in base_progress else 0
session_id = sessions.start_game_session(USER_ID, GAME_ID_SPELL, "SpellDrop")
logs.log_event(USER_ID, "game_start", f"Game session {session_id} started for {GAME_ID_SPELL}")


# --------------------- END LEVELS & SESSIONS INTEGRATION ---------------------

# --------------------- LEVEL DISPLAY HELPER (ADDED) ---------------------
def draw_level_display(surface, level):
    global width  # Explicitly use the global variable
    padding = 10
    level_text = f"Level: {level}"
    level_surface = font_small.render(level_text, True, (255, 255, 255))
    rect = level_surface.get_rect()
    rect.width += 2 * padding
    rect.height += 2 * padding
    rect.topright = (width - 20, 20)
    pygame.draw.rect(surface, THEME_TEXT, rect, border_radius=10)
    inner_rect = rect.inflate(-padding * 2, -padding * 2)
    pygame.draw.rect(surface, THEME_BG, inner_rect, border_radius=10)
    surface.blit(level_surface, level_surface.get_rect(center=rect.center))


# --------------------- END LEVEL DISPLAY HELPER ---------------------
def player_quit():
    global running
    sessions.end_game_session(session_id, USER_ID, GAME_ID_SPELL, level_increment=0)
    logs.log_event(USER_ID, "quit", f"Game session {session_id} ended by player quit with score {score}")
    running = False  # This will break out of the main loop


# --------------------- Highscore Input State Variables (NEW) ---------------------
# We'll use these only in the "enter_highscore" state.
highscore_name_input = ""
enter_highscore_prompt = "Enter your name for highscore (Press ENTER to submit or ESC to cancel):"

# --------------------- Game State ---------------------
# States: "main_menu", "playing", "paused", "game_over", "enter_highscore"
state = "main_menu"
current_difficulty = "easy"
current_menu = create_main_menu(current_difficulty)

# --------------------- Main Loop ---------------------
running = True
gameOver = False
while running:
    current_time = pygame.time.get_ticks()
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

        if state in ("main_menu", "paused", "game_over"):
            action = current_menu.handle_event(event)
            if action:
                if state == "main_menu":
                    if action == "toggle_difficulty":
                        current_difficulty = "normal" if current_difficulty == "easy" else "easy"
                        current_menu = create_main_menu(current_difficulty)
                    elif action == "start":
                        target_word = random.choice(word_list).upper()
                        collected_positions = [False] * len(target_word)
                        score = 0
                        lives = 3
                        currentLetter = resetLetter()
                        word_complete = False
                        state = "playing"
                        gameOver = False  # Ensure gameOver is reset when starting a new game
                    elif action == "highscores":
                        # For Spell Drop, highscore menu is not normally used.
                        pass
                    elif action == "quit":
                        player_quit()
                        running = False
                elif state == "paused":
                    if action == "resume":
                        state = "playing"
                    elif action == "quit_menu":
                        current_menu = create_main_menu(current_difficulty)
                        state = "main_menu"
                elif state == "game_over":
                    if action == "restart":
                        target_word = random.choice(word_list).upper()
                        collected_positions = [False] * len(target_word)
                        score = 0
                        lives = 3
                        currentLetter = resetLetter()
                        word_complete = False
                        state = "playing"
                        gameOver = False  # Reset gameOver when restarting
                    elif action == "quit_menu":
                        current_menu = create_main_menu(current_difficulty)
                        state = "main_menu"
        elif state == "enter_highscore":
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_RETURN:
                    # Update highscore using the input string and then go to game over menu.
                    try:
                        updated, hs_message = update_highscores(score)
                        print(hs_message)
                    except Exception as e:
                        print("Highscore update error:", e)
                    current_menu = create_gameover_menu()
                    state = "game_over"
                elif event.key == pygame.K_ESCAPE:
                    # Cancel highscore entry and go to game over menu.
                    current_menu = create_gameover_menu()
                    state = "game_over"
                else:
                    highscore_name_input += event.unicode

    # --------------------- State-Based Drawing ---------------------
    if state in ("main_menu", "paused", "game_over"):
        current_menu.draw(screen)
        clock.tick(30)
        continue

    if state == "enter_highscore":
        screen.fill(THEME_BG)
        prompt_surface = font_medium.render(enter_highscore_prompt, True, THEME_TEXT)
        input_surface = font_medium.render(highscore_name_input, True, THEME_TEXT)
        prompt_rect = prompt_surface.get_rect(center=(width // 2, height // 2 - 50))
        input_rect = input_surface.get_rect(center=(width // 2, height // 2 + 20))
        screen.blit(prompt_surface, prompt_rect)
        screen.blit(input_surface, input_rect)
        pygame.display.update()
        clock.tick(30)
        continue

    if state == "playing":
        success, img = cap.read()
        if not success:
            break
        img = cv2.flip(img, 1)
        img, faces = detector.findFaceMesh(img, draw=False)
        letter_pos = currentLetter["pos"]
        img = cvzone.overlayPNG(img, currentLetter["image"], letter_pos)
        if current_difficulty == "easy":
            h_img, w_img = currentLetter["image"].shape[:2]
            outline_color = (0, 255, 0) if currentLetter["isCorrect"] else (0, 0, 255)
            cv2.rectangle(img, (letter_pos[0], letter_pos[1]), (letter_pos[0] + w_img, letter_pos[1] + h_img),
                          outline_color, thickness=3)
            if faces:
                face = faces[0]
                up = face[idList[0]]
                down = face[idList[1]]
                cx, cy = (up[0] + down[0]) // 2, (up[1] + down[1]) // 2
                cv2.line(img, (cx, cy), (letter_pos[0] + w_img // 2, letter_pos[1] + h_img // 2), (0, 255, 0), 3)
        letter_pos[1] += speed
        if letter_pos[1] > height - 200:
            if currentLetter["isCorrect"] and current_difficulty == "normal":
                lives -= 1
                if lives <= 0:
                    gameOver = True
            currentLetter = resetLetter()
        if faces:
            face = faces[0]
            up = face[idList[0]]
            down = face[idList[1]]
            upDown, _ = detector.findDistance(face[idList[0]], face[idList[1]])
            leftRight, _ = detector.findDistance(face[idList[2]], face[idList[3]])
            cx, cy = (up[0] + down[0]) // 2, (up[1] + down[1]) // 2
            ratio = int((upDown / leftRight) * 100)
            center_letter = (letter_pos[0] + currentLetter["image"].shape[1] // 2,
                             letter_pos[1] + currentLetter["image"].shape[0] // 2)
            distMouthLetter, _ = detector.findDistance((cx, cy), center_letter)
            if distMouthLetter < 100 and ratio > 60:
                caught = currentLetter["letter"].upper()
                if caught in target_word:
                    for i, char in enumerate(target_word):
                        if char == caught and not collected_positions[i]:
                            collected_positions[i] = True
                            score += 1
                            # Update level progress: add 5 points per correct catch.
                            if USER_ID != 0:
                                levels.update_player_progress(USER_ID, GAME_ID_SPELL, 5)
                                logs.log_event(USER_ID, "score", f"Score incremented to {score}")
                            else:
                                logs.log_event(0, "score", f"Guest score incremented to {score}")
                            break
                else:
                    lives -= 1
                    if lives <= 0:
                        gameOver = True
                currentLetter = resetLetter()
        if all(collected_positions) and not word_complete:
            word_complete = True
            word_complete_time = current_time
        if word_complete:
            if current_time - word_complete_time > 1000:
                target_word = random.choice(word_list).upper()
                collected_positions = [False] * len(target_word)
                word_complete = False
        imgRGB = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        surface = pygame.image.frombuffer(imgRGB.tobytes(), (imgRGB.shape[1], imgRGB.shape[0]), "RGB")
        screen.blit(surface, (0, 0))
        draw_target_word()
        score_surface = font_medium.render("Score: " + str(score), True, THEME_TEXT)
        screen.blit(score_surface, (width - score_surface.get_width() - 20, 20))
        for i in range(lives):
            screen.blit(heart_image, (10 + i * (heart_width + 5), 10))

        # --------------------- LEVEL DISPLAY (ADDED) ---------------------
        current_progress = levels.get_player_progress(USER_ID, GAME_ID_SPELL)
        current_level = current_progress["level"] if current_progress and "level" in current_progress else base_level
        draw_level_display(screen, current_level)
        # --------------------- END LEVEL DISPLAY ---------------------

        pygame.display.update()
        clock.tick(30)
        if gameOver:
            # Transition to enter_highscore state if score qualifies; otherwise, go directly to game_over.
            if qualifies_for_highscore(score):
                state = "enter_highscore"
                highscore_name_input = ""  # Reset input
            else:
                state = "game_over"

    if state == "enter_highscore":
        # In this state, display an input box and capture keystrokes.
        screen.fill(THEME_BG)
        prompt_surface = font_medium.render("Enter your name for highscore:", True, THEME_TEXT)
        instruction_surface = font_small.render("Press ENTER to submit or ESC to cancel", True, THEME_TEXT)
        input_surface = font_medium.render(highscore_name_input, True, THEME_TEXT)
        prompt_rect = prompt_surface.get_rect(center=(width // 2, height // 2 - 50))
        instruction_rect = instruction_surface.get_rect(center=(width // 2, height // 2 + 20))
        input_rect = input_surface.get_rect(center=(width // 2, height // 2 + 80))
        screen.blit(prompt_surface, prompt_rect)
        screen.blit(instruction_surface, instruction_rect)
        screen.blit(input_surface, input_rect)
        pygame.display.update()




        # Process key events for input in the main loop below.
        for event in pygame.event.get():
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_RETURN:
                    # Submit input and update highscore.
                    try:
                        updated, hs_message = update_highscores(score)
                        print(hs_message)
                    except Exception as e:
                        print("Highscore update error:", e)
                    current_menu = create_gameover_menu()
                    state = "game_over"
                elif event.key == pygame.K_ESCAPE:
                    # Cancel highscore entry.
                    current_menu = create_gameover_menu()
                    state = "game_over"
                else:
                    highscore_name_input += event.unicode

    pygame.display.flip()
    clock.tick(30)

cap.release()
pygame.quit()
sys.exit()