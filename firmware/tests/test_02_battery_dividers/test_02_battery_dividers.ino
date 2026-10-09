/*
 * TEST 02: Battery Voltage Dividers (GPIO 32, GPIO 34, GPIO 35)
 * -----------------------------------------------------------------------------
 * Tests 3S LiPo battery taps:
 * - B1 cumulative tap -> GPIO 32 (Cell 1, nominal 3.7V - 4.2V)
 * - B2 cumulative tap -> GPIO 34 (Cell 1+2, nominal 7.4V - 8.4V)
 * - B+ total pack tap -> GPIO 35 (Total 3S, nominal 11.1V - 12.6V)
 * 
 * Resistors: 30 kΩ upper, 4.7 kΩ lower
 * Nominal divider ratio = (30.0 + 4.7) / 4.7 = 7.38298
 * 
 * Displays:
 * 1. Raw ADC counts (0 - 4095)
 * 2. Pin Voltage at ESP32 (V)
 * 3. Scaled Tap Voltage (V)
 * 4. Extracted Individual Cell Voltages (Cell 1, Cell 2, Cell 3)
 * 5. Cell Imbalance (Max - Min in mV)
 */

#include <Arduino.h>

#define PIN_BATT_B1     32
#define PIN_BATT_B2     34
#define PIN_BATT_B_PACK 35

const float V_REF = 3.30;
const float ADC_MAX = 4095.0;
const float R_UPPER_KOHM = 30.0;
const float R_LOWER_KOHM = 4.7;
const float DIVIDER_RATIO = (R_UPPER_KOHM + R_LOWER_KOHM) / R_LOWER_KOHM; // 7.38298

// Trimmer multipliers for fine-tuning against your multimeter
float cal_b1    = 1.000;
float cal_b2    = 1.000;
float cal_bpack = 1.000;

float read_avg_volts(int pin, int samples = 40) {
  uint32_t sum = 0;
  for (int i = 0; i < samples; i++) {
    sum += analogRead(pin);
    delayMicroseconds(80);
  }
  float avg_raw = (float)sum / samples;
  return (avg_raw / ADC_MAX) * V_REF;
}

int read_avg_raw(int pin, int samples = 20) {
  uint32_t sum = 0;
  for (int i = 0; i < samples; i++) {
    sum += analogRead(pin);
    delayMicroseconds(50);
  }
  return sum / samples;
}

void setup() {
  Serial.begin(115200);
  delay(1200);
  Serial.println("\n========================================================");
  Serial.println(" TEST 02: 3S BATTERY VOLTAGE DIVIDERS (GPIO 32, 34, 35)");
  Serial.println("========================================================");
  Serial.printf(" Upper Resistor: %.1f kΩ | Lower Resistor: %.1f kΩ\n", R_UPPER_KOHM, R_LOWER_KOHM);
  Serial.printf(" Nominal Ratio: %.4f\n", DIVIDER_RATIO);
  Serial.println("--------------------------------------------------------");
  Serial.println("Tap B1: GPIO 32  |  Tap B2: GPIO 34  |  Tap B+: GPIO 35");
  Serial.println("========================================================\n");

  analogSetAttenuation(ADC_11db);

  pinMode(PIN_BATT_B1, INPUT);
  pinMode(PIN_BATT_B2, INPUT);
  pinMode(PIN_BATT_B_PACK, INPUT);
}

unsigned long last_print = 0;

void loop() {
  if (millis() - last_print >= 500) {
    last_print = millis();

    int raw_b1 = read_avg_raw(PIN_BATT_B1);
    int raw_b2 = read_avg_raw(PIN_BATT_B2);
    int raw_bp = read_avg_raw(PIN_BATT_B_PACK);

    float v_pin1 = read_avg_volts(PIN_BATT_B1);
    float v_pin2 = read_avg_volts(PIN_BATT_B2);
    float v_pinp = read_avg_volts(PIN_BATT_B_PACK);

    float v_tap1 = v_pin1 * DIVIDER_RATIO * cal_b1;
    float v_tap2 = v_pin2 * DIVIDER_RATIO * cal_b2;
    float v_pack = v_pinp * DIVIDER_RATIO * cal_bpack;

    // Series cell voltages
    float cell1 = v_tap1;
    float cell2 = max(0.0f, v_tap2 - v_tap1);
    float cell3 = max(0.0f, v_pack - v_tap2);

    float max_c = max(cell1, max(cell2, cell3));
    float min_c = min(cell1, min(cell2, cell3));
    float delta_mv = (max_c - min_c) * 1000.0;

    Serial.printf("[ADC RAW] B1=%4d (Pin: %.3fV) | B2=%4d (Pin: %.3fV) | B+=%4d (Pin: %.3fV)\n",
                  raw_b1, v_pin1, raw_b2, v_pin2, raw_bp, v_pinp);
    Serial.printf("[TAPS]    Tap1: %5.2f V   | Tap2: %5.2f V   | Total Pack: %5.2f V\n",
                  v_tap1, v_tap2, v_pack);
    Serial.printf("[CELLS]   Cell 1: %4.2f V | Cell 2: %4.2f V | Cell 3: %4.2f V | Δ: %4.0f mV\n",
                  cell1, cell2, cell3, delta_mv);
    Serial.println("--------------------------------------------------------------------------------");
  }
}
