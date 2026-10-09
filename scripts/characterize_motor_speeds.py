"""
RS-380 Motor Multi-Speed Sensor Characterization
================================================
Steps the motor through multiple PWM speeds over COM5,
records sensor readings at each speed level, and outputs
a clean hardware calibration table.
"""

import sys
import time
import json
import serial

def main():
    port = "COM5"
    baud = 115200

    print("=" * 80)
    print(" RS-380 SENSOR CHARACTERIZATION AT MULTIPLE MOTOR SPEEDS")
    print("=" * 80)
    print(f"Connecting to ESP32 on {port}...")

    ser = serial.Serial()
    ser.port = port
    ser.baudrate = baud
    ser.timeout = 1.0
    ser.dtr = False
    ser.rts = False
    ser.open()
    time.sleep(1.5)

    speeds = [
        (0,   "0% (STOPPED)"),
        (80,  "31% (LOW)"),
        (120, "47% (MEDIUM-LOW)"),
        (160, "63% (MEDIUM)"),
        (200, "78% (HIGH)"),
        (240, "94% (MAX DEMO)"),
    ]

    results = []

    print("\nStarting step-by-step speed sweep...\n")

    for pwm, label in speeds:
        print(f">> Applying PWM {pwm} [{label}]...")
        if pwm == 0:
            ser.write(b"STOP\n")
        else:
            ser.write(f"SPEED={pwm}\n".encode("utf-8"))
            ser.write(b"START\n")

        # Allow motor speed to stabilize (1.5 seconds)
        time.sleep(1.5)

        # Collect 5 samples at this speed
        samples = []
        for _ in range(6):
            line = ser.readline().decode("utf-8", errors="ignore").strip()
            if line.startswith("{") and line.endswith("}"):
                try:
                    data = json.loads(line)
                    samples.append(data)
                except Exception:
                    pass

        if samples:
            # Average the readings
            avg_b_volt = sum(s.get("battery_voltage", 0.0) for s in samples) / len(samples)
            avg_m_volt = sum(s.get("motor_voltage", 0.0) for s in samples) / len(samples)
            avg_t_curr = sum(s.get("total_current", 0.0) for s in samples) / len(samples)
            avg_m_curr = sum(s.get("motor_current", 0.0) for s in samples) / len(samples)
            avg_temp   = sum(s.get("temperature", 0.0) for s in samples) / len(samples)
            avg_vib    = sum(s.get("vibration", 0.0) for s in samples) / len(samples)
            alert      = samples[-1].get("alert", "NONE")

            results.append({
                "pwm": pwm,
                "label": label,
                "b_volt": avg_b_volt,
                "m_volt": avg_m_volt,
                "t_curr": avg_t_curr,
                "m_curr": avg_m_curr,
                "temp": avg_temp,
                "vib": avg_vib,
                "alert": alert
            })

    # Always safely stop motor at end of test
    ser.write(b"STOP\n")
    time.sleep(0.5)
    ser.close()

    print("\n" + "=" * 80)
    print(" SENSOR CHARACTERIZATION REPORT")
    print("=" * 80)
    print(" PWM | SPEED LEVEL       | BATT (V) | MTR (V) | TOTAL (A) | MTR (A) | TEMP (°C) | VIB (g) | ALERT")
    print("-" * 80)
    for r in results:
        print(f" {r['pwm']:3d} | {r['label']:17s} | {r['b_volt']:6.2f}V  | {r['m_volt']:5.2f}V  | {r['t_curr']:7.2f}A  | {r['m_curr']:5.2f}A  |  {r['temp']:5.1f}°C   | {r['vib']:5.2f}g  | {r['alert']}")
    print("=" * 80)
    print("Test complete. Motor safely stopped.")

if __name__ == "__main__":
    main()
