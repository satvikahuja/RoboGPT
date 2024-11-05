
import warnings
import torch
import cv2
import numpy as np
import time
import logging
from ultralytics import YOLO
import serial
import sys
import subprocess
import os  # To handle file paths# To handle JSON files

nc = 5
###['bottle', 'box', 'cup', 'horn', 'small_bottle']
CLASS_NAMES = ['bottle', 'box', 'cup', 'horn', 'small_bottle']

CLASS_ID_MAP = {name: idx for idx, name in enumerate(CLASS_NAMES)}

TARGET_CLASS_IDS = list(range(nc))


CONFIDENCE_THRESHOLD = 0.5

SERIAL_PORT = '/dev/cu.usbserial-1130'
SERIAL_BAUDRATE = 9600

# --- Frame Settings ---
FRAME_WIDTH = 1920
FRAME_HEIGHT = 1080

# --- Alignment Settings ---
VERTICAL_LINE_OFFSET = 0
MIN_PIXEL_DISTANCE = 8
MOVEMENT_INTERVAL = 0.1
MOVEMENT_DURATION = 55

# --- Arrow Drawing Settings ---
ARROW_LENGTH = 200
ARROW_THICKNESS = 5
ARROW_COLOR_LEFT = (255, 255, 0)
ARROW_COLOR_RIGHT = (0, 0, 255)
ARROW_POSITION_OFFSET_Y = 100

# --- Movement Settings ---
PERCENTAGE = 0.8
MOVEMENT_DURATION_MS = 150
STEPS_PER_ALIGNMENT = 1

# --- Distance Threshold ---
DISTANCE_THRESHOLD_DEFAULT = 80

# --- Distance Threshold Mapping ---
DISTANCE_THRESHOLDS = {
    'small_bottle': 100,
    'bottle': 80,
    'cup': 105,
    'horn': 165,
    'box': 75,
}
warnings.filterwarnings("ignore", category=FutureWarning)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)
logging.info(f"Using device: {device}")

try:
    model = YOLO('best.pt')
    logging.info("YOLOv9m model successfully loaded.")
except Exception as e:
    logging.error(f"Failed to load YOLOv9m model: {e}")
    model = None

try:
    arduino = serial.Serial(
        port=SERIAL_PORT,
        baudrate=SERIAL_BAUDRATE,
        timeout=1
    )
    logging.info("Serial connection to Arduino established.")
    time.sleep(2)
except serial.SerialException as e:
    logging.error(f"Failed to connect to Arduino: {e}")
    arduino = None


def send_command(command, duration):

    if arduino and arduino.is_open:
        try:
            command_str = f"{command} {duration}\n"
            arduino.write(command_str.encode())
            logging.info(f"Sent command: '{command}' for {duration}ms")
            time.sleep(0.1)  # Brief pause to ensure command is sent
        except serial.SerialException as e:
            logging.error(f"Error sending command '{command}': {e}")
    else:
        logging.warning("Arduino serial connection is not open.")


def move_forward(duration_ms):

    send_command("forward", duration_ms)

def stop_movement():
    send_command("stop", 0)


def move_base(direction, duration_ms):

    if direction.lower() in ['left', 'right']:
        send_command(direction.lower(), duration_ms)
    else:
        logging.error(f"Invalid direction: {direction}. Use 'left' or 'right'.")


