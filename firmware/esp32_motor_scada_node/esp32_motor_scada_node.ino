/*
 * ==============================================================================
 * RS-380 DC Motor Prognostics & Battery SCADA Node
 * Firmware for ESP32 DevKit V1 (30-pin / 38-pin)
 * ==============================================================================
 * 
 * SENSOR & ACTUATOR PIN MAP:
 * ------------------------------------------------------------------------------
 * | Component                | Pin Description        | ESP32 Pin             |
 * |--------------------------|------------------------|-----------------------|
 * | L298N Motor Driver       | ENA (LEDC PWM Speed)   | GPIO 25               |
 * |                          | IN1 (Direction A)      | GPIO 26               |
 * |                          | IN2 (Direction B)      | GPIO 27               |
 * |                          | GND                    | Common GND            |
 * | ACS712 Total Current     | OUT (via Divider)      | GPIO 33 (ADC1_CH5)    |
 * | ACS712 Motor Current     | OUT (via Divider)      | GPIO 36 (SENSOR_VP)   |
 * | Battery Divider B1       | Cell 1 Tap (30k/4.7k)  | GPIO 32 (ADC1_CH4)    |
 * | Battery Divider B2       | Cell 1+2 (30k/4.7k)    | GPIO 34 (ADC1_CH6)    |
 * | Battery Divider B+       | Full Pack (30k/4.7k)   | GPIO 35 (ADC1_CH7)    |
 * | DS18B20 Temperature      | DATA (4.7kΩ pull-up)   | GPIO 4                |
 * | 801S Vibration Sensor    | AO (Analog Waveform)   | GPIO 39 (SENSOR_VN)   |
 * | KY-040 Rotary Encoder    | CLK                    | GPIO 18               |
 * |                          | DT                     | GPIO 19               |
 * |                          | SW (Push Button)       | GPIO 23               |
 * ------------------------------------------------------------------------------
 * 
 * LIBRARIES REQUIRED:
 * - OneWire (by Paul Stoffregen)
 * - DallasTemperature (by Miles Burton)
 * 
 * TELEMETRY PROTOCOL:
 * Streams JSON over Serial (115200 baud) compatible with the Python SCADA
 * dashboard and Machine Learning RUL Predictor.
 * ==============================================================================
 */

#include <Arduino.h>
#include <OneWire.h>
#include <DallasTemperature.h>

// ------------------------------------------------------------------------------
// PIN ASSIGNMENTS
// ------------------------------------------------------------------------------
#define PIN_MOTOR_PWM     25   // ENA (PWM speed control)
#define PIN_MOTOR_IN1     26   // IN1 (Direction forward)
#define PIN_MOTOR_IN2     27   // IN2 (Direction reverse)

#define PIN_CURR_TOTAL    33   // ACS712 Total system current (ADC1)
#define PIN_CURR_MOTOR    36   // ACS712 Motor current (SENSOR_VP, ADC1)

#define PIN_BATT_B1       32   // Battery Tap 1 (Cell 1, ~3.7V - 4.2V)
#define PIN_BATT_B2       34   // Battery Tap 2 (Cell 1+2, ~7.4V - 8.4V)
#define PIN_BATT_B_PACK   35   // Battery Tap Total (Cell 1+2+3, ~11.1V - 12.6V)

#define PIN_TEMP_ONEWIRE  4    // DS18B20 OneWire Data bus
#define PIN_VIB_ANALOG    39   // 801S Vibration Sensor AO (SENSOR_VN, ADC1)

#define PIN_ENC_CLK       18   // KY-040 Rotary Encoder CLK
#define PIN_ENC_DT        19   // KY-040 Rotary Encoder DT
#define PIN_ENC_SW        23   // KY-040 Rotary Encoder Push Button

// ------------------------------------------------------------------------------
// HARDWARE CALIBRATION & CONSTANTS
// ------------------------------------------------------------------------------
// Battery Voltage Dividers (R_upper = 30kΩ, R_lower = 4.7kΩ)
// Nominal ratio = (30.0 + 4.7) / 4.7 = 7.38298
// Trim factors allow fine calibration against a multimeter
const float V_REF                = 3.30;       // ESP32 ADC full-scale reference
const float ADC_MAX_VAL          = 4095.0;     // 12-bit ADC
const float R_DIVIDER_RATIO      = (30.0 + 4.7) / 4.7; // ~7.383

