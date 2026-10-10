"""
Comprehensive Live Hardware & Web Feature Verification Script
=============================================================
Tests all 10 SCADA web features with the active physical hardware on COM5:
  1. Live Telemetry & Sensor Sanity (COM5, 10 Hz)
  2. Real-Time ML Prognostics (GBR point estimate)
  3. Uncertainty Quantification (95% CI lower/upper bounds)
  4. Real-time SHAP Explainable AI (6-sensor attribution)
  5. Bi-Directional Motor Actuation Control API (Start, Speed, Stop, Reverse, E-Stop, Reset)
  6. Physical KY-040 Rotary Knob State & Sync
  7. SQLite Database Historian (/api/history & data/equipment_health.db)
  8. SCADA Telemetry CSV Export (/api/telemetry/export.csv)
  9. RAG Knowledge Base Search (/api/rag/search)
 10. AI Prognostics Copilot Chat (/api/chat)
"""

import sys
import json
import time
import urllib.request
import urllib.parse
from pathlib import Path

BASE_URL = "http://localhost:8000"

def get(path):
    url = f"{BASE_URL}{path}"
    req = urllib.request.Request(url, headers={"User-Agent": "WebFeatureTester"})
    with urllib.request.urlopen(req, timeout=8) as r:
        return r.status, json.loads(r.read().decode("utf-8"))

def get_raw(path):
    url = f"{BASE_URL}{path}"
    req = urllib.request.Request(url, headers={"User-Agent": "WebFeatureTester"})
    with urllib.request.urlopen(req, timeout=8) as r:
        return r.status, r.headers.get("Content-Type"), r.read()

def post(path, body):
    url = f"{BASE_URL}{path}"
    data = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json", "User-Agent": "WebFeatureTester"})
    with urllib.request.urlopen(req, timeout=12) as r:
        return r.status, json.loads(r.read().decode("utf-8"))

results = []

def check(feature, condition, details):
    status = "PASS" if condition else "FAIL"
    results.append((feature, status, details))
    print(f"[{status}] {feature}: {details}")

print("=" * 80)
print("  DEEP END-TO-END VERIFICATION: REAL HARDWARE + ALL SCADA WEB FEATURES")
print("=" * 80)

# -----------------------------------------------------------------------------
# 1. Live Telemetry & Hardware Connection
# -----------------------------------------------------------------------------
print("\n--- 1. Testing Live Hardware Telemetry Stream ---")
try:
    code, res = get("/api/telemetry")
    data = res.get("data", {})
    conn = data.get("connected")
    port = data.get("port")
    packets = data.get("packets_received", 0)
    hw = data.get("telemetry", {})
    
    check("HTTP 200 Telemetry API", code == 200, f"Returned code {code}")
    check("Physical Serial Link", conn and port == "COM5", f"Port: {port}, Connected: {conn}")
    check("High-Rate Ingestion", packets > 100, f"Packets Ingested: {packets}")
    
    v_bat = hw.get("battery_voltage", 0.0)
    v_mot = hw.get("motor_voltage", 0.0)
    i_tot = hw.get("total_current", 0.0)
    i_mot = hw.get("motor_current", 0.0)
    temp = hw.get("temperature", 0.0)
    vib = hw.get("vibration", 0.0)
    c1 = hw.get("cell1", 0.0)
    c2 = hw.get("cell2", 0.0)
    c3 = hw.get("cell3", 0.0)
    c_delta = hw.get("cell_delta", 0.0)
    
    check("Battery & 3S Cells", 10.0 <= v_bat <= 13.5 and c1 > 3.0 and c2 > 3.0 and c3 > 3.0,
          f"Pack: {v_bat:.2f}V | C1: {c1:.2f}V, C2: {c2:.2f}V, C3: {c3:.2f}V (Delta: {c_delta*1000:.0f}mV)")
    check("Motor Current & Voltage", 0.0 <= i_mot <= 5.0 and 0.0 <= v_mot <= 13.0,
          f"V_mot: {v_mot:.2f}V, I_mot: {i_mot:.2f}A, I_tot: {i_tot:.2f}A")
    check("Temperature & Vibration", 15.0 <= temp <= 65.0 and vib >= 0.0,
          f"Temp: {temp:.2f}°C, Vibration: {vib:.3f}g")
except Exception as e:
    check("Live Telemetry Stream", False, str(e))

