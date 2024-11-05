
import streamlit as st
import openai
import serial
import time
import os
import base64
import re
import cv2
import subprocess
import sys
import logging
import json
from dotenv import load_dotenv

load_dotenv()
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY') or st.secrets.get("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    st.error("OpenAI API key not found. Please set the OPENAI_API_KEY environment variable or add it to Streamlit secrets.")
    st.stop()
openai.api_key = OPENAI_API_KEY

arduino_port = '/dev/cu.usbserial-1130'  
baud_rate = 9600

logging.basicConfig(
    level=logging.INFO,  
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)

st.set_page_config(page_title="RoboGPT", page_icon="🤖")


CLASS_NAMES = ['bottle', 'box', 'cup', 'horn', 'small_bottle']

# Define synonyms for each class
SYNONYMS = {
    'bottle': ['flask', 'jar', 'vial'],
    'box': ['container', 'cardboard'],
    'cup': ['glass', 'mug', 'beaker', 'tumbler'],
    'horn': ['trumpet', 'trombone', 'bugle', 'French horn'],
    'small_bottle': ['mini bottle', 'small container', 'tiny flask']
}

# Create a reverse mapping for easy lookup
SYNONYM_MAP = {}
for class_name, synonyms in SYNONYMS.items():
    for synonym in synonyms:
        SYNONYM_MAP[synonym.lower()] = class_name

def main():
    st.title("🤖 RoboGPT")

    # Initialize session state variables
    if 'conversation_history' not in st.session_state:
        st.session_state.conversation_history = []

    if 'arduino' not in st.session_state:
        try:
            # Initialize serial connection
            st.session_state.arduino = serial.Serial(arduino_port, baud_rate, timeout=1)
            time.sleep(2)  # Wait for connection to initialize
            st.success(f"Connected to Arduino on {arduino_port}")
        except serial.SerialException as e:
            st.error(f"Error connecting to Arduino: {e}")
            st.stop()

    if 'pick_and_place_active' not in st.session_state:
        st.session_state.pick_and_place_active = False

    display_conversation()

    user_input = st.chat_input("You:")
    if user_input:
        st.session_state.conversation_history.append({"role": "user", "content": user_input})

        interpreted_commands = interpret_command_with_gpt4(user_input)

        if interpreted_commands:
            for cmd in interpreted_commands:
                if cmd == "RUN_PICK_AND_PLACE":
                    run_pick_and_place()
                    st.session_state.pick_and_place_active = False
                else:
                    try:
                        command, duration = cmd.split()
                        send_command_to_arduino(command, int(duration))
                    except ValueError:
                        st.error("Error parsing the interpreted command.")
        else:
            st.write("No command executed; only conversational reply provided.")

        display_conversation()

def display_conversation():
    for message in st.session_state.conversation_history:
        if message['role'] == 'user':
            with st.chat_message("user"):
                st.markdown(message['content'])
        elif message['role'] == 'assistant':
            with st.chat_message("assistant"):
                st.markdown(message['content'])

def capture_and_resize_image(filename="surroundings.jpg", size=(720, 720), max_retries=5):
    """Capture an image using the default camera, retrying up to max_retries times if capture fails."""
    cap = cv2.VideoCapture(0)
    time.sleep(2)  

    retry_count = 0
    success = False
    while retry_count < max_retries:
        ret, frame = cap.read()
        if ret:
            resized_frame = cv2.resize(frame, size)
            cv2.imwrite(filename, resized_frame)
            print(f"Image captured, resized to {size}, and saved as {filename}")
            success = True
            break
        else:
            print(f"Retrying to capture image... Attempt {retry_count + 1}")
            retry_count += 1
            time.sleep(0.5)  

    cap.release()
    return filename if success else None

def encode_image(image_path):
    """Encode an image to a Base64 string."""
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode("utf-8")