// Individual divider calibration multipliers (adjust with multimeter)
float cal_b1_mult                = 1.000;
float cal_b2_mult                = 1.000;
float cal_bpack_mult             = 1.000;

// ACS712 Current Sensor Config
// Standard modules: 5A (0.185 V/A), 20A (0.100 V/A), 30A (0.066 V/A)
// Output divider ratio: if using 10k/20k to step 5V down to 3.3V, scale = 3.3 / 5.0 = 0.66
const float ACS_SENSITIVITY      = 0.100;      // Volts per Ampere (20A module default)
const float ACS_DIVIDER_FACTOR   = 0.456;      // Measured output divider ratio (1.139V / 2.500V)
float zero_curr_motor_volt       = 1.139;      // Zero-current quiescent voltage (auto-calibrated on boot)
float zero_curr_total_volt       = 1.137;      // Zero-current quiescent voltage (auto-calibrated on boot)

// LEDC PWM Configuration for Motor Driver
const int   PWM_CHANNEL          = 0;
const int   PWM_FREQ_HZ          = 5000;       // 5 kHz quiet motor drive
const int   PWM_RESOLUTION_BITS  = 8;          // 0 - 255
int         motor_pwm_target     = 0;          // Start safely at 0 on boot
bool        motor_running        = false;      // Requires knob turn or 'START' command
bool        motor_dir_forward    = true;

// Safety Limit Thresholds (Emergency Trip)
const float MAX_MOTOR_CURRENT_A  = 4.50;       // Stall trip threshold
const float MAX_MOTOR_TEMP_C     = 75.0;       // Thermal trip threshold
const float MAX_VIBRATION_G      = 2.80;       // Severe imbalance / bearing seizure
bool        safety_tripped       = false;
String      safety_trip_reason   = "NONE";

// ------------------------------------------------------------------------------
// SENSOR INSTANCES
// ------------------------------------------------------------------------------
OneWire oneWire(PIN_TEMP_ONEWIRE);
DallasTemperature ds18b20(&oneWire);

// Encoder State Variables
volatile int  encoder_position   = 0;         // Starts safely at 0
volatile bool encoder_btn_pressed = false;
volatile unsigned long last_enc_pulse_time = 0;
volatile unsigned long enc_pulse_interval  = 0;
int  last_clk_state = HIGH;

// Timing intervals
unsigned long last_telemetry_tx = 0;
const unsigned long TELEMETRY_INTERVAL_MS = 200; // 5 Hz telemetry stream

// ------------------------------------------------------------------------------
// INTERRUPT SERVICE ROUTINES (KY-040 ENCODER)
// ------------------------------------------------------------------------------
void IRAM_ATTR isr_encoder_clk() {
  int clk = digitalRead(PIN_ENC_CLK);
  int dt  = digitalRead(PIN_ENC_DT);
  if (clk != dt) {
    if (encoder_position < 255) encoder_position += 5;
  } else {
    if (encoder_position > 0) encoder_position -= 5;
  }
  
  // Track pulse frequency for RPM / tachometer estimation
  unsigned long now = micros();
  if (now > last_enc_pulse_time) {
    enc_pulse_interval = now - last_enc_pulse_time;
  }
  last_enc_pulse_time = now;
}

void IRAM_ATTR isr_encoder_btn() {
  static unsigned long last_btn_press = 0;
  if (millis() - last_btn_press > 250) { // Software debounce
    encoder_btn_pressed = true;
    last_btn_press = millis();
  }
}

// ------------------------------------------------------------------------------
// HELPER: OVERSAMPLED ADC READING
// ------------------------------------------------------------------------------
float read_adc_voltage(int pin, int samples = 32) {
  uint32_t sum = 0;
  for (int i = 0; i < samples; i++) {
    sum += analogRead(pin);
    delayMicroseconds(50);
  }
  float avg_raw = (float)sum / (float)samples;
  return (avg_raw / ADC_MAX_VAL) * V_REF;
}

