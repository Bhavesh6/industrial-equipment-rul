import serial
import time
import json

def run_test():
    ser = serial.Serial('COM5', 115200, timeout=1.5)
    time.sleep(1.0)
    ser.reset_input_buffer()

    print("=== READING RESTING TELEMETRY ===")
    for _ in range(5):
        line = ser.readline().decode('utf-8', errors='ignore').strip()
        if line.startswith('{'):
            print("REST:", line)

    print("\n=== SENDING BMS_OVERRIDE=ON ===")
    ser.write(b"BMS_OVERRIDE=ON\n")
    time.sleep(0.2)

    print("\n=== STARTING MOTOR @ PWM 160 ===")
    ser.write(b"SPEED=160\n")
    ser.write(b"START\n")
    time.sleep(0.5)

    print("\n=== READING RUNNING TELEMETRY (3 SECONDS) ===")
    start_t = time.time()
    while time.time() - start_t < 3.0:
        line = ser.readline().decode('utf-8', errors='ignore').strip()
        if line.startswith('{'):
            print("RUN: ", line)

    print("\n=== STOPPING MOTOR ===")
    ser.write(b"STOP\n")
    time.sleep(0.5)

    for _ in range(5):
        line = ser.readline().decode('utf-8', errors='ignore').strip()
        if line.startswith('{'):
            print("STOP:", line)

    ser.close()
    print("\nTest completed.")

if __name__ == '__main__':
    run_test()