def send_image_to_gpt(user_instruction, image_path):
    """Send an image to GPT-4 Mini Vision along with the user instruction."""
    base64_image = encode_image(image_path)
    response = openai.ChatCompletion.create(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "system",
                "content": (
                    "You are a robotic assistant with vision capabilities. When an image is provided, analyze it based on the user's specific instructions. "
                    "If the user requests an action based on detecting certain objects (e.g., a bottle or human), interpret the image accordingly. "
                    "If the requested object is detected, respond by confirming the action and providing the commands within 'BEGIN COMMANDS' and 'END COMMANDS' tags.\n\n"
                    "The robot supports the following commands:\n"
                    "- 'forward <duration>': Move the robot forward for a specified duration in milliseconds.\n"
                    "- 'backward <duration>': Move the robot backward for a specified duration in milliseconds.\n"
                    "- 'left <duration>': Turn the robot to the left for a specified duration in milliseconds.\n"
                    "- 'right <duration>': Turn the robot to the right for a specified duration in milliseconds.\n"
                    "- 'up <duration>': Move the robot's arm up for a specified duration in milliseconds.\n"
                    "- 'down <duration>': Move the robot's arm down for a specified duration in milliseconds.\n"
                    "- 'catch <duration>': Close the claw to catch an object.\n"
                    "- 'release <duration>': Open the claw to release an object.\n\n"
                    "If the object requested by the user is present in the image, include the appropriate command sequence within 'BEGIN COMMANDS' and 'END COMMANDS'."
                )
            },
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": user_instruction},
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}
                    }
                ]
            }
        ]
    )

    llm_output = response['choices'][0]['message']['content'].strip()

    st.session_state.conversation_history.append({"role": "assistant", "content": llm_output})

    if "BEGIN COMMANDS" in llm_output and "END COMMANDS" in llm_output:
        try:
            command_block = re.search(r"BEGIN COMMANDS\s+(.*?)\s+END COMMANDS", llm_output, re.DOTALL).group(1)
            return [line.strip() for line in command_block.splitlines() if line.strip()]
        except (IndexError, AttributeError):
            st.error("Error: Could not parse commands from GPT response.")
            return []
    else:
        st.write("No actionable commands detected; description only.")
        return []

def send_command_to_arduino(command, duration=500):
    full_command = f"{command} {duration}\n"
    st.session_state.arduino.write(full_command.encode())
    st.write(f"Sent to Arduino: {full_command.strip()}")
    time.sleep(duration / 900)

def run_pick_and_place():
    logging.info(f"=== Starting Pick and Place Process ===")

    logging.info(f"Running 'pipeline.py' to execute pick and place...")
    run_script('pipeline.py')

    logging.info(f"=== Pick and Place Process Completed ===")
    st.write("Pick and place operation completed successfully.")

def run_script(script_name):
    try:
        result = subprocess.run(['python', script_name], check=True, capture_output=True, text=True)
        st.write(f"Script '{script_name}' output:\n{result.stdout}")
    except subprocess.CalledProcessError as e:
        st.error(f"Script '{script_name}' exited with an error: {e.stderr}")
    except FileNotFoundError:
        st.error(f"Script '{script_name}' not found. Please ensure it exists in the current directory.")
    except Exception as e:
        st.error(f"An unexpected error occurred while running '{script_name}': {e}")