// ------------------------------------------------------------------------------
// HARDWARE AUTO-CALIBRATION
// ------------------------------------------------------------------------------
void calibrate_current_sensors() {
  Serial.println("[CALIB] Establishing 0A baseline for ACS712 sensors (motor de-energized)...");
  digitalWrite(PIN_MOTOR_IN1, LOW);
  digitalWrite(PIN_MOTOR_IN2, LOW);
  ledcWrite(PWM_CHANNEL, 0);
  delay(500);

  float sum_m = 0, sum_t = 0;
  const int CAL_SAMPLES = 100;
  for (int i = 0; i < CAL_SAMPLES; i++) {
    sum_m += read_adc_voltage(PIN_CURR_MOTOR, 16);
    sum_t += read_adc_voltage(PIN_CURR_TOTAL, 16);
    delay(10);
  }
  zero_curr_motor_volt = sum_m / CAL_SAMPLES;
  zero_curr_total_volt = sum_t / CAL_SAMPLES;

  Serial.printf("[CALIB] Zero-point Motor Current: %.3f V | Total Current: %.3f V\n",
                zero_curr_motor_volt, zero_curr_total_volt);
}

// ------------------------------------------------------------------------------
// MOTOR DRIVER CONTROL FUNCTIONS
// ------------------------------------------------------------------------------
void apply_motor_speed(int pwm, bool forward) {
  if (safety_tripped) {
    ledcWrite(PWM_CHANNEL, 0);
    digitalWrite(PIN_MOTOR_IN1, LOW);
    digitalWrite(PIN_MOTOR_IN2, LOW);
    return;
  }

  pwm = constrain(pwm, 0, 255);
  ledcWrite(PWM_CHANNEL, pwm);

  if (pwm == 0) {
    digitalWrite(PIN_MOTOR_IN1, LOW);
    digitalWrite(PIN_MOTOR_IN2, LOW);
  } else if (forward) {
    digitalWrite(PIN_MOTOR_IN1, HIGH);
    digitalWrite(PIN_MOTOR_IN2, LOW);
  } else {
    digitalWrite(PIN_MOTOR_IN1, LOW);
    digitalWrite(PIN_MOTOR_IN2, HIGH);
  }
}

// ------------------------------------------------------------------------------
// SENSOR READING FUNCTIONS
// ------------------------------------------------------------------------------
void read_battery_taps(float &v_b1, float &v_b2, float &v_pack,
                       float &cell1, float &cell2, float &cell3, float &cell_delta) {
  float v_adc1 = read_adc_voltage(PIN_BATT_B1, 32);
  float v_adc2 = read_adc_voltage(PIN_BATT_B2, 32);
  float v_adcp = read_adc_voltage(PIN_BATT_B_PACK, 32);

  v_b1   = v_adc1 * R_DIVIDER_RATIO * cal_b1_mult;
  v_b2   = v_adc2 * R_DIVIDER_RATIO * cal_b2_mult;
  v_pack = v_adcp * R_DIVIDER_RATIO * cal_bpack_mult;

  // Individual 3S series cell extraction
  cell1 = max(0.0f, v_b1);
  cell2 = max(0.0f, v_b2 - v_b1);
  cell3 = max(0.0f, v_pack - v_b2);

  float max_c = max(cell1, max(cell2, cell3));
  float min_c = min(cell1, min(cell2, cell3));
  cell_delta = max(0.0f, max_c - min_c);
}

void read_currents(float &i_motor, float &i_total) {
  float vm = read_adc_voltage(PIN_CURR_MOTOR, 40);
  float vt = read_adc_voltage(PIN_CURR_TOTAL, 40);

  // ΔV relative to calibrated quiescent 0A point
  float delta_vm = vm - zero_curr_motor_volt;
  float delta_vt = vt - zero_curr_total_volt;

  // Actual Current = ΔV_adc / (sensitivity * divider_ratio)
  float effective_sens = ACS_SENSITIVITY * ACS_DIVIDER_FACTOR;
  i_motor = abs(delta_vm / effective_sens);
  i_total = abs(delta_vt / effective_sens);

  // Noise floor suppression (< 80 mA treated as zero)
  if (i_motor < 0.08) i_motor = 0.0;
  if (i_total < 0.08) i_total = 0.0;
}

