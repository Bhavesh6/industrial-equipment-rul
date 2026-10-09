import urllib.request
import json
import time

def send_cmd(action, value=None):
    url = "http://localhost:8000/api/motor/control"
    payload = json.dumps({"action": action, "value": value}).encode("utf-8")
    req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read().decode("utf-8"))

def get_telemetry():
    url = "http://localhost:8000/api/telemetry"
    with urllib.request.urlopen(url) as resp:
        d = json.loads(resp.read().decode("utf-8"))
        return d.get("data", {}).get("telemetry", {})

print("=" * 60)
print("TEST 1: RS-380 Motor Running Test (PWM 150)")
print("=" * 60)

print("Starting motor at PWM 150...")
res = send_cmd("speed", 150)
print("Speed response:", res)

samples = []
for i in range(15):
    time.sleep(0.2)
    t = get_telemetry()
    samples.append(t)
    print(f"[{i*0.2:.1f}s] PWM: {t.get('pwm')} | Mot I: {t.get('motor_current')}A | Tot I: {t.get('total_current')}A | "
          f"Mot V: {t.get('motor_voltage')}V | Batt V: {t.get('battery_voltage')}V | Vib: {t.get('vibration')}g | Temp: {t.get('temperature')}C")

print("\nStopping motor safely...")
send_cmd("stop")
time.sleep(0.5)
final_t = get_telemetry()
print("Final stopped state:", final_t.get('motor_current'), "A, PWM:", final_t.get('pwm'))
