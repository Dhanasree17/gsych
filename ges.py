

import cv2
import mediapipe as mp
import numpy as np
import pyautogui
import time
import math
import platform
import speech_recognition as sr
import pyttsx3
import webbrowser
import threading

# Initialize MediaPipe Hands
mp_hands = mp.solutions.hands
hands = mp_hands.Hands(static_image_mode=False, max_num_hands=1,
                       min_detection_confidence=0.6,  # Reduced for faster response
                       min_tracking_confidence=0.6)  # Reduced for faster response
mp_drawing = mp.solutions.drawing_utils

# Get screen size
screen_width, screen_height = pyautogui.size()

# Open webcam
cap = cv2.VideoCapture(0)

if not cap.isOpened():
    print("Error: Could not open webcam.")
    exit()

# Cursor smoothing parameters
cursor_x, cursor_y = 0, 0
alpha = 0.2  # Less smoothing for faster response

# Click debounce
click_active = False
click_cooldown = 0.2  # Reduced for quicker clicking
last_click_time = 0

# Scroll tracking
scroll_active = False
last_scroll_y = None  # Used to calculate hand speed for scrolling

# Pointer size
pointer_size = 25  # Increased pointer size

# Landmark drawing spec for thicker lines and bigger dots
landmark_drawing_spec = mp_drawing.DrawingSpec(thickness=4, circle_radius=pointer_size // 3)  # Increased thickness/radius
connection_drawing_spec = mp_drawing.DrawingSpec(thickness=4)  # Increased thickness

# Gesture Control
gesture_sensitivity = 30
last_gesture_time = 0
gesture_cooldown = 0.5  # increased to prevent repeat actions
swipe_distance_threshold = 70  # Adjust for swipe sensitivity increased for prevent action
palm_history = []  # Track palm positions for swipe detection
palm_history_length = 5  # adjust for smooth swipe increased for prevent action

# Platform Checking
system_os = platform.system()
is_mac = system_os == "Darwin"

# Initialize scroll display variables
scroll_display_end = 0
scroll_percentage = 0

# Initialize speech recognition and text-to-speech
recognizer = sr.Recognizer()
engine = pyttsx3.init()

def speak(text):
    engine.say(text)
    engine.runAndWait()

def listen_for_command():
    with sr.Microphone() as source:
        print("Listening for command.")
        recognizer.adjust_for_ambient_noise(source)
        audio = recognizer.listen(source)
        try:
            command = recognizer.recognize_google(audio).lower()
            print(f"Command received: {command}")
            return command
        except sr.UnknownValueError:
            print("Sorry, I did not understand that.")
            return None
        except sr.RequestError:
            print("Sorry, my speech service is down.")
            return None

def execute_command(command):
    if "open browser" in command:
        webbrowser.open("http://www.google.com")
        speak("Opening browser")
    elif "open youtube" in command:
        webbrowser.open("http://www.youtube.com")
        speak("Opening YouTube")
    elif "open" in command and "notepad" in command:
        pyautogui.hotkey('win', 'r')
        pyautogui.typewrite('notepad')
        pyautogui.press('enter')
        speak("Opening Notepad")
    elif "close window" in command:
        pyautogui.hotkey('alt', 'f4')
        speak("Closing window")
    else:
        speak("Command not recognized")

def distance(point1, point2):
    return math.sqrt((point2[0] - point1[0]) ** 2 + (point2[1] - point1[1]) ** 2)

def calculate_angle(p1, p2, p3):
    """Calculates angle between 3 points"""
    angle = math.degrees(math.atan2(p3[1] - p2[1], p3[0] - p2[0]) -
                         math.atan2(p1[1] - p2[1], p1[0] - p2[0]))
    return angle if angle > 0 else angle + 360

def is_index_finger_extended(landmark_positions):
    """Check if only the index finger is extended"""
    index_finger_extended = landmark_positions[mp_hands.HandLandmark.INDEX_FINGER_TIP].y < landmark_positions[
        mp_hands.HandLandmark.INDEX_FINGER_MCP].y
    thumb_folded = landmark_positions[mp_hands.HandLandmark.THUMB_TIP].x > landmark_positions[
        mp_hands.HandLandmark.THUMB_MCP].x
    middle_folded = landmark_positions[mp_hands.HandLandmark.MIDDLE_FINGER_TIP].y > landmark_positions[
        mp_hands.HandLandmark.MIDDLE_FINGER_MCP].y
    ring_folded = landmark_positions[mp_hands.HandLandmark.RING_FINGER_TIP].y > landmark_positions[
        mp_hands.HandLandmark.RING_FINGER_MCP].y
    pinky_folded = landmark_positions[mp_hands.HandLandmark.PINKY_TIP].y > landmark_positions[
        mp_hands.HandLandmark.PINKY_MCP].y

    return index_finger_extended and thumb_folded and middle_folded and ring_folded and pinky_folded

def is_index_and_middle_fingers_extended(landmark_positions):
    """Check if both index and middle fingers are extended"""
    index_extended = landmark_positions[mp_hands.HandLandmark.INDEX_FINGER_TIP].y < landmark_positions[
        mp_hands.HandLandmark.INDEX_FINGER_MCP].y
    middle_extended = landmark_positions[mp_hands.HandLandmark.MIDDLE_FINGER_TIP].y < landmark_positions[
        mp_hands.HandLandmark.MIDDLE_FINGER_MCP].y
    thumb_folded = landmark_positions[mp_hands.HandLandmark.THUMB_TIP].x > landmark_positions[
        mp_hands.HandLandmark.THUMB_MCP].x
    ring_folded = landmark_positions[mp_hands.HandLandmark.RING_FINGER_TIP].y > landmark_positions[
        mp_hands.HandLandmark.RING_FINGER_MCP].y
    pinky_folded = landmark_positions[mp_hands.HandLandmark.PINKY_TIP].y > landmark_positions[
        mp_hands.HandLandmark.PINKY_MCP].y

    return index_extended and middle_extended and thumb_folded and ring_folded and pinky_folded

def change_tab():
    pyautogui.hotkey('ctrl' if not is_mac else 'command', 'tab')

def close_window():
    pyautogui.hotkey('ctrl' if not is_mac else 'command', 'w')

def minimize_window():
    if is_mac:
        pyautogui.hotkey('command', 'm')
    else:
        pyautogui.hotkey('win', 'down')

def open_recent_tab():
    pyautogui.hotkey('ctrl' if not is_mac else 'command', 'shift', 't')

def is_four_fingers_open(landmark_positions):
    """Check if only four fingers (excluding thumb) are extended."""
    thumb_extended = landmark_positions[mp_hands.HandLandmark.THUMB_TIP].y > landmark_positions[mp_hands.HandLandmark.THUMB_MCP].y
    index_extended = landmark_positions[mp_hands.HandLandmark.INDEX_FINGER_TIP].y < landmark_positions[mp_hands.HandLandmark.INDEX_FINGER_MCP].y
    middle_extended = landmark_positions[mp_hands.HandLandmark.MIDDLE_FINGER_TIP].y < landmark_positions[mp_hands.HandLandmark.MIDDLE_FINGER_MCP].y
    ring_extended = landmark_positions[mp_hands.HandLandmark.RING_FINGER_TIP].y < landmark_positions[mp_hands.HandLandmark.RING_FINGER_MCP].y
    pinky_extended = landmark_positions[mp_hands.HandLandmark.PINKY_TIP].y < landmark_positions[mp_hands.HandLandmark.PINKY_MCP].y

    return index_extended and middle_extended and ring_extended and pinky_extended and not thumb_extended

def voice_command_listener():
    while True:
        command = listen_for_command()
        if command:
            execute_command(command)

# Start the voice command listener in a separate thread
voice_thread = threading.Thread(target=voice_command_listener)
voice_thread.daemon = True
voice_thread.start()

print("Press 'q' to exit the script.")

while cap.isOpened():
    ret, frame = cap.read()
    if not ret:
        break

    # Reduce frame size for faster processing
    frame = cv2.resize(frame, (640, 480))

    # Flip frame for a mirror effect
    frame = cv2.flip(frame, 1)
    frame_height, frame_width, _ = frame.shape

    # Convert frame to RGB
    frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    results = hands.process(frame_rgb)

    if results.multi_hand_landmarks:
        for hand_landmarks in results.multi_hand_landmarks:
            # Extract finger landmarks
            landmark_positions = {landmark: hand_landmarks.landmark[landmark] for landmark in
                                  mp_hands.HandLandmark}

            # Convert to screen coordinates
            def get_screen_coords(landmark):
                return (int(landmark.x * frame_width),
                        int(landmark.y * frame_height))

            index_finger = get_screen_coords(landmark_positions[mp_hands.HandLandmark.INDEX_FINGER_TIP])
            middle_finger = get_screen_coords(landmark_positions[mp_hands.HandLandmark.MIDDLE_FINGER_TIP])
            thumb = get_screen_coords(landmark_positions[mp_hands.HandLandmark.THUMB_TIP])
            ring_finger = get_screen_coords(landmark_positions[mp_hands.HandLandmark.RING_FINGER_TIP])
            pinky_finger = get_screen_coords(landmark_positions[mp_hands.HandLandmark.PINKY_TIP])
            wrist_coords = get_screen_coords(landmark_positions[mp_hands.HandLandmark.WRIST])
            # Hand gesture recognition

            current_time = time.time()

            # Check if only index finger is extended
            if is_index_finger_extended(landmark_positions):
                # Move cursor with index finger (with smoothing)
                cursor_x = alpha * (index_finger[0] * (screen_width / frame_width)) + (1 - alpha) * cursor_x
                cursor_y = alpha * (index_finger[1] * (screen_height / frame_height)) + (1 - alpha) * cursor_y
                pyautogui.moveTo(int(cursor_x), int(cursor_y), duration=0.01)

                # Detect pinch (clicking) or Enter Key press
                thumb_index_distance = np.linalg.norm(np.array(thumb) - np.array(index_finger))
                if thumb_index_distance < 30:  # Click threshold
                    if not click_active and (current_time - last_click_time) > click_cooldown:
                        click_active = True
                        last_click_time = current_time
                        pyautogui.press('enter') # changed to enter press
                else:
                    click_active = False  # Reset click state
            else:
                click_active = False

                # Scrolling control (Index and Middle Fingers Extended)
                if is_index_and_middle_fingers_extended(landmark_positions):
                    # Calculate hand speed based on index finger movement
                    if last_scroll_y is not None:
                        scroll_y_change = index_finger[1] - last_scroll_y
                        scroll_amount = int(scroll_y_change * 0.5)  # Adjust multiplier for sensitivity

                        # Perform scrolling
                        pyautogui.scroll(-scroll_amount)  # Invert for natural scrolling
                        scroll_active = True
                        scroll_display_end = current_time + 1  # Display scroll percentage for 1 second
                        scroll_percentage = min(100, max(0, int((scroll_y_change / frame_height) * 100)))  # Calculate scroll percentage
                    else:
                        scroll_active = False
                    last_scroll_y = index_finger[1]  # Update last scroll position
                else:
                    scroll_active = False
                    last_scroll_y = None  # Reset scroll position for next scroll

                # Gestures Control

                if current_time - last_gesture_time > gesture_cooldown:
                    # Four fingers Closed

                    extended_fingers = sum([
                        landmark_positions[mp_hands.HandLandmark.INDEX_FINGER_TIP].y < landmark_positions[
                            mp_hands.HandLandmark.INDEX_FINGER_MCP].y,
                        landmark_positions[mp_hands.HandLandmark.MIDDLE_FINGER_TIP].y < landmark_positions[
                            mp_hands.HandLandmark.MIDDLE_FINGER_MCP].y,
                        landmark_positions[mp_hands.HandLandmark.RING_FINGER_TIP].y < landmark_positions[
                            mp_hands.HandLandmark.RING_FINGER_MCP].y,
                        landmark_positions[mp_hands.HandLandmark.PINKY_TIP].y < landmark_positions[
                            mp_hands.HandLandmark.PINKY_MCP].y,
                        landmark_positions[mp_hands.HandLandmark.THUMB_TIP].y < landmark_positions[
                            mp_hands.HandLandmark.THUMB_MCP].y # added thumb
                    ])
                    if extended_fingers == 0:
                        minimize_window()
                        last_gesture_time = current_time
                    # Four-Finger Swipes
                    # Calculate horizontal movement of the palm
                    palm_x = wrist_coords[0]

                    # Update Palm History
                    palm_history.append(palm_x)
                    if len(palm_history) > palm_history_length:
                        palm_history.pop(0)  # Keep only the last N positions

                    # Calculate Swipe Distance
                    if len(palm_history) == palm_history_length:
                        swipe_distance = palm_history[-1] - palm_history[0]
                        # print(swipe_distance)  # For debugging
                        # Four-Finger Swipes
                        if abs(swipe_distance) > swipe_distance_threshold:
                            change_tab()
                            last_gesture_time = current_time

                    # Four fingers Opened
                    if is_four_fingers_open(landmark_positions):
                        open_recent_tab()
                        last_gesture_time = current_time

            # Draw UI elements
            cv2.circle(frame, (index_finger[0], index_finger[1]), pointer_size, (0, 255, 0), -1)  # Green for index
            cv2.circle(frame, (thumb[0], thumb[1]), pointer_size, (255, 0, 0), -1)  # Blue for thumb
            cv2.circle(frame, (middle_finger[0], middle_finger[1]), pointer_size, (0, 0, 255), -1)  # Red for middle
            cv2.circle(frame, (ring_finger[0], ring_finger[1]), pointer_size, (255, 255, 0), -1)  # Cyan for ring
            cv2.circle(frame, (pinky_finger[0], pinky_finger[1]), pointer_size, (255, 0, 255), -1)  # Purple for pinky

            # Draw hand landmarks with custom DrawingSpec
            mp_drawing.draw_landmarks(
                frame,
                hand_landmarks,
                mp_hands.HAND_CONNECTIONS,
                landmark_drawing_spec=landmark_drawing_spec,
                connection_drawing_spec=connection_drawing_spec
            )
            # Show Scroll percentage
            if scroll_active and current_time <= scroll_display_end:
                text = f"Scrolling: {scroll_percentage}%"
                cv2.putText(frame, text, (10, 70), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2, cv2.LINE_AA)

    # Show the webcam feed
    cv2.imshow("Hand Gesture Tracking - Optimized", frame)

    # Exit when 'q' is pressed
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

# Release resources
cap.release()
cv2.destroyAllWindows()
hands.close()