def catch_claw_command(selected_object):

    if selected_object.lower() == "cup":
        send_command("right", 250)
        time.sleep(0.6)
        send_command("down", 1250)
        logging.info("Since it is a cup, moving down for 1300ms")
        time.sleep(1.7)
        logging.info("Moving down completed")
        send_command("catch", 2500)
        time.sleep(2.5)
        send_command("catch", 3500)
        logging.info("Catching claw for 3500ms.")
        time.sleep(3.5)
        logging.info("Claw catch completed.")
        send_command("up", 2500)
        logging.info("Moving cup up for 200ms")
        time.sleep(2.5)
    elif selected_object.lower() == "horn":
        send_command("down", 750)
        logging.info("Putting object down for 600ms")
        time.sleep(1)
        send_command("catch", 2000)
        time.sleep(2)
        send_command("catch", 3000)
        time.sleep(3)
        send_command("catch", 1000)
        time.sleep(1)
        send_command("up", 2300)
        time.sleep(2.3)
    elif selected_object.lower() == "box":
        send_command("down", 1200)
        logging.info("Putting object down for 1200ms")
        time.sleep(1.2)
        send_command("release", 2500)
        time.sleep(2.5)
    elif selected_object.lower() == "small_bottle":
        send_command("catch", 3000)
        time.sleep(3)
        send_command("catch", 3000)
        logging.info("Catching claw for 3000ms.")
        time.sleep(3)
        send_command("catch", 1000)
        time.sleep(1)
        logging.info("Claw catch completed.")
        send_command("up", 3000)
        time.sleep(3)
    elif selected_object.lower() == "bottle":
        send_command("catch", 2000)
        time.sleep(2)
        send_command("catch", 3000)
        logging.info("Catching claw for 3000ms.")
        time.sleep(3)
        logging.info("Claw catch completed.")
        send_command("up", 2000)
        time.sleep(2)
    else:
        logging.error(f"No catch command defined for '{selected_object}'.")

def detect_objects(frame, model):

    if model is None:
        logging.error("YOLOv9m model is not loaded.")
        return []

    # Run inference with the specified confidence threshold
    results = model(frame, conf=CONFIDENCE_THRESHOLD)

    # Extract the detections (boxes, confidences, and class IDs)
    detections = results[0].boxes  # YOLO format stores results in 'boxes'

    detected_objects = []
    for detection in detections:
        class_id = int(detection.cls[0])  # Assuming 'cls' is class id
        if class_id in TARGET_CLASS_IDS:
            box = detection.xyxy[0].cpu().numpy()  # [x1, y1, x2, y2]
            conf = detection.conf[0].cpu().numpy()
            detected_objects.append({
                'class_id': class_id,
                'class_name': CLASS_NAMES[class_id],
                'box': box,
                'confidence': conf
            })

    # Log the number of detected objects
    logging.info(f"Detected {len(detected_objects)} object(s) in the frame.")

    return detected_objects


def calculate_distances(box, frame_width, frame_height):
    # Calculate the center of the bounding box
    box_center_x = (box[0] + box[2]) / 2
    box_center_y = (box[1] + box[3]) / 2

    # Calculate the center of the frame with offset
    frame_center_x = (frame_width / 2) + VERTICAL_LINE_OFFSET
    frame_center_y = frame_height / 2

    # Calculate distances from center
    horizontal_distance = box_center_x - frame_center_x  # Positive: Right, Negative: Left
    vertical_distance = box_center_y - frame_center_y  # Positive: Down, Negative: Up

    return float(horizontal_distance), float(vertical_distance)


def decide_direction(horizontal_distance):

    if abs(horizontal_distance) < MIN_PIXEL_DISTANCE:
        return 'straight'
    elif horizontal_distance > 0:
        return 'right'
    else:
        return 'left'


def align_robot(direction, distance):

    global last_movement_time, original_distance, required_distance, STEPS_PER_ALIGNMENT  # Added STEPS_PER_ALIGNMENT

    current_time = time.time()

    if current_time - last_movement_time >= MOVEMENT_INTERVAL:
        if direction in ['left', 'right']:
            move_base(direction, MOVEMENT_DURATION)  # Move for specified duration
            logging.info(f"Aligning {direction}: {distance:.2f}px from center.")
            last_movement_time = current_time

            # Record original distance on first alignment
            if original_distance is None:
                original_distance = abs(distance)
                required_distance = original_distance * PERCENTAGE
                logging.info(f"Original distance recorded: {original_distance:.2f}px")
                logging.info(f"Required distance to move forward: {required_distance:.2f}px")
        elif direction == 'straight':
            logging.info("Aligned straight. No movement needed.")
            stop_movement()


