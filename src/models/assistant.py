"""
Context-Grounded Maintenance Assistant Engine
Generates technical root cause analysis (RCA), safety evaluations, and maintenance steps
using real-time sensor telemetry and rule-based diagnostic playbooks, with optional LLM API fallback.
"""

import os
from typing import Dict, Any, Optional
from datetime import datetime


class MaintenanceAssistant:
    def __init__(self):
        self.api_key_openai = os.getenv("OPENAI_API_KEY")
        self.api_key_gemini = os.getenv("GOOGLE_API_KEY")

    def analyze_health(self, query: str, telemetry: Dict[str, Any], health_results: Dict[str, Any]) -> str:
        """
        Synthesizes live telemetry, health indices, and fault attributions into an actionable maintenance report.
        """
        h = health_results.get("health_index", 1.0)
        rul = health_results.get("rul_hours", 10.0)
        rul_low = health_results.get("rul_ci_low", 8.0)
        rul_high = health_results.get("rul_ci_high", 11.0)
        top_sensor = health_results.get("top_contributor", "none")
        top_pct = health_results.get("contributions", {}).get(top_sensor, 0.0)
        status_label = health_results.get("status_label", "HEALTHY")
        cond = telemetry.get("condition", "Normal Operation")

        sensor_labels = {
            "battery_voltage": "Battery Voltage",
            "motor_voltage": "Motor Voltage",
            "total_current": "Total System Current",
            "motor_current": "Motor Current",
            "temperature": "Casing Temperature",
            "vibration": "Vibration (801S Module)"
        }

        # Status badge
        if status_label == "HEALTHY":
            status_badge = "🟢 **HEALTHY (Nominal Operational Envelope)**"
            urgency = "Standard routine preventive inspection schedule."
        elif status_label == "WARNING":
            status_badge = "🟡 **WARNING (Degradation Detected)**"
            urgency = "Schedule inspection at the next available service window."
        else:
            status_badge = "🔴 **CRITICAL (Failure Threshold Breached)**"
            urgency = "⚠️ **Immediate intervention / motor de-energization advised.**"

        sections = []
        sections.append(f"### 📋 Equipment Health & Prognostic Assessment")
        sections.append(f"- **Asset Tag**: `RS380-MOT-01` (12V Brushed DC Motor)")
        sections.append(f"- **Operating Status**: {status_badge}")
        sections.append(f"- **Active Condition Mode**: `{cond}`")
        sections.append(f"- **Health Index ($H$)**: `{h:.3f}` / 1.000 (Failure threshold: `0.700`)")
        sections.append(f"- **Remaining Useful Life (RUL)**: `{rul:.2f} operating hours` (95% CI: `[{rul_low:.2f}h – {rul_high:.2f}h]`)")
        sections.append(f"- **Root Cause Factor**: **{sensor_labels.get(top_sensor, top_sensor)}** driving **{top_pct:.1f}%** of anomalous deviation.\n")

        sections.append(f"### 🔍 Telemetry vs Baseline Deviations")
        sections.append("| Sensor | Measured | Nominal Baseline | Deviation | Status |")
        sections.append("| :--- | :--- | :--- | :--- | :--- |")
        
        baseline_refs = {
            "battery_voltage": (12.20, "V"),
            "motor_voltage": (11.80, "V"),
            "total_current": (2.10, "A"),
            "motor_current": (1.85, "A"),
            "temperature": (38.00, "°C"),
            "vibration": (0.35, "g")
        }

        for s_key, (base_val, unit) in baseline_refs.items():
            meas_val = telemetry.get(s_key, base_val)
            delta = meas_val - base_val
            pct_contrib = health_results.get("contributions", {}).get(s_key, 0.0)
            flag = "⚠️ High Impact" if pct_contrib > 30 else ("⚡ Moderate" if pct_contrib > 15 else "✅ Normal")
            sections.append(f"| **{sensor_labels.get(s_key, s_key)}** | `{meas_val:.2f} {unit}` | `{base_val:.2f} {unit}` | `{delta:+.2f} {unit}` | {flag} |")

        sections.append(f"\n### 🛠️ Step-by-Step Maintenance Playbook")
        if top_sensor == "vibration":
            sections.append("1. **Rotor Alignment & Balance Check**: Inspect motor shaft coupling for eccentric load or loose set screws.")
            sections.append("2. **Mounting Integrity**: Confirm vibration damping mounts and motor bracket fasteners are torqued to specification.")
            sections.append("3. **Bearing Inspection**: Test for radial play on the front/rear sintered bronze bushings or ball bearings.")
        elif top_sensor in ["motor_current", "total_current"]:
            sections.append("1. **Mechanical Load Verification**: Inspect gearbox or attached load for binding, friction, or jamming.")
            sections.append("2. **Commutator & Brush Health**: Inspect carbon brushes for uneven wear, pitting, or carbon dust accumulation.")
            sections.append("3. **Electrical Insulation**: Measure winding resistance across terminals to detect partial turn-to-turn short circuits.")
        elif top_sensor == "temperature":
            sections.append("1. **Airflow & Heat Sinking**: Remove any dust buildup obstructing motor ventilation slots.")
            sections.append("2. **Duty Cycle Audit**: Ensure duty cycle does not exceed thermal dissipation capacity (>60°C continuous).")
            sections.append("3. **Bearing Lubrication**: Dry bearings produce friction heat; apply light synthetic lubricant if applicable.")
        elif top_sensor in ["motor_voltage", "battery_voltage"]:
            sections.append("1. **Supply Verification**: Check 3S LiPo battery pack state-of-charge, cell balance, and internal resistance.")
            sections.append("2. **Switching Driver Resistance**: Check MOSFET H-bridge driver board for thermal throttling or excessive forward drop.")

        if query and query.strip():
            sections.append(f"\n### 💬 Targeted Response to: *\"{query}\"*")
            q_lower = query.lower()
            if "rul" in q_lower or "lifetime" in q_lower or "how long" in q_lower:
                sections.append(f"Estimated Remaining Useful Life is **{rul:.2f} hours** with a 95% confidence interval of `[{rul_low:.2f}h – {rul_high:.2f}h]`. Correcting the anomalous `{sensor_labels.get(top_sensor, top_sensor)}` will halt accelerated degradation.")
            elif "shut" in q_lower or "stop" in q_lower or "safe" in q_lower:
                if h < 0.70:
                    sections.append("🚨 **SAFETY ALERT: Immediate shutdown recommended.** The health index is below the $0.70$ safety limit. Continued operation risks catastrophic thermal or mechanical stall.")
                else:
                    sections.append("System is operating within permissible safety margins, but proactive inspection of the indicated driver is recommended.")
            else:
                sections.append(f"To address this, focus on **{sensor_labels.get(top_sensor, top_sensor)}**, which accounts for **{top_pct:.1f}%** of the total deviation index.")

        sections.append(f"\n> **Urgency Assessment**: {urgency}")
        return "\n".join(sections)
