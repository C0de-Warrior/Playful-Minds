import cv2
import numpy as np
import pygame
import os
from cvzone.HandTrackingModule import HandDetector
import cvzone

# ---------------------- Initialization ---------------------- #
pygame.init()
screen_width, screen_height = 1280, 720
screen = pygame.display.set_mode((screen_width, screen_height))
pygame.display.set_caption("Drag & Drop Game")
clock = pygame.time.Clock()

# Define fonts for text rendering
font_large = pygame.font.SysFont("Arial", 48)
font_medium = pygame.font.SysFont("Arial", 36)

# Initialize webcam
cap = cv2.VideoCapture(0)
cap.set(3, screen_width)
cap.set(4, screen_height)

# Initialize hand detector
detector = HandDetector(detectionCon=0.8)


# ---------------------- DragImg Class ---------------------- #
class DragImg():
    def __init__(self, path, posOrigin, imgType):
        self.posOrigin = posOrigin
        self.imgType = imgType
        self.path = path

        if self.imgType == 'png':
            self.img = cv2.imread(self.path, cv2.IMREAD_UNCHANGED)
        else:
            self.img = cv2.imread(self.path)
        self.size = self.img.shape[:2]

    def update(self, cursor):
        ox, oy = self.posOrigin
        h, w = self.size
        # Update image position if the cursor (hand) is over it
        if ox < cursor[0] < ox + w and oy < cursor[1] < oy + h:
            self.posOrigin = (cursor[0] - w // 2, cursor[1] - h // 2)


# ---------------------- Load Images ---------------------- #
path_images = "ImagesPNG"
myList = os.listdir(path_images)
listImg = []
for i, file in enumerate(myList):
    imgType = 'png' if 'png' in file.lower() else 'jpg'
    listImg.append(DragImg(os.path.join(path_images, file), [50 + i * 300, 50], imgType))

# ---------------------- Game States ---------------------- #
# States: "landing", "game", "pause"
state = "landing"


def draw_text(surface, text, font, color, pos):
    """Helper function to draw text on the Pygame surface."""
    text_surface = font.render(text, True, color)
    surface.blit(text_surface, pos)


# ---------------------- Main Loop ---------------------- #
running = True
while running:
    # Handle Pygame events
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

        if state == "landing":
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_s:
                    state = "game"
                elif event.key == pygame.K_q:
                    running = False

        elif state == "game":
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_p:
                    state = "pause"
                elif event.key == pygame.K_q:
                    running = False

        elif state == "pause":
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_r:
                    state = "game"
                elif event.key == pygame.K_q:
                    running = False

    # Draw according to state
    if state == "landing":
        # Landing screen
        screen.fill((50, 50, 50))
        draw_text(screen, "Welcome to Drag & Drop Game", font_large, (255, 255, 255), (200, 200))
        draw_text(screen, "Press S to Start, Q to Quit", font_medium, (255, 255, 255), (300, 300))

    elif state == "pause":
        # Pause screen
        screen.fill((0, 0, 0))
        draw_text(screen, "Game Paused", font_large, (255, 255, 255), (450, 300))
        draw_text(screen, "Press R to Resume, Q to Quit", font_medium, (255, 255, 255), (400, 400))

    elif state == "game":
        # Capture and process webcam frame
        ret, frame = cap.read()
        if not ret:
            continue
        # Note: The horizontal flip has been removed to avoid the mirror effect.
        # If you ever need a mirror effect, use: frame = cv2.flip(frame, 1)

        hands, frame = detector.findHands(frame, flipType=False)
        if hands:
            lmList = hands[0]['lmList']
            # Use only the x and y coordinates for distance calculation
            length, info, frame = detector.findDistance(lmList[8][:2], lmList[12][:2], frame)
            if length < 60:
                cursor = lmList[8][:2]
                for imgObj in listImg:
                    imgObj.update(cursor)

        try:
            # Overlay the draggable images on the frame
            for imgObj in listImg:
                h, w = imgObj.size
                ox, oy = imgObj.posOrigin
                if imgObj.imgType == "png":
                    frame = cvzone.overlayPNG(frame, imgObj.img, [ox, oy])
                else:
                    frame[oy:oy + h, ox:ox + w] = imgObj.img
        except Exception as e:
            print("Overlay error:", e)

        # Display instruction text directly on the frame
        cv2.putText(frame, "Press 'P' to Pause", (50, 700), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)

        # Convert the frame (BGR to RGB) and then to a Pygame surface
        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        frame = np.rot90(frame)  # Adjust rotation for Pygame's coordinate system
        frame_surface = pygame.surfarray.make_surface(frame)
        screen.blit(frame_surface, (0, 0))

    pygame.display.update()
    clock.tick(30)

cap.release()
pygame.quit()
