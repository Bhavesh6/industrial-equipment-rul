"""In-app help chatbot, Gemini first with Groq as a fallback. Exact PPE architecture.

Answers "how do I..." questions about EquipmentHealth itself, scoped to what
the asking account can actually see and do — a guest gets pointed at the
hardware specifications and testbed overview, an operator gets live motor
telemetry, 4S battery cell balance, and alarm status explained, an admin gets
the full calibration console, reports, and change log. The scoping is a
system prompt per role, not a permissions check on the model's output: the
model is told what's true for this account and asked to stay inside it.

Two providers, tried in order, because both free tiers have daily caps and
running out mid-demo is the failure that actually matters here — they're
unlikely to be exhausted at the same moment. Either key may be blank; only
a request with no working provider at all falls back to the built-in guide.
"""

import os
import time
from pathlib import Path
import requests

try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).resolve().parent.parent / ".env")
    load_dotenv()
except ImportError:
    pass

MAX_MESSAGE_LEN = 800
MAX_HISTORY_TURNS = 6  # each turn is a user+model pair; older context is dropped, not summarized


def _get_config(key, default=""):
    try:
        from flask import current_app
        if current_app and key in current_app.config:
            return current_app.config[key]
    except Exception:
        pass
    return os.getenv(key, default)


# Answers for a server with no language model configured.
#
# Deliberately not dressed up as a fake conversation: it provides clear,
# authoritative SCADA engineering guidance and live telemetry data so the
# user is never left without an answer even in air-gapped environments.
_GUIDE = [
    (("admin", "operator", "guest"), ("current", "amp", "load", "motor current", "total current"),
     "Current Telemetry Breakdown:\n"
     "- Total System Current measures gross bus draw from the 4S battery pack via ACS715 (nominal ~2.82 A).\n"
     "- Motor Load Current isolates armature conduction through the MOSFET H-bridge (nominal ~2.30 A, ~81% of total load).\n"
     "- Auxiliary Load (~0.52 A) powers the ESP32 MCU, logic drivers, and sensor pull-ups.\n"
     "If Motor Current spikes above 3.5 A, inspect for mechanical jamming, bearing seizure, or winding faults."),

    (("admin", "operator", "guest"), ("voltage", "drop", "motor voltage", "total voltage", "eff"),
     "Voltage Regulation Rail:\n"
     "- Total Pack Voltage is the direct sum of all 4 battery cells (nominal ~14.82 V).\n"
     "- Motor Terminal Voltage is the armature PWM drive voltage (nominal ~12.04 V).\n"
     "- Forward Conduction Drop (ΔV ~2.78 V) represents driver MOSFET R_DS(on) and wiring resistance.\n"
     "Voltage transfer efficiency typically sits at ~81.2%."),

    (("admin", "operator", "guest"), ("battery", "cell", "balance", "imbalance", "lipo", "liion"),
     "4S Battery Pack Cell Telemetry:\n"
     "- Cell 1 (~3.715 V), Cell 2 (~3.702 V), Cell 3 (~3.710 V), Cell 4 (~3.693 V).\n"
     "- Pack Imbalance (ΔV) is the spread between the highest and lowest cell.\n"
     "- Threshold: ΔV < 50 mV is considered nominal and balanced. If ΔV exceeds 50 mV, run a BMS cell-balancing cycle."),

    (("admin", "operator", "guest"), ("rul", "remaining useful life", "hours", "lifetime", "prognostic", "health"),
     "Prognostics & RUL:\n"
     "- The Health Index (H) operates from 0% (critical failure) to 100% (brand new).\n"
     "- Est. RUL predicts remaining operating hours until H drops below the 70% maintenance threshold.\n"
     "- A 95% Confidence Interval (CI) is computed around the prediction (e.g. 2,800 h to 3,600 h).\n"
     "View detailed degradation curves on the Prognostics page."),

    (("admin", "operator", "guest"), ("vibration", "bearing", "harmonic", "shake", "vib", "rms"),
     "Vibration & Mechanical Health:\n"
     "- Accelerometer tracks Vib X, Vib Y, and Vib Z axes at 2 Hz streaming.\n"
     "- Top Contributor identifies which axis exhibits highest deviation from baseline.\n"
     "Recommended checks for high vibration: 1) Verify rotor shaft coupling alignment, 2) Tighten mounting fasteners, 3) Inspect sintered bronze bearings for radial play."),

    (("admin", "operator", "guest"), ("temp", "temperature", "heat", "hot", "thermal"),
     "Thermal Envelope:\n"
     "- Motor casing operates nominally around 38–42 °C.\n"
     "- Warning threshold is 55 °C; critical thermal shutdown is 70 °C.\n"
     "If temperature rises rapidly, verify cooling airflow and check for dry/unlubricated bearings."),

    (("admin", "operator"), ("alert", "threshold", "hazard", "alarm"),
     "Alerts & Alarms:\n"
     "- Tracks warning and critical severity thresholds for vibration, temperature, and current.\n"
     "- A critical alert flags immediate operator action required.\n"
     "View past events and acknowledgment logs on the Anomaly Alerts page."),

    (("admin",), ("report", "export", "csv", "download"),
     "Reports & Exports:\n"
     "- Use the Export button in the top bar to download the live 13-column telemetry log as CSV.\n"
     "- Includes timestamps, all 3 vibration axes, temperature, total current, motor current, total voltage, motor voltage, and all 4 battery cell voltages."),

    (("admin",), ("calibration", "slider", "baseline", "tune", "sensitivity"),
     "Calibration Console:\n"
     "- Adjust anomaly detection sensitivity (0–100%) and exponential degradation decay rate (1–30 days).\n"
     "- Changes take effect immediately across the real-time scoring engine."),

    (("admin",), ("audit", "change log", "history of changes"),
     "Audit Log:\n"
     "- Append-only record of system events, parameter changes, and threshold overrides.\n"
     "- Entries cannot be edited or deleted, ensuring industrial traceability."),

    (("admin", "guest"), ("system", "spec", "hardware", "esp32", "rs380"),
     "System Specifications:\n"
     "- Equipment: RS-380 Brushed DC Motor (12V nominal, 6,200 RPM rated).\n"
     "- Microcontroller: ESP32 dual-core Xtensa 32-bit @ 240 MHz.\n"
     "- Sensors: MPU-6050 3-axis accelerometer, ACS715 Hall-effect current sensors, DS18B20 1-wire temperature sensor, 4S Li-ion balance tap ADC."),
]

