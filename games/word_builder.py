import sys
import os
import cv2
import random
import numpy as np
import pygame
import json
from cvzone.HandTrackingModule import HandDetector
import cvzone
import sys
import os
import sqlite3
import datetime
from services import sessions, levels, logs, utils

# Load current user info from a shared JSON file
current_user_path = os.path.join(os.getcwd(), "config", "current_user.json")
try:
    with open(current_user_path, "r") as f:
        current_user = json.load(f)
except Exception as e:
    current_user = {"id": 0, "userName": "Guest", "role": "player", "email": ""}
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

# --------------------- Pygame Setup ---------------------
pygame.init()
width, height = 1280, 720
screen = pygame.display.set_mode((width, height))
pygame.display.set_caption("World Builder")
clock = pygame.time.Clock()

# Use playful fonts for a kid-friendly look.
font_large = pygame.font.SysFont("Comic Sans MS", 80)
font_medium = pygame.font.SysFont("Comic Sans MS", 60)
font_small = pygame.font.SysFont("Comic Sans MS", 40)

# --------------------- Load Background Image ---------------------
# This image will be used on the loading screen.
script_dir = os.path.dirname(os.path.abspath(__file__))
loading_bg_path = os.path.join(script_dir, "..", "assets", "background", "word_builder.png") # Updated path
loading_bg_img = pygame.image.load(loading_bg_path)
loading_bg_img = pygame.transform.scale(loading_bg_img, (width, height))


# --------------------- Load Heart Image ---------------------
heart_img_path = os.path.join(script_dir, "..", "assets", "heart.png")
try:
    heart_img = pygame.image.load(heart_img_path).convert_alpha()
    heart_img = pygame.transform.scale(heart_img, (50, 50))  # Adjust size as needed