def draw_direction_arrow(frame, direction):

    # Calculate the center of the frame
    frame_center_x = int(FRAME_WIDTH / 2 + VERTICAL_LINE_OFFSET)
    frame_center_y = int(FRAME_HEIGHT / 2)

    # Define the starting point of the arrow (above the x-axis)
    start_point = (frame_center_x, frame_center_y - ARROW_POSITION_OFFSET_Y)

    if direction == 'left':
        end_point = (frame_center_x - ARROW_LENGTH, frame_center_y - ARROW_POSITION_OFFSET_Y)
        color = ARROW_COLOR_LEFT
    elif direction == 'right':
        end_point = (frame_center_x + ARROW_LENGTH, frame_center_y - ARROW_POSITION_OFFSET_Y)
        color = ARROW_COLOR_RIGHT
    else:
        return

    cv2.arrowedLine(frame, start_point, end_point, color, ARROW_THICKNESS, tipLength=0.3)


def process_frame(frame, model, selected_object=None):

    global original_distance, required_distance
    # Detect objects in the frame
    detected_objects = detect_objects(frame, model)

    # Initialize dictionary to store movement directions
    movement_directions = {}  # Dictionary to store movement directions per class

    # Initialize list to store only selected objects
    selected_detected_objects = []

    # Process each detected object
    for obj in detected_objects:
        class_id = obj['class_id']
        class_name = obj['class_name']
        box = obj['box']
        confidence = obj['confidence']

        # If a selected_object is specified, ignore others
        if selected_object and class_name.lower() != selected_object.lower():
            continue

        top_left = (int(box[0]), int(box[1]))
        bottom_right = (int(box[2]), int(box[3]))

        # Calculate horizontal and vertical distances
        horizontal_distance, vertical_distance = calculate_distances(box, FRAME_WIDTH, FRAME_HEIGHT)

        # Store distances in the object dictionary
        obj['horizontal_distance'] = horizontal_distance
        obj['vertical_distance'] = vertical_distance

        # Draw the bounding box and confidence on the frame
        frame = cv2.rectangle(frame, top_left, bottom_right, (0, 255, 0), 2)
        cv2.putText(frame, f"{class_name}: {confidence:.2f}", (top_left[0], top_left[1] - 10),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.9, (36, 255, 12), 2)  # Label text

        # Decide alignment direction based on horizontal distance
        direction = decide_direction(horizontal_distance)

        # Align the robot to center the object
        align_robot(direction, horizontal_distance)
        movement_directions[class_name] = direction  # Capture the direction for arrow drawing

        # Check if the required alignment is reached
        if original_distance is not None and abs(horizontal_distance) <= MIN_PIXEL_DISTANCE:
            logging.info(
                f"Reached required alignment for {class_name}: {abs(horizontal_distance):.2f}px <= {MIN_PIXEL_DISTANCE}px")

        # Append to selected_detected_objects
        selected_detected_objects.append(obj)

    # Handle case when no selected object is detected
    if selected_object:
        if not selected_detected_objects:
            logging.warning(f"Selected object '{selected_object}' not detected in the frame.")
            stop_movement()
    else:
        if len(detected_objects) == 0:
            # No objects detected; stop any ongoing movement
            stop_movement()
            logging.warning("No target objects detected in the frame.")

    # Draw center lines
    frame_center_x = int(FRAME_WIDTH / 2 + VERTICAL_LINE_OFFSET)
    frame_center_y = int(FRAME_HEIGHT / 2)
    cv2.line(frame, (frame_center_x, 0), (frame_center_x, FRAME_HEIGHT), (255, 0, 0), 2)  # Vertical center line
    cv2.line(frame, (0, frame_center_y), (FRAME_WIDTH, frame_center_y), (255, 0, 0), 2)  # Horizontal center line

    # Display horizontal and vertical distances for each detected object
    y_offset = FRAME_HEIGHT - 60
    for obj in selected_detected_objects:
        class_name = obj['class_name']
        horizontal_distance = obj['horizontal_distance']
        vertical_distance = obj['vertical_distance']
        cv2.putText(frame, f"{class_name} Horizontal: {horizontal_distance:.2f}px", (10, y_offset),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
        y_offset += 30
        cv2.putText(frame, f"{class_name} Vertical: {vertical_distance:.2f}px", (10, y_offset),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
        y_offset += 30

    # Draw directional arrows for each movement direction
    for class_name, direction in movement_directions.items():
        if direction in ['left', 'right']:
            draw_direction_arrow(frame, direction)

    return frame, selected_detected_objects


def get_distance():
    try:
        # Run distance.py and capture the output
        result = subprocess.run(['python', 'distance.py'], capture_output=True, text=True, check=True)
        output = result.stdout.strip()
        logging.info(f"Distance Measurement Output: '{output}'")

        if output.lower() == 'error':
            logging.error("Distance measurement error.")
            sys.exit(1)
        elif output.lower() == 'out of range':
            logging.warning("Distance out of range.")
            return float('inf')  # Represent out of range as infinity
        else:
            distance_mm = float(output)
            distance_cm = distance_mm / 10.0  # Convert mm to cm
            logging.info(f"Measured Distance: {distance_cm}cm (Converted from {distance_mm}mm)")  # <-- Modified
            return distance_cm  # <-- Modified
    except subprocess.CalledProcessError:
        logging.error("Failed to run distance.py.")
        sys.exit(1)
    except ValueError:
        logging.error("Invalid distance value received.")
        sys.exit(1)


def move_forward_and_check_distance():
    global step_count, state, previous_distance, DISTANCE_THRESHOLD, STEPS_PER_ALIGNMENT, selected_object  # <-- Added 'selected_object'

    # Get current distance in cm
    current_distance_cm = get_distance()

    if previous_distance is None:
        # Initialize previous_distance
        previous_distance = 1000.0  # A large initial value in cm
        logging.info(f"Initial distance recorded: {previous_distance}cm")

    # Calculate the distance difference needed to reach the threshold
    distance_diff_cm = current_distance_cm - (DISTANCE_THRESHOLD / 10.0)  # Convert mm to cm

    if distance_diff_cm <= 0:
        logging.info(
            f"Distance {current_distance_cm}cm is below or equal to the threshold {DISTANCE_THRESHOLD / 10.0}cm. Transitioning to catching claw.")
        state = STATE_CATCHING_CLAW
        return  # Exit the function to proceed to catching

    # Determine threshold_cm and adjustment_factor based on the selected object
    if selected_object.lower() == "small_bottle":
        threshold_cm = 15.0  # Threshold for small_bottle
        adjustment_factor = 0.45
        logging.info(f"Selected object is 'small_bottle'. Using threshold {threshold_cm}cm and adjustment factor {adjustment_factor}.")
    if selected_object.lower() == "horn":
        threshold_cm = 15.0  # Threshold for small_bottle
        adjustment_factor = 0.6
        logging.info(f"Selected object is 'horn'. Using threshold {threshold_cm}cm and adjustment factor {adjustment_factor}.")
    else:
        threshold_cm = 10.0  # Threshold for other objects
        adjustment_factor = 0.65
        logging.info(f"Selected object is '{selected_object}'. Using threshold {threshold_cm}cm and adjustment factor {adjustment_factor}.")

    move_duration_ms = 200  # Default duration for distance_diff_cm <= 5cm

    if distance_diff_cm > 1.3*threshold_cm:
        # Multiply the distance_diff_cm by the adjustment factor
        adjusted_distance_diff_cm = distance_diff_cm * adjustment_factor
        logging.info(f"Adjusted distance difference: {adjusted_distance_diff_cm}cm ({distance_diff_cm}cm * {adjustment_factor})")

        movement_mapping = [
            (2.5, 100),
            (3, 150),
            (6, 200),
            (10, 450),
            (12, 500),
            (14, 600),
            (16, 700),
            (20, 800),
            (22, 900),
            (24, 1000),
            (27, 1100),
            (30, 1200),
            (33, 1300),
            (36, 1400),
            (37, 1500),
            (40, 1600),
            (42, 1700),
            (44, 1800),
            (46, 1900),
            (55, 2000),
            (65, 2800),
            (75, 3300),
            (85, 3800),
        ]

        for distance_cm, duration_ms in movement_mapping:
            if adjusted_distance_diff_cm <= distance_cm:
                move_duration_ms = duration_ms
                logging.info(f"Mapping adjusted distance {adjusted_distance_diff_cm}cm to duration {move_duration_ms}ms.")
                break
        else:
            # If adjusted_distance_diff_cm exceeds all mappings, use the maximum duration
            move_duration_ms = movement_mapping[-1][1]
            logging.info(f"Adjusted distance {adjusted_distance_diff_cm}cm exceeds all mappings. Using maximum duration {move_duration_ms}ms.")

    elif 5.0 < distance_diff_cm <= threshold_cm:
        # Set movement duration to 300ms for distance_diff_cm between 5cm and threshold_cm
        move_duration_ms = 250
        logging.info(f"Distance difference {distance_diff_cm}cm > 5cm and <= {threshold_cm}cm. Using movement duration {move_duration_ms}ms.")

    else:  # distance_diff_cm <= 5.0
        # Set movement duration to 200ms for distance_diff_cm <= 5cm
        move_duration_ms = 150
        logging.info(f"Distance difference {distance_diff_cm}cm <= 5cm. Using movement duration {move_duration_ms}ms.")

    logging.info(f"Distance difference: {distance_diff_cm}cm => Moving forward for {move_duration_ms}ms.")

    # Move forward with the decided duration
    move_forward(move_duration_ms)
    logging.info(f"Moved forward for {move_duration_ms}ms.")
    # Brief pause to allow movement to complete
    time.sleep(move_duration_ms / 1000.0)
    step_count += 1
    logging.info(f"Completed step {step_count} of {STEPS_PER_ALIGNMENT}.")

    if step_count >= STEPS_PER_ALIGNMENT:
        logging.info(f"Reached {STEPS_PER_ALIGNMENT} steps forward. Transitioning to aligning.")
        state = STATE_ALIGNING
        step_count = 0  # Reset step counter
    else:
        logging.info(f"Ready to perform step {step_count + 1} of {STEPS_PER_ALIGNMENT}.")

    # Update previous_distance
    previous_distance = current_distance_cm






def terminate_program():
    # Release the capture and close windows
    if 'cap' in globals() and cap:
        cap.release()
    cv2.destroyAllWindows()
    logging.info("Video capture released and all windows closed.")

    # Close serial connection if open
    if arduino and arduino.is_open:
        arduino.close()
        logging.info("Serial connection to Arduino closed.")

    # Exit the program
    logging.info("Program terminated successfully.")
    sys.exit(0)


def catch_claw(selected_object):

    catch_claw_command(selected_object)

# Define possible states
STATE_ALIGNING = 'aligning'
STATE_MOVING_FORWARD = 'moving_forward'
STATE_CATCHING_CLAW = 'catching_claw'

# Initialize state
state = STATE_ALIGNING

# Initialize movement timing variables
last_movement_time = 0  # Timestamp of the last movement command
original_distance = None  # Original horizontal distance at first detection
required_distance = 0.0  # 80% of original distance

# Initialize step counter
step_count = 0

# Initialize previous_distance
previous_distance = None

def read_selected_objects_from_file(filename='selected_objects.txt'):
    try:
        with open(filename, 'r') as f:
            selected_objects = json.load(f)
        logging.info(f"Selected objects to pick: {selected_objects}")
        return selected_objects
    except FileNotFoundError:
        logging.error(f"File '{filename}' not found. Ensure that 'selection.py' has been run.")
        sys.exit(1)
    except json.JSONDecodeError:
        logging.error(f"File '{filename}' contains invalid JSON.")
        sys.exit(1)
    except Exception as e:
        logging.error(f"Error reading selected objects from file: {e}")
        sys.exit(1)

def main():
    global cap, state, step_count, previous_distance, selected_object, DISTANCE_THRESHOLD, original_distance, required_distance, STEPS_PER_ALIGNMENT

    selected_objects = read_selected_objects_from_file()

    if not selected_objects:
        logging.error("No objects to pick. Exiting program.")
        terminate_program()

    logging.info(f"Proceeding with selected objects: {selected_objects}")

    for idx, selected_object in enumerate(selected_objects, start=1):
        logging.info(f"\n=== Starting Process for Object {idx}: '{selected_object}' ===")

        selected_object_lower = selected_object.lower()

        if selected_object_lower in DISTANCE_THRESHOLDS:
            if selected_object_lower == "box":  # <-- Modified for case-insensitivity
                STEPS_PER_ALIGNMENT = 2  # Set to 2 for 'box'
                logging.info(f"STEPS_PER_ALIGNMENT set to {STEPS_PER_ALIGNMENT} for '{selected_object}'.")
            else:
                STEPS_PER_ALIGNMENT = 1  # Ensure it's set to 1 for other objects
            DISTANCE_THRESHOLD = DISTANCE_THRESHOLDS[selected_object_lower]
            logging.info(f"DISTANCE_THRESHOLD set to {DISTANCE_THRESHOLD}mm for '{selected_object}'.")
        else:
            DISTANCE_THRESHOLD = DISTANCE_THRESHOLD_DEFAULT
            STEPS_PER_ALIGNMENT = 1  # Ensure it's set to 1 for other objects
            logging.warning(
                f"No distance threshold defined for '{selected_object}'. Using default {DISTANCE_THRESHOLD}mm and STEPS_PER_ALIGNMENT={STEPS_PER_ALIGNMENT}.")

        cap = cv2.VideoCapture(0)
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, FRAME_WIDTH)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, FRAME_HEIGHT)

        max_retries = 5  # Maximum number of camera initialization attempts
        retry_delay = 1  # Seconds to wait between camera retries

        for attempt in range(1, max_retries + 1):
            if cap.isOpened():
                logging.info(f"Camera successfully initialized on attempt {attempt}.")
                break
            else:
                logging.warning(
                    f"Camera initialization failed on attempt {attempt}. Retrying in {retry_delay} second(s)...")
                time.sleep(retry_delay)
                cap.release()
                cap = cv2.VideoCapture(0)
                cap.set(cv2.CAP_PROP_FRAME_WIDTH, FRAME_WIDTH)
                cap.set(cv2.CAP_PROP_FRAME_HEIGHT, FRAME_HEIGHT)
        else:
            logging.error(f"Failed to initialize camera after {max_retries} attempts. Exiting program.")
            terminate_program()

        if not cap.isOpened():
            logging.error("Error: Could not open video stream or file")
            terminate_program()

        logging.info(f"Starting video capture for '{selected_object}'. Press 'q' to exit.")

        # Reset state variables for the new object
        state = STATE_ALIGNING
        step_count = 0
        previous_distance = None
        original_distance = None
        required_distance = 0.0

        # Main loop for the current object
        while True:
            if state == STATE_ALIGNING:
                ret, frame = cap.read()

                if not ret:
                    logging.warning("Frame capture failed. Retrying...")
                    time.sleep(retry_delay)
                    continue

                # Process the frame for alignment and additional classes
                annotated_frame, detected_objects = process_frame(frame, model, selected_object=selected_object)

                # Display the annotated frame
                cv2.imshow(f'YOLOv9m Object Detection and Alignment - {selected_object}', annotated_frame)

                # Check if 'q' is pressed to exit
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    logging.info("Exiting program as 'q' was pressed.")
                    terminate_program()

                # Check if alignment is reached for the selected object
                alignment_achieved = False
                for obj in detected_objects:
                    if obj['class_name'].lower() == selected_object_lower:
                        horizontal_distance = obj['horizontal_distance']
                        if original_distance is not None:
                            if abs(horizontal_distance) <= MIN_PIXEL_DISTANCE:
                                logging.info(
                                    f"Alignment achieved for {selected_object}: {abs(horizontal_distance):.2f}px <= {MIN_PIXEL_DISTANCE}px")
                                alignment_achieved = True
                                break
                        else:
                            logging.info("Initial alignment not yet recorded.")

                if alignment_achieved:
                    # Transition to moving forward state
                    state = STATE_MOVING_FORWARD
                    step_count = 0  # Reset step counter
                    previous_distance = None  # Reset previous distance

            elif state == STATE_MOVING_FORWARD:
                # Move forward and check distance
                move_forward_and_check_distance()

            elif state == STATE_CATCHING_CLAW:
                # Send command to catch the claw
                catch_claw(selected_object)
                # After catching the claw, break to proceed to the next object
                logging.info(f"Completed pickup for '{selected_object}'. Proceeding to the next object.")
                break

            else:
                logging.error(f"Unknown state: {state}. Terminating program.")
                terminate_program()

        # Release the capture and close windows for the current object
        if cap:
            cap.release()
        cv2.destroyAllWindows()
        logging.info(f"Released camera and closed windows for '{selected_object}'.")


if __name__ == "__main__":
    main()

    logging.info("All selected objects have been picked successfully.")
    terminate_program()