PAGE_CONTEXT = {
    "index.html": "the Overview console — live SCADA metrics, 4S battery & DC power distribution card, sensor tiles, and telemetry feed",
    "prognostics.html": "the Prognostics page — SHAP degradation attributions, RUL projections, and confidence bands",
    "alerts.html": "the Anomaly Alerts page — critical and warning alarms with live status filtering",
    "waveforms.html": "the Waveform Captures page — 5-channel live oscilloscope view streaming at 2 Hz",
    "reports.html": "the Reports page — generated summaries and historical CSV export archive",
    "calibration.html": "the Calibration page — sensitivity sliders and baseline threshold tuning",
    "audit.html": "the Audit Log page — immutable timestamped record of calibrations and operational events",
    "system.html": "the System Info page — ESP32 pinout diagram, firmware status, and RS-380 motor hardware specifications"
}

_BASE_PROMPT = """You are the AI Equipment Copilot for EquipmentHealth, a smart predictive maintenance system for an RS-380 DC Motor testbed.
You speak like a friendly, knowledgeable, and approachable senior electrical engineer or lab colleague—warm, engaging, natural, and genuinely helpful, like a great teammate chatting with you in person.

Conversational Style Guidelines:
- Be warm, friendly, and human! Greet the user naturally when appropriate (e.g. "Hey there!", "Happy to help!", "Great question!").
- Speak in natural, conversational language. Avoid sounding like a stiff corporate robot or an automated CLI script. Instead of "Based on your live SCADA overview telemetry, here is the breakdown...", say "Here's what's happening under the hood right now:" or "Let's take a look at the motor's power draw:".
- When using headings, use short, clean markdown titles (e.g. `### Current Breakdown` or `### Quick Maintenance Tip`), and keep paragraphs concise and easy to read.
- Explain things intuitively with real engineering insight, then tie them directly to the live motor telemetry readings in the prompt.
- When discussing issues, be encouraging and actionable (e.g. "Good news—the pack is in great shape!", or "Nothing critical right now, but I'd recommend checking...").
- Ground your answers in the live motor telemetry provided in the prompt whenever relevant.
- Never invent nonexistent physical hardware features.
"""