float read_vibration_g() {
  // Sample 801S waveform over a 30ms window to find peak-to-peak amplitude
  uint32_t start = millis();
  int min_val = 4095;
  int max_val = 0;
  int samples = 0;

  while (millis() - start < 30) {
    int val = analogRead(PIN_VIB_ANALOG);
    if (val < min_val) min_val = val;
    if (val > max_val) max_val = val;
    samples++;
    delayMicroseconds(200);
  }

  int pk_pk = max_val - min_val;
  // Convert peak-to-peak ADC delta into approximate g-force
  // (Empirically: baseline resting noise ~ 100-300 counts = 0.25 - 0.35g)
  float g_val = 0.20 + ((float)pk_pk / 4095.0) * 3.50;
  return constrain(g_val, 0.10, 4.00);
}

float read_temperature_c() {
  ds18b20.requestTemperatures();
  float temp = ds18b20.getTempCByIndex(0);
  if (temp == DEVICE_DISCONNECTED_C || temp < -50.0 || temp > 125.0) {
    return 38.0; // Fallback to safe baseline on sensor bus fault
  }
  return temp;
}

int calculate_rpm() {
  if (enc_pulse_interval == 0 || (micros() - last_enc_pulse_time > 200000)) {
    return 0; // Shaft at standstill
  }
  // For 20 pulses per revolution encoder:
  // RPM = (1,000,000 / pulse_interval_us) * (60 / 20)
  float freq = 1000000.0 / (float)enc_pulse_interval;
  int rpm = (int)(freq * 3.0);
  return constrain(rpm, 0, 9500);
}

// ------------------------------------------------------------------------------
// SAFETY INTERLOCK MONITOR
// ------------------------------------------------------------------------------
void check_safety_limits(float i_motor, float temp_c, float vib_g) {
  if (safety_tripped) return;

  if (i_motor > MAX_MOTOR_CURRENT_A) {
    safety_tripped = true;
    safety_trip_reason = "OVERCURRENT_TRIP";
  } else if (temp_c > MAX_MOTOR_TEMP_C) {
    safety_tripped = true;
    safety_trip_reason = "OVERTEMP_TRIP";
  } else if (vib_g > MAX_VIBRATION_G) {
    safety_tripped = true;
    safety_trip_reason = "VIBRATION_LIMIT_BREACH";
  }

  if (safety_tripped) {
    apply_motor_speed(0, true);
    Serial.printf("[ALERT] EMERGENCY TRIP TRIGGERED: %s\n", safety_trip_reason.c_str());
  }
}

// ------------------------------------------------------------------------------
// ARDUINO SETUP
// ------------------------------------------------------------------------------
void setup() {
  Serial.begin(115200);
  delay(1000);
  Serial.println("\n========================================================");
  Serial.println(" RS-380 Motor Prognostics & SCADA Node (ESP32)");
  Serial.println("========================================================");

  // Configure ADC attenuation (11dB = ~0 - 3.1V measuring range)
  analogSetAttenuation(ADC_11db);

  // Configure Motor Pins
  pinMode(PIN_MOTOR_IN1, OUTPUT);
  pinMode(PIN_MOTOR_IN2, OUTPUT);
  digitalWrite(PIN_MOTOR_IN1, LOW);
  digitalWrite(PIN_MOTOR_IN2, LOW);

  // Configure LEDC PWM (ESP32 v2.x / v3.x compatible)
  #if ESP_ARDUINO_VERSION_MAJOR >= 3
    ledcAttach(PIN_MOTOR_PWM, PWM_FREQ_HZ, PWM_RESOLUTION_BITS);
  #else
    ledcSetup(PWM_CHANNEL, PWM_FREQ_HZ, PWM_RESOLUTION_BITS);
    ledcAttachPin(PIN_MOTOR_PWM, PWM_CHANNEL);
  #endif

  // Configure Sensor Inputs
  pinMode(PIN_CURR_TOTAL, INPUT);
  pinMode(PIN_CURR_MOTOR, INPUT);
  pinMode(PIN_BATT_B1, INPUT);
  pinMode(PIN_BATT_B2, INPUT);
  pinMode(PIN_BATT_B_PACK, INPUT);
  pinMode(PIN_VIB_ANALOG, INPUT);

  // Configure Rotary Encoder
  pinMode(PIN_ENC_CLK, INPUT_PULLUP);
  pinMode(PIN_ENC_DT, INPUT_PULLUP);
  pinMode(PIN_ENC_SW, INPUT_PULLUP);
  attachInterrupt(digitalPinToInterrupt(PIN_ENC_CLK), isr_encoder_clk, CHANGE);
  attachInterrupt(digitalPinToInterrupt(PIN_ENC_SW), isr_encoder_btn, FALLING);

  // Initialize Temperature Sensor
  ds18b20.begin();
  ds18b20.setResolution(10); // 10-bit resolution = ~187ms conversion time

  // Calibrate current sensors with motor offline
  calibrate_current_sensors();

  // Start Motor in standby
  apply_motor_speed(0, motor_dir_forward);
  Serial.println("[SETUP] SCADA Node ready. Motor in standby (turn knob to run).");
}

