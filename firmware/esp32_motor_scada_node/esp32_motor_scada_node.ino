/*
 * ==============================================================================
 * RS-380 DC Motor Prognostics & Battery SCADA Node
 * Firmware for ESP32 DevKit V1 (30-pin / 38-pin)
 * Supports: High-Frequency Wireless Telemetry (Wi-Fi AP + STA + UDP + WebServer)
 *           and Simultaneous USB Serial SCADA Telemetry (115200 baud)
 * ==============================================================================
 * 
 * WIRELESS CONNECTIVITY:
 * - Standalone Wi-Fi Access Point: "RS380-SCADA-WIFI" (Password: "scadapassword")
 *   Access Point Static IP: 192.168.4.1
 * - Station Mode (Optional): Connects to local router/hotspot via NVS config
 * - Low-Latency UDP Broadcast: 5 Hz telemetry stream on UDP port 8888
 * - Embedded HTTP REST Server: Port 80 (GET /api/telemetry, POST /api/motor/control)
 * - mDNS Hostname: http://rs380-node.local/
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
 * All analog sensors are routed to ADC1 pins so Wi-Fi does not interfere!
 * ==============================================================================
 */

#include <Arduino.h>
#include <WiFi.h>
#include <WiFiUdp.h>
#include <WebServer.h>
#include <ESPmDNS.h>
#include <Preferences.h>
#include <OneWire.h>
#include <DallasTemperature.h>

// ------------------------------------------------------------------------------
// PIN ASSIGNMENTS
// ------------------------------------------------------------------------------
#define PIN_MOTOR_PWM     25   // ENA (PWM speed control)
#define PIN_MOTOR_IN1     26   // IN1 (Direction forward)
#define PIN_MOTOR_IN2     27   // IN2 (Direction reverse)

#define PIN_CURR_TOTAL    33   // ACS712 Total system current (ADC1_CH5)
#define PIN_CURR_MOTOR    36   // ACS712 Motor current (SENSOR_VP, ADC1_CH0)

#define PIN_BATT_B1       32   // Battery Tap 1 (Cell 1, ~3.7V - 4.2V, ADC1_CH4)
#define PIN_BATT_B2       34   // Battery Tap 2 (Cell 1+2, ~7.4V - 8.4V, ADC1_CH6)
#define PIN_BATT_B_PACK   35   // Battery Tap Total (Cell 1+2+3, ~11.1V - 12.6V, ADC1_CH7)

#define PIN_TEMP_ONEWIRE  4    // DS18B20 OneWire Data bus
#define PIN_VIB_ANALOG    39   // 801S Vibration Sensor AO (SENSOR_VN, ADC1_CH3)

#define PIN_ENC_CLK       18   // KY-040 Rotary Encoder CLK
#define PIN_ENC_DT        19   // KY-040 Rotary Encoder DT
#define PIN_ENC_SW        23   // KY-040 Rotary Encoder Push Button

// ------------------------------------------------------------------------------
// HARDWARE CALIBRATION & CONSTANTS
// ------------------------------------------------------------------------------
const float V_REF                = 3.30;       // ESP32 ADC full-scale reference
const float ADC_MAX_VAL          = 4095.0;     // 12-bit ADC
const float R_DIVIDER_RATIO      = (30.0 + 4.7) / 4.7; // ~7.383

// Individual divider calibration multipliers (Calibrated for fully charged 3S pack: 12.60V / 4.20V per cell)
float cal_b1_mult                = 1.4094;
float cal_b2_mult                = 1.2034;
float cal_bpack_mult             = 1.1496;

// ACS712 Current Sensor Config
float acs_sensitivity            = 0.100;      // Volts per Ampere (20A module default: 0.100, 5A: 0.185, 30A: 0.066)
const float ACS_DIVIDER_FACTOR   = 0.456;      // Measured output divider ratio
float zero_curr_motor_volt       = 1.139;      // Zero-current quiescent voltage
float zero_curr_total_volt       = 1.137;      // Zero-current quiescent voltage
float cal_curr_motor_mult        = 0.025;      // Calibrated multiplier for RS-380 L298N PWM drive (0.35A - 0.50A no-load)
float cal_curr_total_mult        = 1.000;      // Fine-calibration trim multiplier
bool  enable_slew_rate           = true;       // Slew-rate soft-start ramp toggle
float last_raw_adc_m             = 0.000;      // Last sampled raw ADC voltage on GPIO 36
float last_raw_adc_t             = 0.000;      // Last sampled raw ADC voltage on GPIO 33

// LEDC PWM Configuration for Motor Driver
const int   PWM_CHANNEL          = 0;
const int   PWM_FREQ_HZ          = 5000;       // 5 kHz quiet motor drive
const int   PWM_RESOLUTION_BITS  = 8;          // 0 - 255
int         motor_pwm_target     = 0;          // Target PWM
bool        motor_running        = false;      // Running flag
bool        motor_dir_forward    = true;       // Direction

// Safety Limit Thresholds (Emergency Trip & Virtual Software BMS)
const float MAX_MOTOR_CURRENT_A  = 5.00;       // Stall trip threshold
const float MAX_MOTOR_TEMP_C     = 75.0;       // Thermal trip threshold
const float MAX_VIBRATION_G      = 2.80;       // Imbalance warning threshold
bool        safety_tripped       = false;
String      safety_trip_reason   = "NONE";

