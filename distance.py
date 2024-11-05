import serial
import time
import sys


def find_distance(
        serial_port='/dev/cu.usbserial-1130',  # Replace with your Arduino's serial port
        baud_rate=9600,
        timeout=2,  # Timeout for serial read in seconds
        max_attempts=3,  # Total number of attempts
        retry_delay=0.5  # Delay between attempts in seconds
):
    """
    Connects to the Arduino via serial, sends a 'distance' command,
    and prints only the measured distance. Retries up to max_attempts
    times if unsuccessful without disconnecting the Arduino.

    Parameters:
    - serial_port (str): The serial port to which Arduino is connected.
    - baud_rate (int): The baud rate for serial communication.
    - timeout (int): Read timeout in seconds.
    - max_attempts (int): Maximum number of retry attempts.
    - retry_delay (int): Delay between retries in seconds.
    """
    try:
        # Establish serial connection
        # Uncomment the next line for debugging purposes
        # print(f"Connecting to Arduino on {serial_port} at {baud_rate} baud.")
        arduino = serial.Serial(serial_port, baud_rate, timeout=timeout)
        # time.sleep(0.5)  # Wait for Arduino to initialize
        # Uncomment the next line for debugging purposes
        # print("Serial connection established.")
    except serial.SerialException:
        print("Error")
        sys.exit(1)

    # Clear any residual data in the serial buffer
    arduino.reset_input_buffer()
    arduino.reset_output_buffer()

    # Read and discard any initialization messages from Arduino
    while arduino.in_waiting > 0:
        arduino.readline()

    for attempt in range(1, max_attempts + 1):
        try:
            # Send the 'distance' command
            command = "distance\n"
            arduino.write(command.encode())
            arduino.flush()  # Ensure the command is sent immediately
            time.sleep(0.5)  # Wait for Arduino to process the command

            # Check if there's data waiting in the serial buffer
            if arduino.in_waiting > 0:
                response = arduino.readline().decode('utf-8').strip()

                # Determine what to print based on response
                if "Distance (mm):" in response:
                    distance_mm = response.split(":")[1].strip()
                    print(distance_mm)  # Print only the distance value
                    arduino.close()
                    sys.exit(0)
                elif "Distance: Out of range" in response:
                    print("Out of range")
                    arduino.close()
                    sys.exit(0)
                elif "Error" in response:
                    print("Error")
                    arduino.close()
                    sys.exit(0)
                else:
                    # Invalid or unexpected response, retry
                    if attempt < max_attempts:
                        print(f"No valid response. Retrying {attempt}/{max_attempts}...")
                        time.sleep(retry_delay)
                    else:
                        print("Error")
            else:
                # No response received, retry
                if attempt < max_attempts:
                    print(f"No response. Retrying {attempt}/{max_attempts}...")
                    time.sleep(retry_delay)
                else:
                    print("Error")

        except serial.SerialException:
            # Handle serial connection errors
            if attempt < max_attempts:
                print(f"Serial connection error. Retrying {attempt}/{max_attempts}...")
                time.sleep(retry_delay)
            else:
                print("Error")
        except Exception:
            # Handle any other unexpected errors
            if attempt < max_attempts:
                print(f"Unexpected error. Retrying {attempt}/{max_attempts}...")
                time.sleep(retry_delay)
            else:
                print("Error")

    # After all attempts failed
    arduino.close()


if __name__ == "__main__":
    # Replace '/dev/cu.usbserial-2130' with your actual Arduino port
    # For Windows, it might be 'COM3', 'COM4', etc.
    find_distance(serial_port='/dev/cu.usbserial-1130')