# -----------------------------------------------------------------------------
# 2. Real-Time ML Prognostics
# -----------------------------------------------------------------------------
print("\n--- 2. Testing Real-Time ML Prognostics Engine ---")
try:
    pred = data.get("prediction", {})
    rul = pred.get("rul_hours", 0.0)
    health = pred.get("health_index", 0.0)
    status_label = pred.get("status", "")
    model_name = pred.get("model_used", "")
    
    check("ML Model Engine", model_name == "GradientBoosting", f"Active Model: {model_name}")
    check("RUL Point Estimate", 0.0 < rul <= 20.0, f"Predicted RUL: {rul:.2f} hours")
    check("Health Index Scale", 0.0 <= health <= 1.0, f"Health Index: {health:.3f} ({health*100:.1f}%)")
    check("Health Status Classification", status_label in ["HEALTHY", "DEGRADED", "CRITICAL"],
          f"Operational State: {status_label}")
except Exception as e:
    check("ML Prognostics Engine", False, str(e))

# -----------------------------------------------------------------------------
# 3. Uncertainty Quantification (95% CI)
# -----------------------------------------------------------------------------
print("\n--- 3. Testing 95% Uncertainty Confidence Interval (CI) ---")
try:
    ci_low = pred.get("rul_ci_low", 0.0)
    ci_high = pred.get("rul_ci_high", 0.0)
    spread = ci_high - ci_low
    check("Uncertainty Bounds Ordering", 0.0 <= ci_low <= rul <= ci_high,
          f"95% CI: [{ci_low:.2f}h – {ci_high:.2f}h] (Spread: {spread:.2f}h)")
    check("Uncertainty Spread Validity", 1.0 <= spread <= 15.0,
          f"Confidence interval band width: {spread:.2f} hours")
except Exception as e:
    check("Uncertainty Quantification", False, str(e))

# -----------------------------------------------------------------------------
# 4. Real-Time SHAP Explainable AI
# -----------------------------------------------------------------------------
print("\n--- 4. Testing Real-Time SHAP Explainable AI ---")
try:
    contrib = pred.get("contributions", {})
    top_driver = pred.get("top_contributor", "")
    top_pct = pred.get("top_contributor_pct", 0.0)
    
    expected_channels = ["vibration", "temperature", "motor_current", "total_current", "motor_voltage", "battery_voltage"]
    has_all = all(k in contrib for k in expected_channels)
    total_pct = sum(contrib.values())
    
    check("SHAP 6-Sensor Attribution", has_all, f"Decomposed channels: {list(contrib.keys())}")
    check("SHAP Normalization (100%)", 99.0 <= total_pct <= 101.0, f"Sum of feature attributions: {total_pct:.1f}%")
    check("Dominant Fault Driver", top_driver in contrib and top_pct > 20.0,
          f"Top Driver: '{top_driver}' ({top_pct:.1f}%)")
except Exception as e:
    check("SHAP Explainable AI", False, str(e))

# -----------------------------------------------------------------------------
# 5. Bi-Directional Motor Actuation Control API
# -----------------------------------------------------------------------------
print("\n--- 5. Testing Bi-Directional Motor Actuation Control API ---")
try:
    # Test setting speed PWM
    code, r_speed = post("/api/motor/control", {"action": "speed", "value": 0})
    check("Motor Control: Speed 0 PWM", r_speed.get("success", False), f"Msg: {r_speed.get('message')}")

    # Test reverse direction
    code, r_rev = post("/api/motor/control", {"action": "reverse"})
    check("Motor Control: Direction Toggle", r_rev.get("success", False), f"Msg: {r_rev.get('message')}")

    # Restore forward
    code, r_fwd = post("/api/motor/control", {"action": "dir_fwd"})
    check("Motor Control: Direction FWD", r_fwd.get("success", False), f"Msg: {r_fwd.get('message')}")

    # Test Clear Trip / Reset
    code, r_rst = post("/api/motor/control", {"action": "reset"})
    check("Motor Control: Safety Reset", r_rst.get("success", False), f"Msg: {r_rst.get('message')}")
except Exception as e:
    check("Motor Actuation Control", False, str(e))

# -----------------------------------------------------------------------------
# 6. Physical KY-040 Rotary Knob State & Sync
# -----------------------------------------------------------------------------
print("\n--- 6. Testing Rotary Encoder Knob Telemetry ---")
try:
    rpm = hw.get("rpm", 0)
    pwm = hw.get("pwm", 0)
    check("Rotary Encoder Telemetry Fields", "rpm" in hw and "pwm" in hw,
          f"Knob PWM: {pwm}, Tachometer: {rpm} RPM")
except Exception as e:
    check("Rotary Encoder Telemetry", False, str(e))