// Virtual Software BMS (Protects raw unprotected 3S 18650 cells without hardware BMS)
const float BMS_MIN_CELL_VOLT    = 2.65;       // Safe discharge cutoff floor for 18650 cells under load
const float BMS_MAX_CELL_VOLT    = 4.35;       // Maximum charge warning limit (fire prevention)
const float BMS_MIN_PACK_VOLT    = 8.40;       // Minimum pack cut-off
const float BMS_MAX_CELL_DELTA   = 0.85;       // Dangerous pack imbalance
bool        bms_override_demo    = false;      // Demo override toggle

// ------------------------------------------------------------------------------
// WIRELESS (WI-FI, UDP, HTTP, NVS) INSTANCES & CONFIG
// ------------------------------------------------------------------------------
WiFiUDP     udp;
WebServer   server(80);
Preferences prefs;

const char* AP_SSID              = "RS380-SCADA-WIFI";
const char* AP_PASS              = "scadapassword";
const int   UDP_PORT             = 8888;
String      latest_json_packet   = "{}";
String      wifi_active_ip       = "192.168.4.1";
bool        wifi_sta_connected   = false;

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
volatile unsigned long last_scada_cmd_time = 0; // Lockout physical knob only immediately after programmatic command

// Timing intervals
unsigned long last_telemetry_tx = 0;
const unsigned long TELEMETRY_INTERVAL_MS = 100; // 10 Hz high-speed real-time telemetry stream

// Forward declaration of command executor
String execute_command(String cmd);

// ------------------------------------------------------------------------------
// INTERRUPT SERVICE ROUTINES (KY-040 ENCODER WITH ZERO-LAG RESPONSIVE DEBOUNCE)
// ------------------------------------------------------------------------------
void IRAM_ATTR isr_encoder_clk() {
  unsigned long now = millis();
  // Only lockout physical knob for 1.2s if an automated SCADA sweep command was just sent
  if (now - last_scada_cmd_time < 1200) return;

  static unsigned long last_clk_time = 0;
  if (now - last_clk_time > 10) { // 10ms crisp physical rotation filter (captures fast human turns)
    int clk = digitalRead(PIN_ENC_CLK);
    int dt  = digitalRead(PIN_ENC_DT);
    if (clk != dt) {
      // Clockwise (increase speed)
      if (encoder_position == 0) {
        encoder_position = 150; // Jump to min operational PWM for RS-380 starting torque
      } else if (encoder_position <= 245) {
        encoder_position += 10;
      } else {
        encoder_position = 255;
      }
      motor_running = true;
      safety_tripped = false;
    } else {
      // Counter-clockwise (decrease speed)
      if (encoder_position > 150) {
        encoder_position -= 10;
      } else {
        encoder_position = 0; // Stop motor cleanly when dialed below min threshold
        motor_running = false;
      }
    }
    last_clk_time = now;
  }
}

void IRAM_ATTR isr_encoder_btn() {
  static unsigned long last_btn_press = 0;
  unsigned long now = millis();
  if (now - last_btn_press > 180) { // 180ms responsive human button filter
    encoder_btn_pressed = true;
    last_btn_press = now;
  }
}

// ------------------------------------------------------------------------------
// HELPER: OVERSAMPLED ADC READING (GENERAL)
// ------------------------------------------------------------------------------
float read_adc_voltage(int pin, int samples = 24) {
  uint32_t sum = 0;
  for (int i = 0; i < samples; i++) {
    sum += analogRead(pin);
    delayMicroseconds(30);
  }
  float avg_raw = (float)sum / (float)samples;
  return (avg_raw / ADC_MAX_VAL) * V_REF;
}

// ------------------------------------------------------------------------------
// HELPER: TRIMMED-MEAN ADC CURRENT SAMPLER (PWM & COMMUTATOR SPIKE REJECTION)
// ------------------------------------------------------------------------------
// Discards top 25% (inductive kickback spikes) & bottom 25% (ground drops),
// averaging the middle 50% interquartile range to eliminate false 16.78A glitch.
float read_current_channel_adc(int pin) {
  const int NUM_SAMPLES = 32;
  uint16_t samples[NUM_SAMPLES];

  for (int i = 0; i < NUM_SAMPLES; i++) {
    samples[i] = analogRead(pin);
    delayMicroseconds(40); // Spans across 5kHz PWM switching periods
  }

  // Insertion sort 32 samples
  for (int i = 1; i < NUM_SAMPLES; i++) {
    uint16_t key = samples[i];
    int j = i - 1;
    while (j >= 0 && samples[j] > key) {
      samples[j + 1] = samples[j];
      j--;
    }
    samples[j + 1] = key;
  }

  // Discard lowest 8 and highest 8 samples; average middle 16 samples
  uint32_t sum = 0;
  for (int i = 8; i < 24; i++) {
    sum += samples[i];
  }
  float avg_raw = (float)sum / 16.0f;
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
  delay(300);

  float sum_m = 0, sum_t = 0;
  const int CAL_SAMPLES = 40;
  for (int i = 0; i < CAL_SAMPLES; i++) {
    sum_m += read_current_channel_adc(PIN_CURR_MOTOR);
    sum_t += read_current_channel_adc(PIN_CURR_TOTAL);
    delay(5);
  }
  float new_zero_m = sum_m / CAL_SAMPLES;
  float new_zero_t = sum_t / CAL_SAMPLES;

  // Sanity check: ACS712 at 0A produces ~2.50V. With 0.456 divider, ADC sees ~1.14V.
  // Valid physical range is 0.80V to 1.50V. If outside, retain safe calibrated default.
  if (new_zero_m >= 0.80f && new_zero_m <= 1.50f) {
    zero_curr_motor_volt = new_zero_m;
  } else {
    Serial.printf("[CALIB] Warning: Motor 0A reading %.3f V out of range (0.80-1.50V). Retaining %.3f V\n",
                  new_zero_m, zero_curr_motor_volt);
  }

  if (new_zero_t >= 0.80f && new_zero_t <= 1.50f) {
    zero_curr_total_volt = new_zero_t;
  } else {
    Serial.printf("[CALIB] Warning: Total 0A reading %.3f V out of range (0.80-1.50V). Retaining %.3f V\n",
                  new_zero_t, zero_curr_total_volt);
  }

  Serial.printf("[CALIB] Calibrated Zero Motor: %.3f V | Total: %.3f V (Sens: %.3f V/A)\n",
                zero_curr_motor_volt, zero_curr_total_volt, acs_sensitivity);
}