except pygame.error as e:
    print(f"Error loading heart image: {e}")
    heart_img = None

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
    quit_menu_btn = Button("Quit to Menu", width // 2 - btn_width // 2, 400, btn_width, btn_height, action="quit_menu")
    return [resume_btn, quit_menu_btn]

def get_game_over_buttons():
    btn_width, btn_height = 300, 80
    restart_btn = Button("Play Again", width // 2 - btn_width // 2, 400, btn_width, btn_height, action="start")
    menu_btn = Button("Main Menu", width // 2 - btn_width // 2, 500, btn_width, btn_height, action="main_menu")
    quit_btn = Button("Quit", width // 2 - btn_width // 2, 600, btn_width, btn_height, action="quit")
    return [restart_btn, menu_btn, quit_btn]


# --------------------- Loading Screen Function ---------------------
def draw_loading_screen():
    # Blit the background image, then overlay loading text.
    screen.blit(loading_bg_img, (0, 0))
    loading_title = font_large.render("World Builder", True, THEME_TEXT)
    loading_message = font_small.render("Loading... Please wait.", True, THEME_TEXT)
    screen.blit(loading_title, loading_title.get_rect(center=(width // 2, height // 2 - 50)))
    screen.blit(loading_message, loading_message.get_rect(center=(width // 2, height // 2 + 20)))
    pygame.display.update()


# --------------------- Word & Letter Settings ---------------------
# Target area for forming a word (its height matches the letter button size)
LETTER_BUTTON_SIZE = 120
TARGET_RECT = pygame.Rect(100, 550, 1080, LETTER_BUTTON_SIZE * 1.5) # Increased height and width, moved up

NUM_LETTERS = 7  # Number of letters generated (will be based on the target word)
LETTER_FONT_SIZE = 90  # Adjusted for button design

# List of simple words for children
target_words = ["BOY", "GIRL", "PEN", "POT", "CAT", "DOG", "SUN", "FUN", "RUN", "JUMP"]
current_word = ""

def is_valid_word(word):
    return word.upper() == current_word.upper()

# --------------------- Letter Class ---------------------
class Letter:
    def __init__(self, char, pos):
        self.char = char
        self.pos = pos  # Top-left position as a tuple (x, y)
        self.original_pos = pos # Store the original position
        self.button_size = LETTER_BUTTON_SIZE
        # Render the letter using Comic Sans (light beige text on medium brown background)
        self.text_surface = pygame.font.SysFont("Comic Sans MS", LETTER_FONT_SIZE).render(char, True, BUTTON_TEXT)
        # Create a surface for the letter button.
        self.surface = pygame.Surface((self.button_size, self.button_size))
        self.surface.fill(BUTTON_BG)
        pygame.draw.rect(self.surface, THEME_BG, (0, 0, self.button_size, self.button_size), 3)
        text_rect = self.text_surface.get_rect(center=(self.button_size // 2, self.button_size // 2))
        self.surface.blit(self.text_surface, text_rect)
        self.rect = self.surface.get_rect(topleft=pos)
        self.draw_hint = False # Flag to indicate if this letter should have a hint

    def update(self, cursor):
        # Center the letter on the cursor.
        new_x = cursor[0] - self.button_size // 2
        new_y = cursor[1] - self.button_size // 2
        self.pos = (new_x, new_y)
        self.rect.topleft = self.pos

    def reset_position(self):
        self.pos = self.original_pos
        self.rect.topleft = self.pos

    def draw(self, surface):
        surface.blit(self.surface, self.pos)
        if self.draw_hint:
            pygame.draw.rect(surface, HINT_COLOR, self.rect, 5) # Draw a muted orange outline

# --------------------- Letter Generation (Word-Based) ---------------------
def generate_letters():
    global current_word
    letters = []
    current_word = random.choice(target_words)
    shuffled_letters = list(current_word)
    random.shuffle(shuffled_letters)
    spacing = 20
    start_x = (width - (LETTER_BUTTON_SIZE + spacing) * len(shuffled_letters) + spacing) // 2
    y = 50
    for i, char in enumerate(shuffled_letters):
        x = start_x + i * (LETTER_BUTTON_SIZE + spacing)
        letter_obj = Letter(char, (x, y))
        letters.append(letter_obj)
    return letters

# --------------------- Collision Resolution ---------------------
def resolve_collisions(dragged, letters):
    # For every other letter, if it overlaps with the dragged letter, nudge it away horizontally.
    for letter in letters:
        if letter is not dragged and dragged.rect.colliderect(letter.rect):
            if letter.rect.centerx < dragged.rect.centerx:
                letter.pos = (letter.pos[0] - 5, letter.pos[1])
            else:
                letter.pos = (letter.pos[0] + 5, letter.pos[1])
            letter.rect.topleft = letter.pos

# --------------------- Webcam & Hand Detector Setup ---------------------
cap = cv2.VideoCapture(0)
cap.set(3, width)
cap.set(4, height)
detector = HandDetector(detectionCon=0.8)

# --------------------- Game Variables ---------------------
score = 0
lives = 3
letters = []  # Current set of draggable letters
message = ""  # Message to display after word submission
message_timer = 0

# Global variable for the currently dragged letter.
dragging_letter = None

# Hint System Variables
hint_timer = 0
hint_interval = 30000  # 30 seconds in milliseconds
hint_index = 0

# --------------------- Game States ---------------------
# Allowed states: "loading", "main_menu", "game", "paused", "game_over"
game_state = "loading"
loading_start_time = pygame.time.get_ticks()

# --------------------- Draw Lives Function ---------------------
def draw_lives(surface, current_lives, position):
    if heart_img:
        for i in range(current_lives):
            x = position[0] + i * (heart_img.get_width() + 10)
            surface.blit(heart_img, (x, position[1]))


GAME_ID_SPELL = "SpellDrop"  # Unique game ID for Spell Drop

# Initialize the player's progress record (creates one if it doesn't exist)
levels.init_player_progress(USER_ID, GAME_ID_SPELL)
base_progress = levels.get_player_progress(USER_ID, GAME_ID_SPELL)
base_level = base_progress["level"] if base_progress and "level" in base_progress else 0

# Start a game session and log the event.
session_id = sessions.start_game_session(USER_ID, GAME_ID_SPELL, "SpellDrop")
logs.log_event(USER_ID, "game_start", f"Game session {session_id} started for {GAME_ID_SPELL}")

def player_quit():
    global running
    sessions.end_game_session(session_id, USER_ID, GAME_ID_SPELL, level_increment=0)
    logs.log_event(USER_ID, "quit", f"Game session {session_id} ended by player quit with score {score}")
    running = False  # Exit the main loop


# --------------------- Main Loop ---------------------
while True:
    elapsed_time = clock.tick(30)
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
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
                            score = 0 # Reset score on new game
                            lives = 3 # Reset lives on new game
                            letters = generate_letters()
                            hint_timer = 0
                            hint_index = 0
                        elif button.action == "quit":
                            player_quit()
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
                            letters = generate_letters()
                            hint_timer = 0
                            hint_index = 0
                        elif button.action == "main_menu":
                            game_state = "main_menu"
                        elif button.action == "quit":
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
                    cap.release()
                    pygame.quit()
                    sys.exit()

    # --------------------- State-Based Drawing ---------------------
    if game_state == "loading":
        draw_loading_screen()
        if pygame.time.get_ticks() - loading_start_time > 2000:
            game_state = "main_menu"

    elif game_state == "main_menu":
        screen.fill(THEME_BG)
        title_text = font_large.render("Main Menu", True, THEME_TEXT)
        screen.blit(title_text, title_text.get_rect(center=(width // 2, 100)))
        # Display instructions for how to play.
        instructions = [
            "Instructions:",
            "1. Use pinch gesture (index & middle finger) to select a letter.",
            "2. Drag the letter into the box at the bottom to form the word.",
            "3. Valid words earn points.",
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
        screen.blit(game_over_text, game_over_text.get_rect(center=(width // 2, 200)))
        screen.blit(final_score_text, final_score_text.get_rect(center=(width // 2, 300)))
        for button in get_game_over_buttons():
            button.draw(screen)

    elif game_state == "game":
        ret, frame = cap.read()
        if not ret:
            continue
        frame = cv2.flip(frame, 1)
        hands, frame = detector.findHands(frame, flipType=True)
        pinch = False
        cursor = None
        if hands:
            lmList = hands[0]['lmList']
            length, info, _ = detector.findDistance(lmList[8][:2], lmList[12][:2], frame)
            pinch = length < 60
            cursor = lmList[8][:2]

        # Handle dragging with a selected letter.
        if pinch and cursor is not None:
            if dragging_letter is None:
                # Check if any letter is under the cursor to select it.
                for letter_obj in letters:
                    if letter_obj.rect.collidepoint(cursor):
                        dragging_letter = letter_obj
                        break
            else:
                # Update the selected letter's position.
                dragging_letter.update(cursor)
                resolve_collisions(dragging_letter, letters)
        else:
            if dragging_letter:
                # Check if a significant portion of the letter is within the target rect
                if TARGET_RECT.colliderect(dragging_letter.rect):
                    # Snap the letter into the target rect (aligning the top)
                    dragging_letter.pos = (dragging_letter.pos[0], TARGET_RECT.top)
                    dragging_letter.rect.topleft = dragging_letter.pos
                dragging_letter = None

        # Convert webcam frame for display.
        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        frame_surface = pygame.image.frombuffer(frame.tobytes(), (width, height), "RGB")
        screen.blit(frame_surface, (0, 0))

        # Draw target zone for word formation.
        pygame.draw.rect(screen, TARGET_BG, TARGET_RECT) # Fill the target area
        pygame.draw.rect(screen, THEME_TEXT, TARGET_RECT, 3) # Draw the border
        instruction = font_small.render("Form the word below", True, THEME_TEXT)
        screen.blit(instruction, (TARGET_RECT.x, TARGET_RECT.y - 40))

        # Draw letters.
        for letter_obj in letters:
            letter_obj.draw(screen)

        # Display score and lives.
        score_text = font_small.render(f"Score: {score}", True, THEME_TEXT)
        screen.blit(score_text, (20, 20))
        if heart_img:
            draw_lives(screen, lives, (20, 70))

        # Check for letters inside target zone.
        selected_letters = [letter_obj for letter_obj in letters if TARGET_RECT.colliderect(letter_obj.rect)]
        selected_letters.sort(key=lambda l: l.pos[0])
        formed_word = "".join(letter_obj.char for letter_obj in selected_letters)


        if formed_word:
            if is_valid_word(formed_word):
                score += 1
                message = f"'{formed_word}' is correct! +3 points"
                # --- LEVEL UPDATE & LOGGING SNIPPET ---
                # (Assumes USER_ID and GAME_ID_SPELL are defined earlier in the file.)
                if USER_ID != 0:
                    try:
                        levels.update_player_progress(USER_ID, GAME_ID_SPELL, additional_points=5)
                    except Exception as e:
                        print("Level update error:", e)
                    logs.log_event(USER_ID, "score", f"Score incremented to {score}")
                else:
                    logs.log_event(0, "score", f"Guest score incremented to {score}")
                # --- END LEVEL UPDATE & LOGGING SNIPPET ---

                letters = generate_letters()
                hint_timer = 0
                hint_index = 0
                for letter in letters:
                    letter.draw_hint = False # Reset hints for the new word
            elif len(formed_word) == len(current_word): # Only show incorrect message if word length matches
                message = f"'{formed_word}' is not the word. Try again!"
                for letter in selected_letters:
                    letter.reset_position()
                lives -= 1
                if lives <= 0:
                    game_state = "game_over"
            message_timer = pygame.time.get_ticks()
            hint_timer = 0 # Reset hint timer on any word attempt

        elif not formed_word:
            message = "" # Clear the message when no word is formed

        if message and pygame.time.get_ticks() - message_timer < 3000:
            msg_surface = font_small.render(message, True, THEME_TEXT)
            screen.blit(msg_surface, (300, 520))

        # Hint System
        if game_state == "game" and not formed_word and pygame.time.get_ticks() - (loading_start_time if game_state == "loading" else pygame.time.get_ticks() - hint_timer) > hint_interval:
            letters_in_target = [letter for letter in letters if TARGET_RECT.colliderect(letter.rect)]
            correctly_placed = []
            for i, letter in enumerate(letters_in_target):
                if i < len(current_word) and letter.char.upper() == current_word[i].upper() and not letter.draw_hint:
                    correctly_placed.append(letter)

            # Find the first correctly placed letter that hasn't been hinted yet
            hinted = False
            for i in range(len(current_word)):
                for letter in letters_in_target:
                    index_in_target = letters_in_target.index(letter)
                    if index_in_target == i and letter.char.upper() == current_word[i].upper() and not letter.draw_hint and not hinted:
                        letter.draw_hint = True
                        hinted = True
                        break
                if hinted:
                    break
            hint_timer = pygame.time.get_ticks() # Reset the hint timer

        # Reset hint if a new word is generated
        if not letters: # Check if the letters list is empty (new word generated)
            for letter in letters:
                letter.draw_hint = False
            hint_index = 0
            hint_timer = 0


    pygame.display.update()
    clock.tick(30)