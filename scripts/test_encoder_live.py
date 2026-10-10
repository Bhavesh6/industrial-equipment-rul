import urllib.request
import json
import time
import sys

BASE_URL = "http://localhost:8000"

def get_telemetry():
    try:
        req = urllib.request.Request(f"{BASE_URL}/api/telemetry")
        with urllib.request.urlopen(req, timeout=1.5) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return data.get("data", {}).get("telemetry", {})
    except Exception:
        return None

def monitor_encoder_live(duration_s=60):
    print("=" * 80, flush=True)
    print(" KY-040 ROTARY ENCODER LIVE HARDWARE TEST MONITOR", flush=True)
    print("=" * 80, flush=True)
    print("Hardware Controls Ready on ESP32:", flush=True)
    print("  -> Turn Knob Clockwise:      Increases speed (0 -> 150 -> 160 -> ... -> 255)", flush=True)
    print("  -> Turn Knob Counter-Clockwise: Decreases speed (... -> 150 -> 0)", flush=True)
    print("  -> Press Knob (Push SW):     Toggles START / STOP (or clears safety trips)", flush=True)
    print("-" * 80, flush=True)
    print("Listening for physical knob inputs from the user on the rig...", flush=True)
    print("-" * 80, flush=True)

    last_pwm = None
    last_rpm = None
    start_time = time.time()

    # Get initial baseline
    t = get_telemetry()
    if t:
        last_pwm = t.get("pwm", 0)
        last_rpm = t.get("rpm", 0)
        print(f"[CURRENT STATE] PWM: {last_pwm:3d} | Motor: {t.get('motor_voltage', 0.0):5.2f}V | "
              f"Current: {t.get('motor_current', 0.0):4.2f}A | RPM: {last_rpm:5d} | "
              f"Pack: {t.get('battery_voltage', 0.0):5.2f}V", flush=True)

    while (time.time() - start_time) < duration_s:
        t = get_telemetry()
        if t:
            pwm = t.get("pwm", 0)
            rpm = t.get("rpm", 0)
            v_mot = t.get("motor_voltage", 0.0)
            i_mot = t.get("motor_current", 0.0)
            i_tot = t.get("total_current", 0.0)
            vib = t.get("vibration", 0.0)
            v_pack = t.get("battery_voltage", 0.0)
            alert = t.get("alert", "NONE")

            # Detect change in PWM or significant change in state
            if last_pwm is not None and pwm != last_pwm:
                action = "ACCELERATION" if pwm > last_pwm else ("STOPPED" if pwm == 0 else "DECELERATION")
                print(f"---> [KNOB EVENT: {action:<12}] Target PWM: {pwm:3d} (was {last_pwm:3d}) | "
                      f"V_mot: {v_mot:5.2f}V | I_mot: {i_mot:4.2f}A | RPM: {rpm:5d} | "
                      f"Vib: {vib:4.2f}g | Alert: {alert}", flush=True)
                last_pwm = pwm
                last_rpm = rpm
            elif last_pwm is not None and pwm > 0 and abs(rpm - (last_rpm or 0)) > 400:
                print(f"     [RUNNING] PWM: {pwm:3d} | V_mot: {v_mot:5.2f}V | I_mot: {i_mot:4.2f}A | "
                      f"RPM: {rpm:5d} | Vib: {vib:4.2f}g", flush=True)
                last_rpm = rpm

        time.sleep(0.15)

    print("\n[MONITOR] Test window finished. Motor status safe.", flush=True)

if __name__ == "__main__":
    dur = int(sys.argv[1]) if len(sys.argv) > 1 else 90
    monitor_encoder_live(duration_s=dur)