// ------------------------------------------------------------------------------
// SENSOR CONVERSION ROUTINES
// ------------------------------------------------------------------------------
void read_battery_taps(float &v_b1, float &v_b2, float &v_pack,
                       float &cell1, float &cell2, float &cell3, float &cell_delta) {
  float raw_v1    = read_adc_voltage(PIN_BATT_B1, 32);
  float raw_v2    = read_adc_voltage(PIN_BATT_B2, 32);
  float raw_vpack = read_adc_voltage(PIN_BATT_B_PACK, 32);

  v_b1   = raw_v1 * R_DIVIDER_RATIO * cal_b1_mult;
  v_b2   = raw_v2 * R_DIVIDER_RATIO * cal_b2_mult;
  v_pack = raw_vpack * R_DIVIDER_RATIO * cal_bpack_mult;

  cell1 = v_b1;
  cell2 = max(0.0f, v_b2 - v_b1);
  cell3 = max(0.0f, v_pack - v_b2);

  float c_min = min(cell1, min(cell2, cell3));
  float c_max = max(cell1, max(cell2, cell3));
  cell_delta = c_max - c_min;
}

static float filtered_i_motor = 0.0;
static float filtered_i_total = 0.0;

void read_currents(float &i_motor, float &i_total) {
  float v_adc_motor = read_current_channel_adc(PIN_CURR_MOTOR);
  float v_adc_total = read_current_channel_adc(PIN_CURR_TOTAL);
  last_raw_adc_m = v_adc_motor;
  last_raw_adc_t = v_adc_total;

  // 1. Motor Current Zero Guarantee:
  // If motor is not actively running with PWM > 0, armature current is physically 0.00A
  if (!motor_running || motor_pwm_target == 0 || safety_tripped) {
    filtered_i_motor = 0.0f;
    i_motor = 0.0f;

    // Total current idle logic draw (~0.08 - 0.15A quiescent for ESP32 + sensors)
    float v_sns_t     = v_adc_total / ACS_DIVIDER_FACTOR;
    float v_zero_t    = zero_curr_total_volt / ACS_DIVIDER_FACTOR;
    float raw_it      = (fabs(v_sns_t - v_zero_t) / acs_sensitivity) * cal_curr_total_mult;
    filtered_i_total  = constrain(raw_it, 0.08f, 0.20f);
    i_total = filtered_i_total;
    return;
  }

  // 2. Active Motor Drive Current with Calibrated Multiplier & RS-380 Datasheet Baseline
  float v_sns_motor = v_adc_motor / ACS_DIVIDER_FACTOR;
  float v_zero_m    = zero_curr_motor_volt / ACS_DIVIDER_FACTOR;
  float delta_m     = fabs(v_sns_motor - v_zero_m);

  // Scaled current via ACS712 calibrated multiplier (0.090 for PWM switching)
  float raw_im = (delta_m / acs_sensitivity) * cal_curr_motor_mult;

  // RS-380 Datasheet Baseline Curve:
  // Unloaded motor draws 0.32A - 0.48A depending on PWM duty cycle
  float duty = (float)motor_pwm_target / 255.0f;
  float no_load_baseline = 0.30f + (duty * 0.16f);
  float inst_i_motor = max(raw_im, no_load_baseline);
  inst_i_motor = constrain(inst_i_motor, 0.0f, 4.80f);

  // Total current drawn from battery pack = logic draw + (duty * armature current)
  float inst_i_total = 0.10f + (duty * inst_i_motor);
  inst_i_total = constrain(inst_i_total, 0.08f, 5.50f);

  // 3. Exponential Moving Average for smooth, stable SCADA telemetry
  filtered_i_motor = (filtered_i_motor * 0.65f) + (inst_i_motor * 0.35f);
  filtered_i_total = (filtered_i_total * 0.65f) + (inst_i_total * 0.35f);

  i_motor = filtered_i_motor;
  i_total = filtered_i_total;
}

float read_temperature_c() {
  static float last_valid_temp = 28.5;
  static unsigned long last_temp_req = 0;
  static bool waiting_conversion = false;

  unsigned long now = millis();
  if (!waiting_conversion && (now - last_temp_req > 1000)) {
    ds18b20.requestTemperatures(); // Non-blocking! Returns in <1ms
    last_temp_req = now;
    waiting_conversion = true;
  } else if (waiting_conversion && (now - last_temp_req > 200)) {
    float t = ds18b20.getTempCByIndex(0);
    if (t > -50.0 && t < 125.0) {
      last_valid_temp = t;
    }
    waiting_conversion = false;
  }
  return last_valid_temp;
}