// ------------------------------------------------------------------------------
// ARDUINO MAIN LOOP
// ------------------------------------------------------------------------------
void loop() {
  // Handle Knob Switch Toggle (Start / Pause or Reset Trip)
  if (encoder_btn_pressed) {
    encoder_btn_pressed = false;
    if (safety_tripped) {
      // Clear safety trip on manual knob button click
      safety_tripped = false;
      safety_trip_reason = "NONE";
      motor_running = true;
      Serial.println("[RESET] Safety trip acknowledged and cleared.");
    } else {
      motor_running = !motor_running;
      Serial.printf("[MANUAL] Motor State toggled: %s\n", motor_running ? "RUNNING" : "STOPPED");
    }
    apply_motor_speed(motor_running ? encoder_position : 0, motor_dir_forward);
  }

  // Update PWM from rotary encoder knob position
  if (motor_running && !safety_tripped) {
    motor_pwm_target = encoder_position;
    apply_motor_speed(motor_pwm_target, motor_dir_forward);
  }

  // Periodic Telemetry Acquisition & Transmission
  if (millis() - last_telemetry_tx >= TELEMETRY_INTERVAL_MS) {
    last_telemetry_tx = millis();

    // 1. Read all sensor channels
    float v_b1, v_b2, v_pack, cell1, cell2, cell3, cell_delta;
    read_battery_taps(v_b1, v_b2, v_pack, cell1, cell2, cell3, cell_delta);

    float i_motor, i_total;
    read_currents(i_motor, i_total);

    float vib_g = read_vibration_g();
    float temp_c = read_temperature_c();
    int rpm = calculate_rpm();

    // Motor voltage across terminal (supply scaled by duty cycle)
    float motor_voltage = v_pack * ((float)motor_pwm_target / 255.0f);

    // 2. Safety Interlock Check
    check_safety_limits(i_motor, temp_c, vib_g);

    // 3. Emit Clean JSON Telemetry to Serial
    // Schema matches the SCADA Dashboard & ML RUL Predictor
    Serial.printf("{\"device_id\":\"RS380-MOT-01\",\"battery_voltage\":%.2f,\"motor_voltage\":%.2f,"
                  "\"total_current\":%.2f,\"motor_current\":%.2f,\"temperature\":%.2f,\"vibration\":%.2f,"
                  "\"rpm\":%d,\"pwm\":%d,\"direction\":\"%s\",\"cell1\":%.2f,\"cell2\":%.2f,\"cell3\":%.2f,"
                  "\"cell_delta\":%.2f,\"alert\":\"%s\"}\n",
                  v_pack, motor_voltage, i_total, i_motor, temp_c, vib_g,
                  rpm, motor_running ? motor_pwm_target : 0,
                  motor_dir_forward ? "FWD" : "REV",
                  cell1, cell2, cell3, cell_delta,
                  safety_trip_reason.c_str());
  }

  // Handle incoming Serial commands from Python SCADA (e.g., speed set, stop)
  if (Serial.available() > 0) {
    String cmd = Serial.readStringUntil('\n');
    cmd.trim();
    if (cmd.startsWith("SPEED=")) {
      int val = cmd.substring(6).toInt();
      encoder_position = constrain(val, 0, 255);
      apply_motor_speed(encoder_position, motor_dir_forward);
    } else if (cmd == "STOP") {
      motor_running = false;
      apply_motor_speed(0, motor_dir_forward);
    } else if (cmd == "START") {
      motor_running = true;
      safety_tripped = false;
      apply_motor_speed(encoder_position, motor_dir_forward);
    } else if (cmd == "REVERSE") {
      motor_dir_forward = !motor_dir_forward;
      apply_motor_speed(encoder_position, motor_dir_forward);
    }
  }
}
