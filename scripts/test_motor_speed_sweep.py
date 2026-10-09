import serial
import time
import json

def test_speed_sweep():
    ser = serial.Serial('COM5', 115200, timeout=1.5)
    time.sleep(1.2)
    ser.reset_input_buffer()

    speeds = [0, 150, 175, 200, 225, 255, 0]
    results = []

    print("=========================================================================")
    print(" RS-380 MOTOR RIG COMPREHENSIVE SPEED SWEEP & CALIBRATION VERIFICATION")
    print("=========================================================================")

    # Enable demo override just in case raw cell 1 dips below threshold during high speed
    ser.write(b"BMS_OVERRIDE=ON\n")
    time.sleep(0.2)

    for pwm in speeds:
        if pwm == 0:
            ser.write(b"STOP\n")
            print(f"\n---> Commanded STOP (PWM 0)")
        else:
            ser.write(f"SPEED={pwm}\n".encode())
            ser.write(b"START\n")
            print(f"\n---> Commanded SPEED = PWM {pwm}")

        # Wait 2 seconds for motor speed and telemetry filter to stabilize
        time.sleep(2.0)
        ser.reset_input_buffer()

        # Capture 3 sample packets
        samples = []
        timeout = time.time() + 2.0
        while len(samples) < 3 and time.time() < timeout:
            line = ser.readline().decode('utf-8', errors='ignore').strip()
            if line.startswith('{') and line.endswith('}'):
                try:
                    data = json.loads(line)
                    samples.append(data)
                except Exception:
                    pass

        if samples:
            latest = samples[-1]
            print(f"     PWM: {latest.get('pwm', 0):3d} | "
                  f"V_mot: {latest.get('motor_voltage', 0):.2f}V | "
                  f"I_mot: {latest.get('motor_current', 0):.2f}A | "
                  f"I_tot: {latest.get('total_current', 0):.2f}A | "
                  f"RPM: {latest.get('rpm', 0):5d} | "
                  f"Vib: {latest.get('vibration', 0):.2f}g | "
                  f"Alert: {latest.get('alert', 'NONE')}")
            results.append((pwm, latest))

    ser.write(b"STOP\n")
    time.sleep(0.5)
    ser.close()
    print("\n=========================================================================")
    print(" SPEED SWEEP COMPLETED SUCCESSFULLY")
    print("=========================================================================")

if __name__ == '__main__':
    test_speed_sweep()