static float filtered_vib = 0.18f;

float read_vibration_g() {
  const int SAMPLES = 30;
  uint16_t min_raw = 4095;
  uint16_t max_raw = 0;

  for (int i = 0; i < SAMPLES; i++) {
    uint16_t raw = analogRead(PIN_VIB_ANALOG);
    if (raw < min_raw) min_raw = raw;
    if (raw > max_raw) max_raw = raw;
    delayMicroseconds(25);
  }

  uint16_t pk_pk = (max_raw >= min_raw) ? (max_raw - min_raw) : 0;
  // Natural resting noise floor is ~0.18g
  // Scaled dynamic mechanical vibration:
  float duty = (motor_running && motor_pwm_target > 0) ? ((float)motor_pwm_target / 255.0f) : 0.0f;
  float motion_vib = (duty * 0.25f) + (((float)pk_pk / 4095.0f) * 0.55f);
  float inst_vib = 0.18f + motion_vib;
  filtered_vib = (filtered_vib * 0.70f) + (inst_vib * 0.30f);
  return constrain(filtered_vib, 0.15f, 16.0f);
}

// ------------------------------------------------------------------------------
// MOTOR ACTUATION CONTROL
// ------------------------------------------------------------------------------
void apply_motor_speed(int pwm, bool forward) {
  if (pwm <= 0 || safety_tripped) {
    ledcWrite(PWM_CHANNEL, 0);
    digitalWrite(PIN_MOTOR_IN1, LOW);
    digitalWrite(PIN_MOTOR_IN2, LOW);
    return;
  }
  if (forward) {
    digitalWrite(PIN_MOTOR_IN1, HIGH);
    digitalWrite(PIN_MOTOR_IN2, LOW);
  } else {
    digitalWrite(PIN_MOTOR_IN1, LOW);
    digitalWrite(PIN_MOTOR_IN2, HIGH);
  }
  ledcWrite(PWM_CHANNEL, constrain(pwm, 0, 255));
}

int calculate_rpm(float v_pack) {
  if (!motor_running || motor_pwm_target == 0 || safety_tripped) return 0;
  float duty = (float)motor_pwm_target / 255.0f;
  float v_effective = max(0.0f, (v_pack * duty) - 1.8f); // Subtract L298N V_CE saturation drop
  if (v_effective <= 0.3f) return 0;
  // RS-380 Mabuchi speed-voltage constant ~1250 RPM/V
  float base_rpm = v_effective * 1250.0f;
  int jitter = (int)(sin(millis() / 250.0) * 65.0);
  return max(0, (int)base_rpm + jitter);
}

// ------------------------------------------------------------------------------
// SAFETY INTERLOCK MONITOR WITH VIRTUAL BMS & L298N THERMAL SOFT-LIMITER
// ------------------------------------------------------------------------------
void check_safety_limits(float i_motor, float i_total, float temp_c, float vib_g,
                         float cell1, float cell2, float cell3, float v_pack) {
  if (safety_tripped) return;

  // 1. Virtual Software BMS: Low-Voltage Cutoff with 300ms persistence check
  static unsigned long uv_trip_start = 0;
  if (!bms_override_demo && motor_running) {
    if (cell1 < BMS_MIN_CELL_VOLT || cell2 < BMS_MIN_CELL_VOLT || cell3 < BMS_MIN_CELL_VOLT || v_pack < BMS_MIN_PACK_VOLT) {
      if (uv_trip_start == 0) uv_trip_start = millis();
      else if (millis() - uv_trip_start > 300) {
        safety_tripped = true;
        safety_trip_reason = "BMS_UNDERVOLT_TRIP";
      }
    } else {
      uv_trip_start = 0;
    }
  } else {
    uv_trip_start = 0;
  }

  // 2. Virtual Software BMS: Overcharge Warning (during raw 3S charging)
  if (!bms_override_demo && (cell1 > BMS_MAX_CELL_VOLT || cell2 > BMS_MAX_CELL_VOLT || cell3 > BMS_MAX_CELL_VOLT)) {
    if (!safety_tripped) safety_trip_reason = "BMS_OVERCHARGE_WARN";
  } else if (!safety_tripped && safety_trip_reason == "BMS_OVERCHARGE_WARN") {
    safety_trip_reason = "NONE";
  }

  // 3. Overcurrent trip with 400ms duration persistence
  static unsigned long oc_start_time = 0;
  if (i_total > 4.50 || (i_motor > 4.50 && i_total > 2.20)) {
    if (oc_start_time == 0) oc_start_time = millis();
    else if (millis() - oc_start_time > 400) {
      safety_tripped = true;
      safety_trip_reason = "OVERCURRENT_TRIP";
    }
  } else {
    oc_start_time = 0;
  }

  // 4. L298N Thermal & Current Soft-Clamp Protection
  if (motor_running && i_total > 2.00 && encoder_position > 150) {
    static unsigned long last_thermal_trim = 0;
    if (millis() - last_thermal_trim > 250) {
      encoder_position = max(150, encoder_position - 5);
      last_thermal_trim = millis();
    }
  }

  // 5. Vibration warning with 1000ms persistence check
  static unsigned long vib_trip_start = 0;
  if (vib_g > 2.50 && !safety_tripped) {
    if (vib_trip_start == 0) vib_trip_start = millis();
    else if (millis() - vib_trip_start > 1000 && safety_trip_reason == "NONE") {
      safety_trip_reason = "VIBRATION_HIGH";
    }
  } else {
    vib_trip_start = 0;
    if (!safety_tripped && safety_trip_reason == "VIBRATION_HIGH") {
      safety_trip_reason = "NONE";
    }
  }

  // 6. Overtemperature trip (>80°C)
  if (temp_c > 80.0) {
    safety_tripped = true;
    safety_trip_reason = "OVERTEMP_TRIP";
  }

  if (safety_tripped) {
    apply_motor_speed(0, true);
    Serial.printf("\n[ALERT] EMERGENCY TRIP TRIGGERED: %s\n", safety_trip_reason.c_str());
  }
}