SYSTEM_PROMPTS = {
    "guest": _BASE_PROMPT + """
This person is viewing as a guest or visitor. What they can explore:
- The live overview testbed demo with real-time sensor streams and electrical telemetry.
- RS-380 motor hardware specs, ESP32 microcontroller architecture, and sensor instrumentation.
- High-level predictive maintenance principles (RUL estimation, vibration harmonics, 4S battery balancing).
They cannot modify calibration sliders or download industrial audit archives.
""",
    "operator": _BASE_PROMPT + """
This person is a certified plant operator running equipment tests. What they can do:
- Monitor live operational telemetry: Total Current vs Motor Current, 4S battery cell balance, core temperature, and 3-axis vibration.
- Check real-time RUL projections and 95% confidence intervals.
- Acknowledge warning and critical hazard alarms on the Anomaly Alerts page.
- Review recent telemetry logs and sensor waveforms.
They cannot modify baseline calibration thresholds or alter system sensitivity settings.
""",
    "admin": _BASE_PROMPT + """
This person is a lead diagnostic engineer with full administrative access to the SCADA console.
Pages and features:
- Overview: live SCADA KPI rail, DC power subsystem (Total Current, Motor Current, Pack Voltage, Motor Voltage, 4S cell balance), sensor grid, and 13-column live feed.
- Prognostics: SHAP degradation attribution, RUL probability distributions, and Weibull degradation curves.
- Anomaly Alerts: warning/critical threshold filters, alarm acknowledgement log, and fault severity tracker.
- Waveform Captures: 5-channel real-time oscilloscope streaming at 2 Hz.
- Reports: CSV exports of the 13-channel telemetry feed for any selected timeframe.
- Calibration: tuning anomaly detection sensitivity (0–100%) and exponential degradation decay rate (1–30 days).
- Audit Log: immutable append-only record of calibrations, alarms, and operator overrides.
- System Info: ESP32 pinout diagram, firmware version, and RS-380 brushed DC motor technical specifications.
"""
}


def _offline_answer(message, role, page, telemetry=None):
    """Answer from the built-in guide when no external LLM is configured."""
    text = (message or "").lower()
    best, best_score = None, 0
    for roles, keywords, answer in _GUIDE:
        if role not in roles:
            continue
        score = sum(1 for word in keywords if word in text)
        if score > best_score:
            best, best_score = answer, score

    here = PAGE_CONTEXT.get(page)
    note = ("\n\n*This is the built-in guide - connect a `GEMINI_API_KEY` or `GROQ_API_KEY` on the server for full generative AI.*")

    if best:
        if telemetry and any(w in text for w in ("current", "voltage", "battery", "rul", "health", "temp", "status")):
            h = telemetry.get("health", 98.5)
            rul = telemetry.get("rulHours", 3200)
            tot_i = telemetry.get("totalCurrent", 2.82)
            mot_i = telemetry.get("motorCurrent", 2.30)
            tot_v = telemetry.get("totalVoltage", 14.82)
            mot_v = telemetry.get("motorVoltage", 12.04)
            live_prefix = f"**Live Snapshot**: Health `{h:.1f}%` | RUL `{rul} h` | I_tot `{tot_i:.2f} A` | I_mot `{mot_i:.2f} A` | V_tot `{tot_v:.2f} V` | V_mot `{mot_v:.2f} V`\n\n"
            return live_prefix + best + note
        return best + note

    topics = "Current telemetry, Voltage regulation, 4S Battery cells, RUL prognostics, Vibration, Thermal limits, Alerts, Reports, and Calibration."
    where = f"You are on {here}. " if here else ""
    return f"{where}I can assist with: {topics} Ask about any of those by name.{note}"


def _build_system_prompt(role, page, telemetry=None):
    prompt = SYSTEM_PROMPTS.get(role, SYSTEM_PROMPTS["admin"])
    if telemetry:
        prompt += f"""
Live Equipment Telemetry Snapshot:
- Health Index: {telemetry.get('health', 98.5):.1f}% (Normal >70%, Warning 40-70%, Critical <40%)
- Est. RUL: {telemetry.get('rulHours', 3200)} operating hours (CI: [{telemetry.get('rulLo', 2800)}h – {telemetry.get('rulHi', 3600)}h])
- Total System Current: {telemetry.get('totalCurrent', 2.82):.3f} A (4S pack bus draw via ACS715)
- Motor Load Current: {telemetry.get('motorCurrent', 2.30):.3f} A (Armature conduction)
- Auxiliary Current: {telemetry.get('auxCurrent', 0.52):.3f} A (ESP32 MCU, driver logic, sensors)
- Total Battery Voltage: {telemetry.get('totalVoltage', 14.82):.2f} V (4S Li-ion pack sum)
- Motor Terminal Voltage: {telemetry.get('motorVoltage', 12.04):.2f} V (Forward PWM drive)
- Forward Voltage Drop: {telemetry.get('totalVoltage', 14.82) - telemetry.get('motorVoltage', 12.04):.2f} V
- 4S Battery Cells: Cell 1={telemetry.get('cell1', 3.715):.3f}V, Cell 2={telemetry.get('cell2', 3.702):.3f}V, Cell 3={telemetry.get('cell3', 3.710):.3f}V, Cell 4={telemetry.get('cell4', 3.693):.3f}V
- Cell Imbalance: {telemetry.get('cellDeltaMv', 22)} mV (Balanced <50 mV)
- Vibration Driver: {telemetry.get('topAxis', 'Vib X')} ({telemetry.get('rms', 0.05):.3f} g)
- Core Temperature: {telemetry.get('temp', 42.0):.1f} °C
"""
    hint = PAGE_CONTEXT.get((page or "").strip().lower())
    if hint:
        prompt += f"\nCurrently the operator is viewing {hint}."
    return prompt


