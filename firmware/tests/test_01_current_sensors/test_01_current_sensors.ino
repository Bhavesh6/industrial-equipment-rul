/*
 * TEST 01: ACS712 Current Sensors (Motor Current on GPIO 36 & Total Current on GPIO 33)
 * -------------------------------------------------------------------------------------
 * Tests:
 * 1. Zero-current quiescent ADC values and voltages (when motor is stopped).
 * 2. Motor spin-up at PWM 100, 150, 200, 255 to measure current under no-load / load.
 * 3. Shows Raw ADC, Pin Voltage (V), and Calculated Amperes (A).
 * 
 * Pins:
 * - ACS712 Motor Current: GPIO 36 (VP) via voltage divider
 * - ACS712 Total Current: GPIO 33 via voltage divider
 * - L298N ENA (PWM): GPIO 25
 * - L298N IN1: GPIO 26
 * - L298N IN2: GPIO 27
 */

#include <Arduino.h>

#define PIN_CURR_MOTOR 36   // SENSOR_VP
#define PIN_CURR_TOTAL 33   // ADC1_CH5

#define PIN_PWM        25   // ENA
#define PIN_IN1        26   // IN1
#define PIN_IN2        27   // IN2

const float V_REF = 3.30;
const float ADC_MAX = 4095.0;

// ACS712 parameters:
// 20A module sensitivity = 0.100 V/A (change to 0.185 for 5A, 0.066 for 30A)
const float ACS_SENSITIVITY = 0.100;
// Measured output divider ratio: 1.139V / 2.500V = 0.4556
float acs_divider_factor = 0.456;

float zero_v_motor = 1.139;
float zero_v_total = 1.137;

// Averages 100 samples spaced 200us apart = 20ms window (cancels 5kHz PWM ripple & 50Hz mains noise)
float read_avg_volts(int pin, int samples = 100) {
  uint32_t sum = 0;
  for (int i = 0; i < samples; i++) {
    sum += analogRead(pin);
    delayMicroseconds(200);
  }
  float avg = (float)sum / samples;
  return (avg / ADC_MAX) * V_REF;
}

void set_motor(int pwm) {
  pwm = constrain(pwm, 0, 255);
  #if ESP_ARDUINO_VERSION_MAJOR >= 3
    ledcWrite(PIN_PWM, pwm);
  #else
    ledcWrite(0, pwm);
  #endif

  if (pwm > 0) {
    digitalWrite(PIN_IN1, HIGH);
    digitalWrite(PIN_IN2, LOW);
  } else {
    digitalWrite(PIN_IN1, LOW);
    digitalWrite(PIN_IN2, LOW);
  }
}

void setup() {
  Serial.begin(115200);
  delay(1200);
  Serial.println("\n========================================================");
  Serial.println(" TEST 01: ACS712 CURRENT SENSORS (GPIO 36 & GPIO 33)");
  Serial.println("========================================================");

  analogSetAttenuation(ADC_11db);

  pinMode(PIN_IN1, OUTPUT);
  pinMode(PIN_IN2, OUTPUT);

  #if ESP_ARDUINO_VERSION_MAJOR >= 3
    ledcAttach(PIN_PWM, 5000, 8);
  #else
    ledcSetup(0, 5000, 8);
    ledcAttachPin(PIN_PWM, 0);
  #endif

  set_motor(0);

  pinMode(PIN_CURR_MOTOR, INPUT);
  pinMode(PIN_CURR_TOTAL, INPUT);

  // Measure zero-current quiescent voltage
  Serial.println("\n[1] Motor OFF: Measuring 0A baseline voltage (100 samples)...");
  delay(1000);
  zero_v_motor = read_avg_volts(PIN_CURR_MOTOR, 100);
  zero_v_total = read_avg_volts(PIN_CURR_TOTAL, 100);

  Serial.printf("    Motor Current (GPIO 36) Zero V: %.3f V\n", zero_v_motor);
  Serial.printf("    Total Current (GPIO 33) Zero V: %.3f V\n", zero_v_total);
  Serial.println("--------------------------------------------------------");
  Serial.println("Commands available in Serial Monitor (type and press Enter):");
  Serial.println("  0   -> Motor STOP");
  Serial.println("  1   -> Motor Speed 40%  (PWM 100)");
  Serial.println("  2   -> Motor Speed 65%  (PWM 165)");
  Serial.println("  3   -> Motor Speed 85%  (PWM 215)");
  Serial.println("  4   -> Motor Speed 100% (PWM 255)");
  Serial.println("  cal -> Re-zero calibration at current state");
  Serial.println("========================================================\n");
}

int current_pwm = 0;
unsigned long last_print = 0;

void loop() {
  // Check for serial input commands
  if (Serial.available()) {
    String cmd = Serial.readStringUntil('\n');
    cmd.trim();
    if (cmd == "0") {
      current_pwm = 0;
      set_motor(0);
      Serial.println("\n--> Motor STOPPED");
    } else if (cmd == "1") {
      current_pwm = 100;
      set_motor(100);
      Serial.println("\n--> Motor RUNNING @ PWM 100 (40%)");
    } else if (cmd == "2") {
      current_pwm = 165;
      set_motor(165);
      Serial.println("\n--> Motor RUNNING @ PWM 165 (65%)");
    } else if (cmd == "3") {
      current_pwm = 215;
      set_motor(215);
      Serial.println("\n--> Motor RUNNING @ PWM 215 (85%)");
    } else if (cmd == "4") {
      current_pwm = 255;
      set_motor(255);
      Serial.println("\n--> Motor RUNNING @ FULL SPEED (PWM 255)");
    } else if (cmd.equalsIgnoreCase("cal")) {
      set_motor(0);
      delay(500);
      zero_v_motor = read_avg_volts(PIN_CURR_MOTOR, 100);
      zero_v_total = read_avg_volts(PIN_CURR_TOTAL, 100);
      Serial.printf("\n[RE-CALIB] Zero Motor: %.3f V | Zero Total: %.3f V\n", zero_v_motor, zero_v_total);
    }
  }

  // Periodic display every 300 ms
  if (millis() - last_print >= 300) {
    last_print = millis();

    float v_mot = read_avg_volts(PIN_CURR_MOTOR, 40);
    float v_tot = read_avg_volts(PIN_CURR_TOTAL, 40);

    float eff_sens = ACS_SENSITIVITY * acs_divider_factor;
    float delta_vm = v_mot - zero_v_motor;
    float delta_vt = v_tot - zero_v_total;

    float i_mot = abs(delta_vm / eff_sens);
    float i_tot = abs(delta_vt / eff_sens);

    // Filter tiny ADC noise
    if (i_mot < 0.05) i_mot = 0.0;
    if (i_tot < 0.05) i_tot = 0.0;

    Serial.printf("[PWM: %3d] | MotorCurr (GPIO36): Pin=%.3fV (Δ=%.3fV) -> %5.2f A | TotalCurr (GPIO33): Pin=%.3fV -> %5.2f A\n",
                  current_pwm, v_mot, delta_vm, i_mot, v_tot, i_tot);
  }
}
