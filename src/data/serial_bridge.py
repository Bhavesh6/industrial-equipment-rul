"""
RS-380 Hardware Serial Bridge & Live Prognostics Ingestion
==========================================================
Connects your laptop directly to the ESP32 on COM5 via USB Serial,
ingests the live multi-sensor JSON telemetry stream, runs real-time
Machine Learning RUL inferences, and prints an industrial SCADA console.

USAGE:
    python src/data/serial_bridge.py
    python src/data/serial_bridge.py COM5
"""

import sys
import os
import time
import json
from pathlib import Path

# Add project root to path
ROOT_DIR = Path(__file__).resolve().parent.parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

try:
    import serial
    import serial.tools.list_ports
except ImportError:
    print("Error: pyserial not installed. Run: pip install pyserial")
    sys.exit(1)

from src.models.predict import RULPredictor


def find_esp32_port(preferred="COM5"):
    ports = list(serial.tools.list_ports.comports())
    for p in ports:
        if p.device == preferred:
            return preferred
    for p in ports:
        desc = (p.description or "").lower()
        if "cp210" in desc or "ch340" in desc or "uart" in desc or "usb" in desc:
            return p.device
    return preferred if ports else None


def main():
    target_port = sys.argv[1] if len(sys.argv) > 1 else find_esp32_port()
    baud_rate = 115200

    if not target_port:
        print("❌ No serial port detected. Please plug in the ESP32 via USB.")
        sys.exit(1)

    print("=" * 75)
    print(f" RS-380 IIoT Serial Bridge & Real-Time ML Engine ({target_port} @ {baud_rate})")
    print("=" * 75)
    print("Loading Machine Learning model pipelines...")
    predictor = RULPredictor()
    print(f"✅ ML Engine Ready (Model: {'GradientBoosting + RandomForest' if predictor.is_ml_ready else 'Rule-Based Fallback'})")
    print("Connecting to ESP32... (Press Ctrl+C to stop)\n")

    try:
        ser = serial.Serial()
        ser.port = target_port
        ser.baudrate = baud_rate
        ser.timeout = 1.0
        ser.dtr = False
        ser.rts = False
        ser.open()
    except Exception as e:
        print(f"❌ Could not open {target_port}: {e}")
        sys.exit(1)

    time.sleep(1.0)
    print("---------------------------------------------------------------------------")
    print(" TIME    | VOLT  | M-CURR | T-CURR | TEMP  | VIB   | ML RUL  | HEALTH | STATUS")
    print("---------------------------------------------------------------------------")

    sample_count = 0
    try:
        while True:
            line = ser.readline().decode("utf-8", errors="ignore").strip()
            if not line:
                continue

            if not line.startswith("{") or not line.endswith("}"):
                # Debug / print setup text
                if not line.startswith("[PWM"):
                    print(f"  [ESP32] {line}")
                continue

            try:
                data = json.loads(line)
            except Exception:
                continue

            sample_count += 1

            # Run ML Inference
            pred = predictor.predict(data)
            now_str = time.strftime("%H:%M:%S")

            b_volt = data.get("battery_voltage", 0.0)
            m_curr = data.get("motor_current", 0.0)
            t_curr = data.get("total_current", 0.0)
            temp_c = data.get("temperature", 0.0)
            vib_g  = data.get("vibration", 0.0)

            rul_h  = pred.get("rul_hours", 0.0)
            h_idx  = pred.get("health_index", 1.0)
            status = pred.get("status", "HEALTHY")

            status_icon = "🟢" if status == "HEALTHY" else ("🟡" if status == "WARNING" else "🔴")

            print(f" {now_str} | {b_volt:5.2f}V| {m_curr:5.2f}A | {t_curr:5.2f}A | {temp_c:4.1f}°C | {vib_g:4.2f}g | {rul_h:5.2f}h  |  {h_idx:.2f}  | {status_icon} {status}")

    except KeyboardInterrupt:
        print("\n\nBridge stopped by user.")
    finally:
        ser.close()


if __name__ == "__main__":
    main()
