import urllib.request
import json
import time

BASE_URL = "http://localhost:8000"

def send_motor_cmd(action, value=None):
    payload = {"action": action}
    if value is not None:
        payload["value"] = value
    req = urllib.request.Request(
        f"{BASE_URL}/api/motor/control",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req, timeout=3.0) as resp:
        return json.loads(resp.read().decode("utf-8"))

def get_telemetry():
    req = urllib.request.Request(f"{BASE_URL}/api/telemetry")
    with urllib.request.urlopen(req, timeout=3.0) as resp:
        data = json.loads(resp.read().decode("utf-8"))
        return data.get("telemetry") or data.get("data", {}).get("telemetry", {})

def run_low_to_high_calibration():
    print("=========================================================================================")
    print(" RS-380 LOW-TO-HIGH SPEED SWEEP & MULTI-SENSOR CALIBRATION (12.6V FULLY CHARGED)")
    print("=========================================================================================")

    # Test points from Low to High
    test_points = [
        {"name": "STANDBY / 0A BASELINE", "pwm": 0, "dwell": 3.0},
        {"name": "LOW SPEED (MIN TORQUE)", "pwm": 150, "dwell": 3.5},
        {"name": "LOW-MID SPEED",          "pwm": 175, "dwell": 3.5},
        {"name": "MID SPEED (CRUISE)",     "pwm": 200, "dwell": 3.5},
        {"name": "HIGH SPEED (MODULATION)","pwm": 225, "dwell": 3.5},
        {"name": "FULL THROTTLE (MAX)",    "pwm": 255, "dwell": 4.0},
        {"name": "DECELERATION TO STOP",   "pwm": 0,   "dwell": 3.0},
    ]

    records = []

    try:
        # Ensure demo BMS override is ON to avoid tripping during high speed ramp
        send_motor_cmd("bms_override", "ON")
        time.sleep(0.5)

        for pt in test_points:
            pwm = pt["pwm"]
            name = pt["name"]
            dwell = pt["dwell"]

            print(f"\n---> Actuating: {name} (Target PWM: {pwm})", flush=True)
            if pwm == 0:
                send_motor_cmd("stop")
            else:
                send_motor_cmd("speed", pwm)

            # Dwell time for motor to reach steady state and filter to settle
            time.sleep(dwell)

            # Sample 3 packets and average
            samples = []
            for _ in range(3):
                t = get_telemetry()
                if t:
                    samples.append(t)
                time.sleep(0.2)

            if samples:
                latest = samples[-1]
                rec = {
                    "step": name,
                    "pwm": latest.get("pwm", pwm),
                    "v_pack": latest.get("battery_voltage", 0.0),
                    "v_mot": latest.get("motor_voltage", 0.0),
                    "i_mot": latest.get("motor_current", 0.0),
                    "i_tot": latest.get("total_current", 0.0),
                    "rpm": latest.get("rpm", 0),
                    "vib": latest.get("vibration", 0.0),
                    "temp": latest.get("temperature", 0.0),
                    "cell1": latest.get("cell1", 0.0),
                    "cell2": latest.get("cell2", 0.0),
                    "cell3": latest.get("cell3", 0.0),
                    "delta": latest.get("cell_delta", 0.0),
                    "raw_m": latest.get("raw_m", 0.0),
                    "raw_t": latest.get("raw_t", 0.0),
                    "alert": latest.get("alert", "NONE"),
                }
                records.append(rec)
                print(f"     PWM: {rec['pwm']:3d} | V_mot: {rec['v_mot']:5.2f}V | I_mot: {rec['i_mot']:4.2f}A | "
                      f"I_tot: {rec['i_tot']:4.2f}A | RPM: {rec['rpm']:5d} | Vib: {rec['vib']:4.2f}g | "
                      f"V_pack: {rec['v_pack']:5.2f}V | Alert: {rec['alert']}")

    finally:
        send_motor_cmd("stop")
        print("\n---> Motor Safely Commanded to STOP.")

    print("\n=========================================================================================")
    print(" CHARACTERIZATION SUMMARY TABLE (LOW TO HIGH)")
    print("=========================================================================================")
    print(f"{'Step / PWM':<28} | {'V_mot':<7} | {'I_mot':<7} | {'I_tot':<7} | {'RPM':<6} | {'Vib (g)':<7} | {'Pack (V)':<8} | {'Alert':<6}")
    print("-" * 89)
    for r in records:
        print(f"{r['step'] + ' (' + str(r['pwm']) + ')':<28} | {r['v_mot']:5.2f}V  | {r['i_mot']:5.2f}A  | {r['i_tot']:5.2f}A  | {r['rpm']:5d}  | {r['vib']:5.2f}g   | {r['v_pack']:5.2f}V   | {r['alert']:<6}")
    print("=========================================================================================\n")

if __name__ == "__main__":
    run_low_to_high_calibration()
