import cv2
import pytesseract
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
import pygame
import sys
import numpy as np

# --- Configuration ---
expected_text = "hello"  # Change this to any expected word or phrase

# --- Pygame Initialization ---
pygame.init()
window_width, window_height = 800, 600
screen = pygame.display.set_mode((window_width, window_height))
pygame.display.set_caption("Interactive Writing Game")
font = pygame.font.SysFont(None, 36)
clock = pygame.time.Clock()

# --- OpenCV Video Capture ---
cap = cv2.VideoCapture(0)
if not cap.isOpened():
    print("Cannot access webcam")
    sys.exit()

# --- Helper functions ---
def cv2frame_to_pygame(surface_frame):
    """Convert an OpenCV image (BGR) to a pygame surface."""
    # Convert color from BGR to RGB
    frame_rgb = cv2.cvtColor(surface_frame, cv2.COLOR_BGR2RGB)
    frame_rgb = np.rot90(frame_rgb)  # Rotate if needed
    pygame_image = pygame.surfarray.make_surface(frame_rgb)
    return pygame.transform.scale(pygame_image, (window_width, window_height))

def get_ocr_text(frame):
    """Process frame with pytesseract to detect text."""
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

    # 1. Noise Reduction: Apply Gaussian Blur to smooth the image
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)

    # 2. Thresholding: Experiment with different methods (uncomment only one)
    # Method A: Otsu's Thresholding (often a good starting point)
    _, thresh = cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)

    # Method B: Adaptive Thresholding (try this if Otsu doesn't work well)
    # thresh = cv2.adaptiveThreshold(blurred, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
    #                                cv2.THRESH_BINARY_INV, 11, 2)

    # Method C: Fixed Threshold (if lighting is very consistent)
    # _, thresh = cv2.threshold(blurred, 160, 255, cv2.THRESH_BINARY_INV) # Adjust threshold value

    # 3. Morphological Operations: Dilation to thicken, Erosion to clean
    kernel = np.ones((2, 2), np.uint8)
    dilated = cv2.dilate(thresh, kernel, iterations=1)
    eroded = cv2.erode(dilated, kernel, iterations=1) # Try erosion after dilation

    # 4. Tesseract Configuration (specifically for single words)
    config = '--oem 1 --psm 8'  # LSTM engine, single word
    ocr_result = pytesseract.image_to_string(eroded, config=config) # Use the processed image

    return ocr_result.strip().lower()

# --- Main Game Loop ---
challenge_complete = False
info_text = "Write the word: '{}'".format(expected_text)

while True:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            cap.release()
            pygame.quit()
            sys.exit()
        # For example, use spacebar to capture the frame and check the writing
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_SPACE:
                ret, frame = cap.read()
                if ret:
                    # Flip the frame horizontally (mirror effect)
                    frame = cv2.flip(frame, 1)

                    recognized_text = get_ocr_text(frame)
                    print("Detected text:", recognized_text)
                    if expected_text in recognized_text:
                        info_text = "Great job! You wrote '{}' correctly!".format(expected_text)
                        challenge_complete = True
                    else:
                        info_text = "Try again! Expected: '{}'".format(expected_text)

    # Capture frame from webcam
    ret, frame = cap.read()
    if not ret:
        continue

    # Flip the frame horizontally (mirror effect)
    frame = cv2.flip(frame, 1)

    # Convert captured frame to pygame surface
    frame_surface = cv2frame_to_pygame(frame)

    # Draw the video feed on the screen
    screen.blit(frame_surface, (0, 0))

    # Overlay the instructions text on the screen
    text_surface = font.render(info_text, True, (255, 255, 255))
    text_rect = text_surface.get_rect(center=(window_width // 2, 50))
    # Adding a background rectangle for better visibility
    pygame.draw.rect(screen, (0, 0, 0), text_rect.inflate(20, 20))
    screen.blit(text_surface, text_rect)

    # Optionally, display recognized text on screen for debugging:
    recognized_text = get_ocr_text(frame)
    debug_surface = font.render("Detected: " + recognized_text, True, (255, 255, 0))
    debug_rect = debug_surface.get_rect(center=(window_width // 2, window_height - 50))
    pygame.draw.rect(screen, (0, 0, 0), debug_rect.inflate(10, 10))
    screen.blit(debug_surface, debug_rect)

    pygame.display.update()
    clock.tick(30)