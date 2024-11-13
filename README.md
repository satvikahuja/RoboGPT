basic concept of robogpt inspired by orangewoods labs

# RoboGPT jr🤖

[Watch the Demo Video]([https://github.com/satvikahuja/RoboGPT/blob/main/demo.mp4?raw=true](https://www.youtube.com/watch?v=0gcH466rV34)


RoboGPT jr is an interactive robotic system that leverages OpenAI's GPT-4 model to interpret and execute human commands in real time. Through natural language, users can instruct the robot to move, capture images, perform pick-and-place tasks, and even learn custom moves that can be saved for future use. This project combines NLP, computer vision, and robotics, enabling users to control physical actions through conversational AI.

---

## Features

- Natural Language Processing (NLP): Uses GPT-4 (`gpt-4o-mini` model) to interpret user commands and respond conversationally.
- Real-Time Computer Vision: Captures images and detects objects based on user instructions.
- Autonomous Pick-and-Place: The robot can pick up and place objects with precision.
- Movement Control: Executes movement commands (forward, backward, left, right) and operates a claw mechanism.
- Custom Move Learning: Users can teach RoboGPT a sequence of moves, which it saves for future execution.
- Interactive GUI: A Streamlit-based interface enables users to interact with the robot in a chat-like environment.

---

## Components Used

### Physical Components
- Arduino Microcontroller
- Camera Module
- Motor Driver (4 Channel)
- DC Motors
- Robot Chassis
- Battery Pack
- Robotic Arm with Claw

### Software & Libraries
- Python: Main programming language
- OpenAI API: For GPT-4 model integration
- Streamlit: Interactive user interface
- OpenCV: Image capture and processing
- Arduino IDE: Motor and sensor control

---

## System Requirements

- Python 3.8+
- Arduino hardware (configured with necessary motor and sensor components)
- Camera Module (USB or built-in webcam)
- OpenAI API Key

---

## Installation

1. **Clone this repository**:
   ```bash
   git clone https://github.com/your-username/RoboGPT.git
   cd RoboGPT
   ```

2. **Install the required libraries**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Set up your OpenAI API Key**:
   - Create a `.env` file in the root directory.
   - Add your API key:
     ```plaintext
     OPENAI_API_KEY=your_openai_api_key
     ```

4. **Connect Arduino and Camera**:
   - Ensure the Arduino is connected to the specified port.
   - Check the camera setup for image capture.

---

## Usage

1. **Run the Streamlit Interface**:
   ```bash
   streamlit run robo_control.py
   ```
   Replace `robo_control.py` with the actual filename if different.

2. **Enter Commands**:
   - Type natural language commands to control the robot.
   - Example commands:
     - `"Move forward for 1 second"`
     - `"Capture image and identify objects"`
     - `"Pick up the horn and place it in the box"`
     - `"Teach a dance move with 5 steps"`
   
---

## Command Overview

### Movement Commands

| Command          | Description                                  |
|------------------|----------------------------------------------|
| `forward <ms>`   | Move forward for a specified duration        |
| `backward <ms>`  | Move backward for a specified duration       |
| `left <ms>`      | Turn left for a specified duration           |
| `right <ms>`     | Turn right for a specified duration          |
| `up <ms>`        | Move arm up for a specified duration         |
| `down <ms>`      | Move arm down for a specified duration       |
| `catch <ms>`     | Close claw to catch an object                |
| `release <ms>`   | Open claw to release an object               |

### Pick-and-Place Automation
- To perform pick-and-place actions, use commands such as:
  - `"Pick the bottle and place it in the box"`
  - The system will capture an image if needed, identify the objects, and execute the pick-and-place sequence.

### Teach and Save Moves
- Users can teach RoboGPT a custom sequence of moves:
  - **Command**: `"Teach a dance move with forward and backward steps"`
  - **Response**: RoboGPT saves this as a custom move, which you can later execute by calling `"Execute dance move"`.

---

## Future Enhancements
- **Improved Object Detection**: Integrate advanced computer vision techniques for more accurate object recognition.
- **Voice Control**: Add voice command capabilities.
- **Enhanced GUI**: Upgrade the Streamlit interface with visual feedback on robot actions.

---

## Troubleshooting

### Common Errors
```plaintext
- OpenAI API Errors: Ensure the API key is valid and up-to-date.
- Camera Not Found: Verify the camera is correctly connected and configured.
- Arduino Port Issues: Confirm the Arduino is connected to the specified port and recognized by the OS.
```

### Logs and Debugging
Enable detailed logging to view errors and track command execution:
```python
logging.basicConfig(level=logging.DEBUG)
```

---

## License
This project is licensed under the MIT License.

---

## Acknowledgments
- **OpenAI** for GPT-4 API.
- **Streamlit** for creating a flexible UI platform.
- **Arduino** for open-source hardware.
```

Replace placeholders such as `"robo_control.py"`, `"your_openai_api_key"`, and `"your-username"` with actual values before using this `README.md` on GitHub. This version should be clear and informative for anyone viewing the project.
