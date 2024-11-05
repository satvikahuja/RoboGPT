import serial
import time
import sys


def find_distance(
        serial_port='/dev/cu.usbserial-1130', 
        baud_rate=9600,
        timeout=2,  
        max_attempts=3,  
        retry_delay=0.5  
):
    
    try:
        
        arduino = serial.Serial(serial_port, baud_rate, timeout=timeout)
        
    except serial.SerialException:
        print("Error")
        sys.exit(1)

    arduino.reset_input_buffer()
    arduino.reset_output_buffer()

    while arduino.in_waiting > 0:
        arduino.readline()

    for attempt in range(1, max_attempts + 1):
        try:
            command = "distance\n"
            arduino.write(command.encode())
            arduino.flush()  
            time.sleep(0.5)  

            if arduino.in_waiting > 0:
                response = arduino.readline().decode('utf-8').strip()

                if "Distance (mm):" in response:
                    distance_mm = response.split(":")[1].strip()
                    print(distance_mm) 
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
                    if attempt < max_attempts:
                        print(f"No valid response. Retrying {attempt}/{max_attempts}...")
                        time.sleep(retry_delay)
                    else:
                        print("Error")
            else:
                if attempt < max_attempts:
                    print(f"No response. Retrying {attempt}/{max_attempts}...")
                    time.sleep(retry_delay)
                else:
                    print("Error")

        except serial.SerialException:
            if attempt < max_attempts:
                print(f"Serial connection error. Retrying {attempt}/{max_attempts}...")
                time.sleep(retry_delay)
            else:
                print("Error")
        except Exception:
            if attempt < max_attempts:
                print(f"Unexpected error. Retrying {attempt}/{max_attempts}...")
                time.sleep(retry_delay)
            else:
                print("Error")

    arduino.close()


if __name__ == "__main__":
    find_distance(serial_port='/dev/cu.usbserial-1130')