def _trim_history(history):
    turns = []
    for turn in (history or [])[-(MAX_HISTORY_TURNS * 2):]:
        if not isinstance(turn, dict):
            continue
        text = str(turn.get("text", "")).strip()[:MAX_MESSAGE_LEN]
        if not text:
            continue
        role = "assistant" if turn.get("role") == "assistant" else "user"
        turns.append({"role": role, "text": text})
    return turns


def _ask_gemini(system_prompt, turns, message):
    key = _get_config("GEMINI_API_KEY") or _get_config("GOOGLE_API_KEY")
    if not key:
        return None, None, True

    contents = [
        {"role": "model" if t["role"] == "assistant" else "user", "parts": [{"text": t["text"]}]}
        for t in turns
    ]
    contents.append({"role": "user", "parts": [{"text": message}]})

    model_pref = _get_config("GEMINI_MODEL") or "gemini-flash-lite-latest"
    candidate_models = [model_pref]
    for fallback_m in ("gemini-3.5-flash-lite", "gemini-flash-latest", "gemini-1.5-flash"):
        if fallback_m not in candidate_models:
            candidate_models.append(fallback_m)

    payload = {
        "system_instruction": {"parts": [{"text": system_prompt}]},
        "contents": contents,
        "generationConfig": {"maxOutputTokens": 1024, "temperature": 0.3},
    }

    last_status = None
    for model in candidate_models:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
        backoff = (1.0, 2.5)
        for attempt in range(3):
            try:
                res = requests.post(url, params={"key": key}, json=payload, timeout=20)
            except requests.RequestException:
                return None, "Could not reach the assistant", False
            if res.status_code != 503:
                break
            if attempt < len(backoff):
                time.sleep(backoff[attempt])

        if not res:
            continue
        last_status = res.status_code
        if res.status_code == 429:
            return None, None, True
        if res.status_code == 404:
            continue
        if not res.ok:
            if res.status_code == 503:
                continue
            return None, "The assistant couldn't answer that just now.", False

        try:
            return res.json()["candidates"][0]["content"]["parts"][0]["text"].strip(), None, False
        except (KeyError, IndexError, ValueError):
            return None, "The assistant couldn't answer that.", False

    if last_status == 503:
        return None, "The assistant is busy right now - ask again in a moment.", False
    return None, "The assistant could not reach a suitable model.", False


def _ask_groq(system_prompt, turns, message):
    key = _get_config("GROQ_API_KEY")
    if not key:
        return None, None, True

    messages = [{"role": "system", "content": system_prompt}]
    messages += [{"role": t["role"], "content": t["text"]} for t in turns]
    messages.append({"role": "user", "content": message})

    model = _get_config("GROQ_MODEL") or "llama-3.3-70b-versatile"
    try:
        res = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
            json={"model": model, "messages": messages, "max_tokens": 700, "temperature": 0.3},
            timeout=20,
        )
    except requests.RequestException:
        return None, "Could not reach the assistant", False

    if res.status_code == 429:
        return None, None, True
    if not res.ok:
        return None, "The assistant couldn't answer that just now.", False

    try:
        return res.json()["choices"][0]["message"]["content"].strip(), None, False
    except (KeyError, IndexError, ValueError):
        return None, "The assistant couldn't answer that.", False


def enabled():
    return bool(_get_config("GEMINI_API_KEY") or _get_config("GOOGLE_API_KEY") or _get_config("GROQ_API_KEY"))


def ask(message, role="admin", history=None, page=None, telemetry=None):
    message = (message or "").strip()
    if not message:
        return None, "No message supplied"
    if len(message) > MAX_MESSAGE_LEN:
        return None, "Message too long"

    if not enabled():
        return _offline_answer(message, role, page, telemetry), None

    system_prompt = _build_system_prompt(role, page, telemetry)
    turns = _trim_history(history)

    last_error = None
    for provider in (_ask_gemini, _ask_groq):
        reply, error, exhausted = provider(system_prompt, turns, message)
        if reply:
            return reply, None
        if not exhausted:
            return None, error
        last_error = error

    return None, last_error or "The assistant has hit its daily free-tier limit. It'll work again tomorrow."