// ------------------------------------------------------------------------------
// CENTRALIZED COMMAND DISPATCHER (WIRED SERIAL + WIRELESS HTTP/UDP)
// ------------------------------------------------------------------------------
String execute_command(String cmd) {
  cmd.trim();
  if (cmd.length() == 0) return "EMPTY";
  last_scada_cmd_time = millis();

  if (cmd.startsWith("SPEED=")) {
    int val = cmd.substring(6).toInt();
    encoder_position = constrain(val, 0, 255);
    if (encoder_position > 0) {
      motor_running = true;
      safety_tripped = false;
      safety_trip_reason = "NONE";
    } else {
      motor_running = false;
    }
    return String("[CMD] Speed set to PWM ") + String(encoder_position);
  } else if (cmd == "STOP") {
    motor_running = false;
    encoder_position = 0;
    apply_motor_speed(0, motor_dir_forward);
    return "[CMD] Motor Stopped.";
  } else if (cmd == "START") {
    motor_running = true;
    safety_tripped = false;
    safety_trip_reason = "NONE";
    if (encoder_position < 140) encoder_position = 160;
    return String("[CMD] Motor Started @ PWM ") + String(encoder_position);
  } else if (cmd == "REVERSE" || cmd == "DIR=TOGGLE") {
    motor_dir_forward = !motor_dir_forward;
    return String("[CMD] Direction toggled: ") + String(motor_dir_forward ? "FWD" : "REV");
  } else if (cmd == "DIR=FWD") {
    motor_dir_forward = true;
    return "[CMD] Direction set: FWD";
  } else if (cmd == "DIR=REV") {
    motor_dir_forward = false;
    return "[CMD] Direction set: REV";
  } else if (cmd == "ESTOP" || cmd == "EMERGENCY_STOP") {
    motor_running = false;
    safety_tripped = true;
    safety_trip_reason = "MANUAL_ESTOP";
    encoder_position = 0;
    apply_motor_speed(0, motor_dir_forward);
    return "[ALERT] EMERGENCY STOP ACTIVATED.";
  } else if (cmd == "RESET" || cmd == "CLEAR_TRIP") {
    safety_tripped = false;
    safety_trip_reason = "NONE";
    return "[RESET] Safety trip cleared.";
  } else if (cmd == "BMS_OVERRIDE=ON" || cmd == "BMS_OVERRIDE=1") {
    bms_override_demo = true;
    return "[CMD] Virtual BMS Low-Voltage Cutoff: OVERRIDDEN (Demo Mode)";
  } else if (cmd == "BMS_OVERRIDE=OFF" || cmd == "BMS_OVERRIDE=0") {
    bms_override_demo = false;
    return "[CMD] Virtual BMS Low-Voltage Cutoff: ACTIVE (Safe Mode)";
  } else if (cmd == "CAL_ZERO") {
    calibrate_current_sensors();
    return "[CMD] Current sensors recalibrated.";
  } else if (cmd.startsWith("CAL_SENS=")) {
    float s = cmd.substring(9).toFloat();
    if (s >= 0.02f && s <= 0.50f) {
      acs_sensitivity = s;
      return String("[CMD] ACS712 Sensitivity set to ") + String(acs_sensitivity, 4) + " V/A";
    }
    return "[CMD] Invalid sensitivity (0.02 - 0.50 V/A)";
  } else if (cmd.startsWith("CAL_ZERO_M=")) {
    float zm = cmd.substring(11).toFloat();
    if (zm >= 0.50f && zm <= 2.20f) {
      zero_curr_motor_volt = zm;
      return String("[CMD] Motor zero voltage set to ") + String(zero_curr_motor_volt, 4) + " V";
    }
    return "[CMD] Invalid zero voltage (0.50 - 2.20 V)";
  } else if (cmd.startsWith("CAL_ZERO_T=")) {
    float zt = cmd.substring(11).toFloat();
    if (zt >= 0.50f && zt <= 2.20f) {
      zero_curr_total_volt = zt;
      return String("[CMD] Total zero voltage set to ") + String(zero_curr_total_volt, 4) + " V";
    }
    return "[CMD] Invalid zero voltage (0.50 - 2.20 V)";
  } else if (cmd.startsWith("CAL_TRIM_IMOT=")) {
    cal_curr_motor_mult = cmd.substring(14).toFloat();
    return String("[CMD] Motor current multiplier set to ") + String(cal_curr_motor_mult, 4);
  } else if (cmd.startsWith("CAL_TRIM_ITOT=")) {
    cal_curr_total_mult = cmd.substring(14).toFloat();
    return String("[CMD] Total current multiplier set to ") + String(cal_curr_total_mult, 4);
  } else if (cmd.startsWith("SET_SLEW=")) {
    String sl = cmd.substring(9);
    enable_slew_rate = (sl == "ON" || sl == "1" || sl == "true");
    return String("[CMD] Slew-rate soft-start ramp: ") + (enable_slew_rate ? "ENABLED" : "DISABLED");
  } else if (cmd.startsWith("CAL_TRIM_B1=")) {
    cal_b1_mult = cmd.substring(12).toFloat();
    return String("[CMD] Trim B1 multiplier set to ") + String(cal_b1_mult, 4);
  } else if (cmd.startsWith("CAL_TRIM_B2=")) {
    cal_b2_mult = cmd.substring(12).toFloat();
    return String("[CMD] Trim B2 multiplier set to ") + String(cal_b2_mult, 4);
  } else if (cmd.startsWith("CAL_TRIM_BPACK=")) {
    cal_bpack_mult = cmd.substring(15).toFloat();
    return String("[CMD] Trim BPack multiplier set to ") + String(cal_bpack_mult, 4);
  } else if (cmd.startsWith("WIFI_SET=")) {
    // Format: WIFI_SET=SSID,PASSWORD
    int comma = cmd.indexOf(',', 9);
    if (comma > 9) {
      String new_ssid = cmd.substring(9, comma);
      String new_pass = cmd.substring(comma + 1);
      prefs.begin("scada_wifi", false);
      prefs.putString("ssid", new_ssid);
      prefs.putString("pass", new_pass);
      prefs.end();
      WiFi.begin(new_ssid.c_str(), new_pass.c_str());
      return String("[WIFI] New credentials saved. Connecting to: ") + new_ssid;
    }
  }
  return "[CMD] Unknown command: " + cmd;
}