def interpret_command_with_gpt4(user_input):
    """Use GPT-4 Mini to interpret the user's natural language command with context."""
    system_prompt = (
        "You are a robotic assistant with movement, vision, and pick-and-place capabilities. Interpret user commands, "
        "including capturing images, detecting objects, moving around, and picking up items. For commands related to picking and placing objects, "
        "extract all object names mentioned in the command and include them in a comma-separated list. "
        "Then, execute the necessary scripts to perform the action.\n\n"

        "Commands the robot supports:\n"
        "- 'forward <duration>': Move forward for the specified duration in milliseconds.\n"
        "- 'backward <duration>': Move backward for a specified duration in milliseconds.\n"
        "- 'left <duration>': Turn left for the specified duration.\n"
        "- 'right <duration>': Turn right for the specified duration.\n"
        "- 'up <duration>': Move the robot's arm up for a specified duration in milliseconds.\n"
        "- 'down <duration>': Move the robot's arm down for a specified duration in milliseconds.\n"            
        "- 'catch <duration>': Catch with the claw.\n"
        "- 'release <duration>': Release with the claw.\n"
        "- 'stop 0': Stop all movements.\n"
        "- 'RUN_PICK_AND_PLACE': Run pick and place scripts to pick up the selected object(s).\n\n"

        "Encapsulate actionable commands in 'BEGIN COMMANDS' and 'END COMMANDS' tags. Ensure image-based requests "
        "are processed by capturing an image, analyzing it for specific objects, and responding accordingly."
    )

    # Prepare messages, including system prompt and conversation history
    messages = [{"role": "system", "content": system_prompt}]

    # Limit conversation history to the last N messages
    N = 25  # Adjust as needed
    conversation_snippet = st.session_state.conversation_history[-N:]

    messages.extend(conversation_snippet)

    # Add current user input
    messages.append({"role": "user", "content": user_input})

    # Determine if the command implies image capture
    vision_keywords = ["see", "observe", "detect", "look at", "scan", "show me"]
    pick_place_keywords = ["pick", "place", "select", "grasp", "grab", "transport"]
    # Removed 'move' from pick_place_keywords

    # Use regular expressions to match whole words
    pick_place_pattern = r'\b(' + '|'.join(pick_place_keywords) + r')\b'
    vision_pattern = r'\b(' + '|'.join(vision_keywords) + r')\b'

    if re.search(vision_pattern, user_input.lower()):
        st.write("An image is required for this command. Capturing image...")
        filename = capture_and_resize_image()

        if filename:
            # Now, send the image to GPT
            action_commands = send_image_to_gpt(user_input, filename)
            return action_commands
        else:
            st.write("Image capture failed.")
            return []
    elif re.search(pick_place_pattern, user_input.lower()):
        # For pick and place commands, extract objects using GPT-4
        extracted_objects = extract_objects_from_command(user_input)
        if extracted_objects:
            # Validate and process the extracted objects
            selected_objects = process_selected_objects(extracted_objects)
            if selected_objects:
                # Write selected objects to 'selected_objects.txt'
                write_selected_objects_to_file(selected_objects)
                st.write(f"Objects '{', '.join(selected_objects)}' selected for pick and place.")
                st.session_state.pick_and_place_active = True
                return ["RUN_PICK_AND_PLACE"]
            else:
                st.write("No valid objects found. Please try again.")
                return []
        else:
            st.write("No objects detected in your command. Please try again.")
            return []
    else:
        try:
            # Call GPT-4 Mini API
            response = openai.ChatCompletion.create(
                model="gpt-4o-mini",
                messages=messages,
                temperature=0
            )
            llm_output = response['choices'][0]['message']['content'].strip()

            # Log the assistant's response for debugging
            logging.info(f"Assistant's response: {llm_output}")

            # Update conversation history with assistant's response
            st.session_state.conversation_history.append({"role": "assistant", "content": llm_output})

            # Extract commands if present
            if "BEGIN COMMANDS" in llm_output and "END COMMANDS" in llm_output:
                command_block = re.search(r"BEGIN COMMANDS\s+(.*?)\s+END COMMANDS", llm_output, re.DOTALL).group(1)
                return [line.strip() for line in command_block.splitlines() if line.strip()]
            else:
                st.write(llm_output)
                return []
        except Exception as e:
            st.error(f"Error with LLM interpretation: {e}")
            return []

def extract_objects_from_command(command, model="gpt-4o-mini"):

    messages = [
        {
            "role": "system",
            "content": f"You are a helpful assistant that extracts and maps object names from user commands to a predefined list of objects. The available objects are: {', '.join(CLASS_NAMES)} and their synonyms. Respond with a comma-separated list of object names in the order they appear in the command. Do not include any additional text."
        },
        {
            "role": "user",
            "content": command
        }
    ]

    try:
        response = openai.ChatCompletion.create(
            model=model,
            messages=messages,
            max_tokens=50,
            temperature=0.0,  # Set to 0 for deterministic output
            n=1,
            stop=["\n"]  # Stop at newline to prevent additional text
        )
        extracted_text = response['choices'][0]['message']['content'].strip().lower()

        extracted_objects = [obj.strip() for obj in extracted_text.split(',') if obj.strip()]

        logging.debug(f"Raw GPT-4o-mini response: '{response['choices'][0]['message']['content']}'")
        logging.debug(f"Extracted Objects List: {extracted_objects}")

        return extracted_objects
    except Exception as e:
        logging.error(f"Error communicating with OpenAI API: {e}")
        return []

def process_selected_objects(extracted_objects):
    valid_selections = []
    for obj in extracted_objects:
        if obj in CLASS_NAMES:
            valid_selections.append(obj)
        elif obj in SYNONYM_MAP:
            mapped_obj = SYNONYM_MAP[obj]
            logging.info(f"Mapped '{obj}' to '{mapped_obj}'")
            valid_selections.append(mapped_obj)
        else:
            logging.warning(f"Extracted object '{obj}' is not recognized.")
            st.write(f"'{obj}' is not a valid object. Please choose from: {', '.join(CLASS_NAMES)}.")

    if valid_selections:
        return valid_selections
    else:
        return []

def write_selected_objects_to_file(selected_objects, filename='selected_objects.txt'):

    try:
        with open(filename, 'w') as f:
            json.dump(selected_objects, f)
        logging.info(f"Selected objects {selected_objects} written to '{filename}'.")
    except Exception as e:
        logging.error(f"Error writing selected objects to file: {e}")

if __name__ == "__main__":
    main()



