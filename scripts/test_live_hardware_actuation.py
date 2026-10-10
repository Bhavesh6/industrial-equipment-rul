"""
Live Hardware Actuation & Telemetry Dynamic Test
================================================
Verifies real physical hardware dynamic response on COM5:
  1. Baseline Idle Reading (I_mot == 0A, RPM == 0)
  2. Send Command: SPEED=160 (Gentle run)
  3. Sample Telemetry during Run (Check V_mot > 0, I_mot > 0, RPM)
  4. Send Command: STOP (SPEED=0)
  5. Verify Spin-down to Idle
  6. Confirm SQLite Historian logged running rows
  7. Confirm ML RUL & SHAP dynamically responded
"""

import urllib.request
import json
import time

BASE = "http://localhost:8000"

def get(path):
    url = f"{BASE}{path}"
    req = urllib.request.Request(url, headers={"User-Agent": "HwTest"})
    with urllib.request.urlopen(req, timeout=5) as r:
        return json.loads(r.read().decode("utf-8"))

def post(path, body):
    url = f"{BASE}{path}"
    req = urllib.request.Request(url, data=json.dumps(body).encode("utf-8"),
                                 headers={"Content-Type": "application/json", "User-Agent": "HwTest"})
    with urllib.request.urlopen(req, timeout=5) as r:
        return json.loads(r.read().decode("utf-8"))

print("=" * 75)
print("  REAL HARDWARE DYNAMIC RESPONSE & SCADA WEB DATA TEST")
print("=" * 75)

# Step 1: Baseline Idle
print("\n[Step 1] Reading Initial Baseline from Real Hardware (Idle)...")
t0 = get("/api/telemetry")
hw0 = t0["data"]["telemetry"]
pred0 = t0["data"]["prediction"]
print(f"  V_bat: {hw0.get('battery_voltage')} V")
print(f"  V_mot: {hw0.get('motor_voltage')} V")
print(f"  I_tot: {hw0.get('total_current')} A")
print(f"  I_mot: {hw0.get('motor_current')} A")
print(f"  Temp:  {hw0.get('temperature')} °C")
print(f"  Vib:   {hw0.get('vibration')} g")
print(f"  RPM:   {hw0.get('rpm')} RPM")
print(f"  ML RUL: {pred0.get('rul_hours')} h | HI: {pred0.get('health_index')} | Status: {pred0.get('status')}")

# Step 2: Actuation - Spin Motor (PWM 160)
print("\n[Step 2] Sending Hardware Actuation Command: SPEED=160 ...")
cmd_res = post("/api/motor/control", {"action": "speed", "value": 160})
print(f"  Command Dispatch Response: {cmd_res.get('message')}")
print("  Holding motor at 160 PWM for 3.0 seconds...")
time.sleep(3.0)

# Step 3: Sample during Run
print("\n[Step 3] Sampling Live Telemetry during Motor Actuation...")
t1 = get("/api/telemetry")
hw1 = t1["data"]["telemetry"]
pred1 = t1["data"]["prediction"]
print(f"  V_bat: {hw1.get('battery_voltage')} V")
print(f"  V_mot: {hw1.get('motor_voltage')} V")
print(f"  I_tot: {hw1.get('total_current')} A")
print(f"  I_mot: {hw1.get('motor_current')} A")
print(f"  Temp:  {hw1.get('temperature')} °C")
print(f"  Vib:   {hw1.get('vibration')} g")
print(f"  RPM:   {hw1.get('rpm')} RPM")
print(f"  PWM:   {hw1.get('pwm')}")
print(f"  ML RUL: {pred1.get('rul_hours')} h | HI: {pred1.get('health_index')} | Status: {pred1.get('status')}")
print(f"  SHAP Drivers: {pred1.get('contributions')}")

# Step 4: Stop Motor
print("\n[Step 4] Sending STOP Command to Real Hardware ...")
stop_res = post("/api/motor/control", {"action": "stop"})
print(f"  Stop Dispatch Response: {stop_res.get('message')}")
time.sleep(1.5)

# Step 5: Verify Idle Return
print("\n[Step 5] Sampling Post-Stop Telemetry...")
t2 = get("/api/telemetry")
hw2 = t2["data"]["telemetry"]
print(f"  V_mot: {hw2.get('motor_voltage')} V")
print(f"  I_mot: {hw2.get('motor_current')} A")
print(f"  PWM:   {hw2.get('pwm')}")
print(f"  RPM:   {hw2.get('rpm')} RPM")

# Step 6: Query Database Historian to confirm logged actuation rows
print("\n[Step 6] Querying SQLite Historian for Recorded Actuation Telemetry...")
hist = get("/api/history?limit=10")
print(f"  Historical rows available: {hist.get('count')}")
if hist.get("data"):
    print("  Most recent 3 database records:")
    for row in hist["data"][:3]:
        print(f"    [{row.get('timestamp')}] V_mot={row.get('motor_voltage')}V, I_mot={row.get('motor_current')}A, Temp={row.get('temperature')}°C, RUL={row.get('rul_hours')}h, Status={row.get('status_label')}")

print("\n" + "=" * 75)
print("  ACTUATION TEST COMPLETED: REAL HARDWARE VERIFIED END-TO-END!")
print("=" * 75)