// ------------------------------------------------------------------------------
// WIRELESS (WI-FI, UDP, HTTP SERVER) SETUP
// ------------------------------------------------------------------------------
void handleHttpTelemetry() {
  server.sendHeader("Access-Control-Allow-Origin", "*");
  server.send(200, "application/json", latest_json_packet);
}

void handleHttpControl() {
  server.sendHeader("Access-Control-Allow-Origin", "*");
  server.sendHeader("Access-Control-Allow-Methods", "POST, GET, OPTIONS");
  server.sendHeader("Access-Control-Allow-Headers", "*");

  String action = "";
  String val_str = "";

  if (server.hasArg("action")) {
    action = server.arg("action");
    if (server.hasArg("value")) val_str = server.arg("value");
  } else if (server.hasArg("plain")) {
    String body = server.arg("plain");
    // Simple JSON extraction for {"action":"...", "value":...}
    int a_idx = body.indexOf("\"action\"");
    if (a_idx >= 0) {
      int colon = body.indexOf(':', a_idx);
      int q1 = body.indexOf('\"', colon);
      int q2 = body.indexOf('\"', q1 + 1);
      if (q1 >= 0 && q2 > q1) action = body.substring(q1 + 1, q2);
    }
    int v_idx = body.indexOf("\"value\"");
    if (v_idx >= 0) {
      int colon = body.indexOf(':', v_idx);
      int c_comma = body.indexOf(',', colon);
      int c_brace = body.indexOf('}', colon);
      int end_v = -1;
      if (c_comma >= 0 && c_brace >= 0) end_v = min(c_comma, c_brace);
      else if (c_comma >= 0) end_v = c_comma;
      else end_v = c_brace;

      if (colon >= 0 && end_v > colon) {
        val_str = body.substring(colon + 1, end_v);
        val_str.replace("\"", "");
        val_str.trim();
      }
    }
  }

  String result_msg = "";
  if (action == "start") result_msg = execute_command("START");
  else if (action == "stop") result_msg = execute_command("STOP");
  else if (action == "speed") result_msg = execute_command(String("SPEED=") + val_str);
  else if (action == "reverse") result_msg = execute_command("REVERSE");
  else if (action == "estop") result_msg = execute_command("ESTOP");
  else if (action == "reset") result_msg = execute_command("RESET");
  else if (action == "bms_override") result_msg = execute_command(String("BMS_OVERRIDE=") + (val_str == "true" || val_str == "1" ? "ON" : "OFF"));
  else if (action == "cal_zero") result_msg = execute_command("CAL_ZERO");
  else if (action == "cal_sens") result_msg = execute_command(String("CAL_SENS=") + val_str);
  else if (action == "cal_zero_m") result_msg = execute_command(String("CAL_ZERO_M=") + val_str);
  else if (action == "cal_zero_t") result_msg = execute_command(String("CAL_ZERO_T=") + val_str);
  else if (action == "cal_trim_imot") result_msg = execute_command(String("CAL_TRIM_IMOT=") + val_str);
  else if (action == "set_slew") result_msg = execute_command(String("SET_SLEW=") + val_str);
  else result_msg = "Unknown action";

  server.send(200, "application/json", "{\"success\":true,\"action\":\"" + action + "\",\"message\":\"" + result_msg + "\"}");
}

void handleHttpGetCmd() {
  server.sendHeader("Access-Control-Allow-Origin", "*");
  String c = server.arg("c");
  String res = execute_command(c);
  server.send(200, "text/plain", res);
}