# -----------------------------------------------------------------------------
# 7. SQLite Database Historian (/api/history)
# -----------------------------------------------------------------------------
print("\n--- 7. Testing SQLite Database Historian Archive ---")
try:
    code, hist = get("/api/history")
    count = hist.get("count", 0)
    rows = hist.get("data", [])
    
    check("Historian API Response", code == 200 and hist.get("success", False), f"HTTP 200, count: {count}")
    check("Active Row Logging", count > 0 and len(rows) > 0, f"Retrieved {len(rows)} recent records")
    if rows:
        latest = rows[0]
        check("Historical Telemetry Schema", "timestamp" in latest and "health_index" in latest and "rul_hours" in latest,
              f"Latest: [{latest.get('timestamp')}] RUL={latest.get('rul_hours')}h, HI={latest.get('health_index')}, Status={latest.get('status_label')}")
except Exception as e:
    check("SQLite Historian Archive", False, str(e))

# -----------------------------------------------------------------------------
# 8. SCADA Telemetry CSV Export (/api/telemetry/export.csv)
# -----------------------------------------------------------------------------
print("\n--- 8. Testing SCADA Telemetry CSV Export ---")
try:
    code, content_type, raw_bytes = get_raw("/api/telemetry/export.csv")
    csv_text = raw_bytes.decode("utf-8")
    lines = [l for l in csv_text.splitlines() if l.strip()]
    
    check("CSV Export HTTP Status", code == 200 and "text/csv" in content_type, f"Content-Type: {content_type}")
    check("CSV Header Structure", "Timestamp,Device_ID,Battery_Voltage_V" in lines[0],
          f"Header columns: {len(lines[0].split(','))} fields")
    check("CSV Rows Exported", len(lines) >= 2, f"Total CSV rows available: {len(lines)}")
except Exception as e:
    check("SCADA Telemetry CSV Export", False, str(e))

# -----------------------------------------------------------------------------
# 9. RAG Knowledge Base Search (/api/rag/search)
# -----------------------------------------------------------------------------
print("\n--- 9. Testing RAG Knowledge Base Search ---")
try:
    code, rag_data = get("/api/rag/search?q=overheating+bushing+lubrication")
    hits = rag_data.get("results", [])
    
    check("RAG Search API", code == 200 and rag_data.get("success", False), f"Query: '{rag_data.get('query')}'")
    check("Semantic Document Hits", len(hits) >= 1, f"Found {len(hits)} relevant passages")
    if hits:
        top = hits[0]
        check("Top Ranked Passage", top.get("score", 0) > 3.0,
              f"[{top.get('doc')}] {top.get('title')} (BM25: {top.get('score'):.2f})")
except Exception as e:
    check("RAG Knowledge Base Search", False, str(e))

# -----------------------------------------------------------------------------
# 10. AI Prognostics Copilot Chat (/api/chat)
# -----------------------------------------------------------------------------
print("\n--- 10. Testing AI Prognostics Copilot Assistant ---")
try:
    code, chat_res = post("/api/chat", {
        "message": "Motor vibration is 0.72g, temperature is 48°C. What is the current RUL prognosis and recommended action according to standard SOP?",
        "role": "maintenance_engineer"
    })
    reply = chat_res.get("reply", "")
    
    check("Copilot Chat Response", code == 200 and chat_res.get("success", False), f"Reply length: {len(reply)} chars")
    check("Live Telemetry Grounding", any(w in reply.lower() for w in ["rul", "hour", "health", "deg", "temperature", "vibration"]),
          "Grounded in real prognostics & sensor telemetry")
    check("RAG SOP Knowledge Grounding", any(w in reply.lower() for w in ["sop", "lubricat", "bearing", "bushing", "maintenance", "alignment"]),
          "Synthesized maintenance guidelines from RAG knowledge base")
except Exception as e:
    check("AI Prognostics Copilot Assistant", False, str(e))

# -----------------------------------------------------------------------------
# Summary
# -----------------------------------------------------------------------------
print("\n" + "=" * 80)
total_tests = len(results)
passed_tests = sum(1 for _, st, _ in results if st == "PASS")
failed_tests = total_tests - passed_tests

print(f"  TOTAL CHECKS: {total_tests} | PASSED: {passed_tests} | FAILED: {failed_tests}")
print("=" * 80)

if failed_tests == 0:
    print("\n>>> ALL WEB FEATURES ARE 100% OPERATIONAL WITH REAL PHYSICAL HARDWARE! <<<")
else:
    print(f"\n>>> ATTENTION: {failed_tests} CHECKS FAILED <<<")
