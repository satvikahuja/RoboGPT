#include <Wire.h>
#include <Adafruit_VL53L0X.h>

// Create an instance of the VL53L0X sensor
Adafruit_VL53L0X lox = Adafruit_VL53L0X();

// Define Motor 1 pins (Base Movement)
const int motor1_dir = 2;  // Motor 1 Direction pin connected to Arduino D2
const int motor1_pwm = 9;  // Motor 1 PWM pin connected to Arduino D9

// Define Motor 2 pins (Base Movement)
const int motor2_dir = 3;  // Motor 2 Direction pin connected to Arduino D3
const int motor2_pwm = 10; // Motor 2 PWM pin connected to Arduino D10

// Define Motor 3 pins (Claw Catch/Release)
const int motor3_dir = 4;  // Motor 3 Direction pin connected to Arduino D4
const int motor3_pwm = 11; // Motor 3 PWM pin connected to Arduino D11

// Define Motor 4 pins (Claw Up/Down)
const int motor4_dir = 6;  // Motor 4 Direction pin connected to Arduino D6
const int motor4_pwm = 5;  // Motor 4 PWM pin connected to Arduino D5

// Threshold Distance (in millimeters)
const int MIN_DISTANCE_THRESHOLD = 1000; // 1 meter

// Maximum number of sensor initialization attempts
const int MAX_INIT_ATTEMPTS = 30;

// Delay between initialization attempts (in milliseconds)
const unsigned long INIT_DELAY_MS = 100;

// Flag to indicate sensor initialization status
bool sensorInitialized = false;

// Function Prototypes
void moveBase(String direction, int duration);
void moveLeft(int duration);
void moveRight(int duration);
void controlClaw(String action, int duration);
void moveClaw(String direction, int duration);
void stopAllMotors();
void measureDistance();

void setup() {
  // Initialize all motor pins as outputs
  pinMode(motor1_dir, OUTPUT);
  pinMode(motor1_pwm, OUTPUT);

  pinMode(motor2_dir, OUTPUT);
  pinMode(motor2_pwm, OUTPUT);

  pinMode(motor3_dir, OUTPUT);
  pinMode(motor3_pwm, OUTPUT);

  pinMode(motor4_dir, OUTPUT);
  pinMode(motor4_pwm, OUTPUT);

  // Initialize serial communication
  Serial.begin(9600);
  while (!Serial) {
    delay(1); // Wait for Serial to initialize
  }

  // Attempt to initialize VL53L0X Sensor with retries
  for (int attempt = 1; attempt <= MAX_INIT_ATTEMPTS; attempt++) {
    if (lox.begin()) {
      sensorInitialized = true;
      Serial.println("VL53L0X initialized");
      break; // Exit loop if initialization is successful
    } else {
      Serial.print("VL53L0X initialization failed (Attempt ");
      Serial.print(attempt);
      Serial.println(")");
      delay(INIT_DELAY_MS); // Wait before retrying
    }
  }

  if (!sensorInitialized) {
    Serial.println("Failed to initialize VL53L0X after multiple attempts");
  }
}

void loop() {
  // Handle incoming serial commands
  if (Serial.available() > 0) {
    String command = Serial.readStringUntil('\n');  // Read until newline
    command.trim();  // Remove any leading/trailing whitespace
    int spaceIndex = command.indexOf(' ');  // Split command and duration

    // Check if there's a space separating command and duration
    if (spaceIndex == -1) {
      // If the command is 'distance', measure and return distance
      if (command.equalsIgnoreCase("distance")) {
        measureDistance();
      } else {
        Serial.println("Error: Invalid command format.");
      }
      return;
    }

    String action = command.substring(0, spaceIndex);
    int duration = command.substring(spaceIndex + 1).toInt();

    if (action == "forward") moveBase("forward", duration);
    else if (action == "backward") moveBase("backward", duration);
    else if (action == "left") moveLeft(duration);
    else if (action == "right") moveRight(duration);
    else if (action == "catch") controlClaw("catch", duration);
    else if (action == "release") controlClaw("release", duration);
    else if (action == "up") moveClaw("up", duration);
    else if (action == "down") moveClaw("down", duration);
    else {
      Serial.println("Error: Unknown command received.");
    }
  }
}

// Function to measure and send distance
void measureDistance() {
  if (sensorInitialized) {
    VL53L0X_RangingMeasurementData_t measure;
    lox.rangingTest(&measure, false); // Set to 'true' for debug data

    if (measure.RangeStatus != 4) {  // 4 indicates out of range
      Serial.print("Distance (mm): ");
      Serial.println(measure.RangeMilliMeter);
    } else {
      Serial.println("Distance: Out of range");
    }
  } else {
    Serial.println("Error: VL53L0X sensor not initialized");
  }
}

// Function to control base movement forward and backward
void moveBase(String direction, int duration) {
  if (direction == "forward") {
    digitalWrite(motor1_dir, HIGH);
    analogWrite(motor1_pwm, 160);
    digitalWrite(motor2_dir, LOW);
    analogWrite(motor2_pwm, 200);
  } else if (direction == "backward") {
    digitalWrite(motor1_dir, LOW);
    analogWrite(motor1_pwm, 200);
    digitalWrite(motor2_dir, HIGH);
    analogWrite(motor2_pwm, 160);
  }

  delay(duration);
  analogWrite(motor1_pwm, 0);
  analogWrite(motor2_pwm, 0);
}

// Function to move base left (rotate counterclockwise)
void moveLeft(int duration) {
  digitalWrite(motor1_dir, HIGH);
  analogWrite(motor1_pwm, 200);
  digitalWrite(motor2_dir, HIGH);
  analogWrite(motor2_pwm, 200);

  delay(duration);
  analogWrite(motor1_pwm, 0);
  analogWrite(motor2_pwm, 0);
}

// Function to move base right (rotate clockwise)
void moveRight(int duration) {
  digitalWrite(motor1_dir, LOW);
  analogWrite(motor1_pwm, 200);
  digitalWrite(motor2_dir, LOW);
  analogWrite(motor2_pwm, 200);

  delay(duration);
  analogWrite(motor1_pwm, 0);
  analogWrite(motor2_pwm, 0);
}

// Function to control the claw (catch and release)
void controlClaw(String action, int duration) {
  if (action == "catch") {
    digitalWrite(motor3_dir, HIGH);
    analogWrite(motor3_pwm, 255);
  } else if (action == "release") {
    digitalWrite(motor3_dir, LOW);
    analogWrite(motor3_pwm, 255);
  }

  delay(duration);
  analogWrite(motor3_pwm, 0);
}

// Function to control claw movement (up and down)
void moveClaw(String direction, int duration) {
  if (direction == "up") {
    digitalWrite(motor4_dir, LOW);
    analogWrite(motor4_pwm, 255);
  } else if (direction == "down") {
    digitalWrite(motor4_dir, HIGH);
    analogWrite(motor4_pwm, 255);
  }

  delay(duration);
  analogWrite(motor4_pwm, 0);
}