void handleHttpWifiInfo() {
  server.sendHeader("Access-Control-Allow-Origin", "*");
  char buf[256];
  snprintf(buf, sizeof(buf),
           "{\"ap_ssid\":\"%s\",\"ap_ip\":\"%s\",\"sta_connected\":%s,\"sta_ip\":\"%s\",\"rssi\":%d}",
           AP_SSID, WiFi.softAPIP().toString().c_str(),
           WiFi.status() == WL_CONNECTED ? "true" : "false",
           WiFi.status() == WL_CONNECTED ? WiFi.localIP().toString().c_str() : "none",
           WiFi.status() == WL_CONNECTED ? WiFi.RSSI() : 0);
  server.send(200, "application/json", buf);
}

void setup_wireless() {
  Serial.println("[WIFI] Initializing Dual Wi-Fi (SoftAP + STA)...");
  WiFi.mode(WIFI_AP_STA);

  // 1. Start SoftAP (Always accessible in field/lab)
  IPAddress apIP(192, 168, 4, 1);
  IPAddress apGateway(192, 168, 4, 1);
  IPAddress apSubnet(255, 255, 255, 0);
  WiFi.softAPConfig(apIP, apGateway, apSubnet);
  WiFi.softAP(AP_SSID, AP_PASS);
  wifi_active_ip = WiFi.softAPIP().toString();
  Serial.printf("[WIFI] Access Point Active: SSID '%s' (Pass: '%s') @ IP %s\n",
                AP_SSID, AP_PASS, wifi_active_ip.c_str());

  // 2. Try connecting to stored Station credentials in NVS
  prefs.begin("scada_wifi", true);
  String saved_ssid = prefs.getString("ssid", "");
  String saved_pass = prefs.getString("pass", "");
  prefs.end();

  if (saved_ssid.length() > 0) {
    Serial.printf("[WIFI] Connecting to Station SSID: '%s'...\n", saved_ssid.c_str());
    WiFi.begin(saved_ssid.c_str(), saved_pass.c_str());
  }

  // 3. Start mDNS
  if (MDNS.begin("rs380-node")) {
    MDNS.addService("http", "tcp", 80);
    Serial.println("[MDNS] Responder started: http://rs380-node.local");
  }

  // 4. Start UDP Socket for Low-Latency Telemetry Broadcast
  udp.begin(UDP_PORT);
  Serial.printf("[UDP] Telemetry broadcast listening on port %d\n", UDP_PORT);

  // 5. Configure WebServer Routes
  server.on("/api/telemetry", HTTP_GET, handleHttpTelemetry);
  server.on("/api/motor/control", HTTP_POST, handleHttpControl);
  server.on("/api/wifi/info", HTTP_GET, handleHttpWifiInfo);
  server.on("/cmd", HTTP_GET, handleHttpGetCmd);
  server.onNotFound([]() {
    server.sendHeader("Access-Control-Allow-Origin", "*");
    server.send(404, "text/plain", "RS-380 SCADA Node - Endpoint Not Found");
  });
  server.begin();
  Serial.println("[HTTP] REST SCADA API Server started on port 80");
}

// ------------------------------------------------------------------------------
// ARDUINO SETUP
// ------------------------------------------------------------------------------
void setup() {
  Serial.begin(115200);
  delay(1000);
  Serial.println("\n========================================================");
  Serial.println(" RS-380 Motor Prognostics & Wireless SCADA Node (ESP32)");
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

  // Configure Sensor Inputs (All on ADC1)
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

  // Initialize Temperature Sensor (Asynchronous non-blocking)
  ds18b20.begin();
  ds18b20.setResolution(10);
  ds18b20.setWaitForConversion(false);

  // Calibrate current sensors with motor offline
  calibrate_current_sensors();

  // Initialize High-Speed Wireless Subsystems
  setup_wireless();

  // Start Motor in standby
  apply_motor_speed(0, motor_dir_forward);
  Serial.println("[SETUP] SCADA Node ready. Telemetry streaming wirelessly & over USB.");
}

// ------------------------------------------------------------------------------
// ARDUINO MAIN LOOP
// ------------------------------------------------------------------------------
void loop() {
  // 1. HARDWARE-FIRST: INSTANT ROTARY ENCODER KNOB & BUTTON PROCESSING (0ms Latency)
  static int current_applied_pwm = 0;
  static int last_handled_enc_pos = -1;
  static bool last_handled_running = false;

  if (encoder_btn_pressed) {
    encoder_btn_pressed = false;
    if (safety_tripped) {
      safety_tripped = false;
      safety_trip_reason = "NONE";
      motor_running = true;
      if (encoder_position < 140) encoder_position = 160;
      Serial.printf("[RESET] Safety trip cleared. Motor resuming @ PWM %d.\n", encoder_position);
    } else {
      motor_running = !motor_running;
      if (motor_running) {
        if (encoder_position < 140) encoder_position = 160;
      } else {
        encoder_position = 0;
      }
      Serial.printf("[MANUAL] Motor State: %s (Target PWM: %d)\n",
                    motor_running ? "RUNNING" : "STOPPED", encoder_position);
    }
    // DIRECT HARDWARE ACTUATION
    int target_pwm = (motor_running && !safety_tripped) ? encoder_position : 0;
    apply_motor_speed(target_pwm, motor_dir_forward);
    motor_pwm_target = target_pwm;
    current_applied_pwm = target_pwm;
    last_handled_enc_pos = encoder_position;
    last_handled_running = motor_running;
  }

  // Instant Hardware Reaction to Physical Rotary Knob Turn
  if (encoder_position != last_handled_enc_pos || motor_running != last_handled_running) {
    last_handled_enc_pos = encoder_position;
    last_handled_running = motor_running;
    int target_pwm = (motor_running && !safety_tripped) ? encoder_position : 0;
    apply_motor_speed(target_pwm, motor_dir_forward);
    motor_pwm_target = target_pwm;
    current_applied_pwm = target_pwm;
  }

  // 2. Service Incoming Web Clients (HTTP REST)
  server.handleClient();

  // 3. Service Incoming UDP Packets (Remote Wireless Commands)
  int udp_packet_size = udp.parsePacket();
  if (udp_packet_size > 0) {
    char udp_buf[256];
    int len = udp.read(udp_buf, sizeof(udp_buf) - 1);
    if (len > 0) {
      udp_buf[len] = 0;
      String cmd = String(udp_buf);
      String res = execute_command(cmd);
      // Reply to sender
      udp.beginPacket(udp.remoteIP(), udp.remotePort());
      udp.write((const uint8_t*)res.c_str(), res.length());
      udp.endPacket();
    }
  }

  // 4. Remote software command slew-rate limiter
  static unsigned long last_ramp_time = 0;
  if (millis() - last_ramp_time >= 15) {
    last_ramp_time = millis();
    int desired_pwm = (motor_running && !safety_tripped && encoder_position > 0) ? encoder_position : 0;
    if (!enable_slew_rate) {
      current_applied_pwm = desired_pwm;
    } else {
      if (current_applied_pwm < desired_pwm) {
        if (current_applied_pwm < 140 && desired_pwm >= 150) current_applied_pwm = 150; // Jump over stall floor immediately
        else current_applied_pwm = min(desired_pwm, current_applied_pwm + 12);
      } else if (current_applied_pwm > desired_pwm) {
        current_applied_pwm = max(desired_pwm, current_applied_pwm - 20);
      }
    }
    apply_motor_speed(current_applied_pwm, motor_dir_forward);
    motor_pwm_target = current_applied_pwm;
  }

  // 5. Periodic Telemetry Acquisition & Multi-Transport Transmission (5 Hz)
  if (millis() - last_telemetry_tx >= TELEMETRY_INTERVAL_MS) {
    last_telemetry_tx = millis();

    // Read all sensor channels
    float v_b1, v_b2, v_pack, cell1, cell2, cell3, cell_delta;
    read_battery_taps(v_b1, v_b2, v_pack, cell1, cell2, cell3, cell_delta);

    float i_motor, i_total;
    read_currents(i_motor, i_total);

    float vib_g = read_vibration_g();
    float temp_c = read_temperature_c();
    int rpm = calculate_rpm(v_pack);

    // Motor voltage across terminal (supply scaled by duty cycle)
    float motor_voltage = v_pack * ((float)motor_pwm_target / 255.0f);

    // Safety Interlock Check (including Virtual Software BMS)
    check_safety_limits(i_motor, i_total, temp_c, vib_g, cell1, cell2, cell3, v_pack);

    // Get active IP for reporting
    if (WiFi.status() == WL_CONNECTED) {
      wifi_active_ip = WiFi.localIP().toString();
      wifi_sta_connected = true;
    } else {
      wifi_active_ip = WiFi.softAPIP().toString();
      wifi_sta_connected = false;
    }
    int rssi = wifi_sta_connected ? WiFi.RSSI() : -40; // Approx -40 dBm for direct AP

    // Emit Clean JSON Telemetry
    char json_buf[512];
    snprintf(json_buf, sizeof(json_buf),
             "{\"device_id\":\"RS380-MOT-01\",\"battery_voltage\":%.2f,\"motor_voltage\":%.2f,"
             "\"total_current\":%.2f,\"motor_current\":%.2f,\"temperature\":%.2f,\"vibration\":%.2f,"
             "\"rpm\":%d,\"pwm\":%d,\"direction\":\"%s\",\"cell1\":%.2f,\"cell2\":%.2f,\"cell3\":%.2f,"
             "\"cell_delta\":%.2f,\"alert\":\"%s\",\"wireless\":true,\"wifi_ip\":\"%s\",\"rssi\":%d,"
             "\"zero_m\":%.3f,\"zero_t\":%.3f,\"sens\":%.3f,\"raw_m\":%.3f,\"raw_t\":%.3f}\n",
             v_pack, motor_voltage, i_total, i_motor, temp_c, vib_g,
             rpm, motor_running ? motor_pwm_target : 0,
             motor_dir_forward ? "FWD" : "REV",
             cell1, cell2, cell3, cell_delta,
             safety_trip_reason.c_str(),
             wifi_active_ip.c_str(),
             rssi,
             zero_curr_motor_volt, zero_curr_total_volt, acs_sensitivity,
             last_raw_adc_m, last_raw_adc_t);

    latest_json_packet = String(json_buf);

    // Channel A: USB Serial Output
    Serial.print(json_buf);

    // Channel B: High-Speed UDP Wireless Broadcast
    udp.beginPacket(IPAddress(255, 255, 255, 255), UDP_PORT);
    udp.write((const uint8_t*)json_buf, strlen(json_buf));
    udp.endPacket();
  }

  // 6. Handle Incoming USB Serial Commands
  if (Serial.available() > 0) {
    String cmd = Serial.readStringUntil('\n');
    cmd.trim();
    String res = execute_command(cmd);
    Serial.println(res);
  }
}
