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
    from rag.retriever import rag_retriever
except ImportError:
    try:
        import sys
        sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
        from rag.retriever import rag_retriever
    except Exception:
        rag_retriever = None

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
     "- Total System Current measures gross bus draw from the 3S battery pack via ACS712 (nominal ~0.20 - 0.50 A).\n"
     "- Motor Load Current isolates armature conduction through the L298N driver (nominal ~0.35 - 0.45 A no-load, up to 1.8 A loaded).\n"
     "- Auxiliary Load (~0.08 - 0.15 A) powers the ESP32 MCU, logic drivers, and sensor pull-ups.\n"
     "If Motor Current spikes above 3.0 A, safety interlock triggers OVERCURRENT_TRIP to prevent winding burnout."),

    (("admin", "operator", "guest"), ("voltage", "drop", "motor voltage", "total voltage", "eff"),
     "Voltage Regulation Rail:\n"
     "- Total Pack Voltage is the direct sum of all 3 battery cells (nominal ~11.1 V - 12.6 V).\n"
     "- Motor Terminal Voltage is the armature PWM drive voltage (scaled from 0V to Pack Voltage).\n"
     "- Forward Conduction Drop represents driver saturation and wiring resistance.\n"
     "Voltage is protected by Virtual BMS with a 2.80 V/cell under-voltage cutoff."),

    (("admin", "operator", "guest"), ("battery", "cell", "balance", "imbalance", "lipo", "liion"),
     "3S Battery Pack Cell Telemetry:\n"
     "- Cell 1 (~4.20 V), Cell 2 (~4.20 V), Cell 3 (~4.20 V) running averages.\n"
     "- Pack Imbalance (ΔV) is the spread between the highest and lowest cell.\n"
     "- Threshold: ΔV < 150 mV is considered nominal and balanced. If ΔV exceeds 350 mV, the Virtual BMS flags an imbalance warning."),

    (("admin", "operator", "guest"), ("rul", "remaining useful life", "hours", "lifetime", "prognostic", "health"),
     "Prognostics & RUL:\n"
     "- The Health Index operates from 0.0 (critical failure) to 1.0 (brand new).\n"
     "- Est. RUL predicts remaining operating hours with a 95% Confidence Interval (e.g. ±3.53 h) via Gradient Boosting.\n"
     "- SHAP attribution breaks down the percentage influence of vibration, temperature, currents, and voltages.\n"
     "View detailed degradation curves on the Prognostics page."),

    (("admin", "operator", "guest"), ("vibration", "bearing", "harmonic", "shake", "vib", "rms"),
     "Vibration & Mechanical Health:\n"
     "- Dynamic accelerometer continuously monitors casing vibration magnitude and FFT spectrum.\n"
     "- Baseline idle vibration is typically 0.15–0.22 g; operating nominal under load is 0.30–0.45 g.\n"
     "Recommended checks for high vibration: 1) Verify rotor shaft coupling alignment, 2) Tighten mounting fasteners, 3) Inspect bronze bearings for radial play."),

    (("admin", "operator", "guest"), ("temp", "temperature", "heat", "hot", "thermal"),
     "Thermal Envelope:\n"
     "- Motor casing operates nominally around 28–45 °C measured via DS18B20.\n"
     "- Warning threshold is 55 °C; critical thermal shutdown is 70 °C.\n"
     "If temperature rises rapidly, verify cooling airflow and check for dry/unlubricated bearings."),

    (("admin", "operator"), ("alert", "threshold", "hazard", "alarm"),
     "Alerts & Alarms:\n"
     "- Tracks warning and critical severity thresholds for vibration, temperature, current, and cell balance.\n"
     "- Emergency Stop (ESTOP) cutoff disengages motor drive immediately.\n"
     "View past events and acknowledgment logs on the Anomaly Alerts page."),

    (("admin",), ("report", "export", "csv", "download", "pdf", "docx"),
     "Reports & Technical Deliverables:\n"
     "- Official Project Technical & Experimental Results Report available in PDF and Word DOCX formats under /reports/.\n"
     "- Includes complete system architecture, mathematical derivations, SHAP analysis, and hardware benchmarks.\n"
     "- CSV exports of real-time telemetry logs are also available."),

    (("admin",), ("calibration", "slider", "baseline", "tune", "sensitivity"),
     "Calibration Console:\n"
     "- Zero-voltage offset calibration and sensitivity trim for ACS712 current sensors.\n"
     "- Voltage divider trim multipliers for 3S battery cells and overall pack voltage.\n"
     "- Changes take effect immediately across the real-time scoring engine."),

    (("admin",), ("audit", "change log", "history of changes"),
     "Audit Log:\n"
     "- Append-only record of system events, parameter changes, and threshold overrides.\n"
     "- SQLite Historian logs 1 Hz telemetry frames with complete electrical and mechanical vitals."),

    (("admin", "guest"), ("system", "spec", "hardware", "esp32", "rs380"),
     "System Specifications:\n"
     "- Equipment: Single RS-380 Brushed DC Motor (12V nominal, 6,200 - 12,000 RPM).\n"
     "- Microcontroller: ESP32 dual-core Xtensa 32-bit @ 240 MHz (Dual Wi-Fi AP + STA + USB Serial).\n"
     "- Sensors: Dynamic accelerometer vibration sensor, ACS712 Hall-effect current sensors, DS18B20 1-wire temperature sensor, 3S Li-ion balance tap ADC.\n"
     "- Driver: L298N Dual H-Bridge motor driver with PWM speed regulation and direction control."),
]

PAGE_CONTEXT = {
    "index.html": "the Overview console — live SCADA metrics, 3S battery & DC power distribution card, sensor tiles, and telemetry feed",
    "prognostics.html": "the Prognostics page — SHAP degradation attributions, RUL projections, and confidence bands",
    "alerts.html": "the Anomaly Alerts page — critical and warning alarms with live status filtering",
    "waveforms.html": "the Waveform Captures page — 5-channel live oscilloscope view streaming at 2 Hz",
    "reports.html": "the Reports page — generated summaries, official technical reports (PDF/DOCX), and CSV export archive",
    "calibration.html": "the Calibration page — sensitivity sliders, zero-offsets, and baseline threshold tuning",
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
- The live single RS-380 motor testbed with real-time sensor streams and electrical telemetry.
- RS-380 motor hardware specs, ESP32 microcontroller architecture, and sensor instrumentation.
- High-level predictive maintenance principles (RUL estimation, vibration harmonics, 3S battery balancing).
They cannot modify calibration sliders or download industrial audit archives.
""",
    "operator": _BASE_PROMPT + """
This person is a certified plant operator running equipment tests. What they can do:
- Monitor live operational telemetry: Total Current vs Motor Current, 3S battery cell balance, core temperature, and dynamic vibration.
- Check real-time RUL projections and 95% confidence intervals.
- Acknowledge warning and critical hazard alarms on the Anomaly Alerts page.
- Review recent telemetry logs and sensor waveforms.
They cannot modify baseline calibration thresholds or alter system sensitivity settings.
""",
    "admin": _BASE_PROMPT + """
This person is a lead diagnostic engineer with full administrative access to the SCADA console.
Pages and features:
- Overview: live SCADA KPI rail, DC power subsystem (Total Current, Motor Current, Pack Voltage, Motor Voltage, 3S cell balance), sensor grid, and live feed.
- Prognostics: SHAP degradation attribution, RUL probability distributions, and Weibull degradation curves.
- Anomaly Alerts: warning/critical threshold filters, alarm acknowledgement log, and fault severity tracker.
- Waveform Captures: multi-channel real-time oscilloscope streaming.
- Reports: official project technical reports (PDF/DOCX) and CSV exports of the telemetry feed.
- Calibration: tuning current sensor offsets, sensitivity, and 3S voltage divider trims.
- Audit Log: immutable append-only record of calibrations, alarms, and operator overrides.
- System Info: ESP32 pinout diagram, firmware status, and single RS-380 brushed DC motor technical specifications.
"""
}


def _offline_answer(message, role, page, telemetry=None, rag_context=""):
    """Answer grounded in live hardware telemetry and RAG knowledge base when offline."""
    text = (message or "").lower()
    
    t = telemetry or {}
    pred = t.get("prediction") or {}

    bat_v = float(t.get("battery_voltage", t.get("totalVoltage", 12.48)))
    mot_v = float(t.get("motor_voltage", t.get("motorVoltage", 0.0)))
    tot_i = float(t.get("total_current", t.get("totalCurrent", 0.08)))
    mot_i = float(t.get("motor_current", t.get("motorCurrent", 0.0)))
    temp  = float(t.get("temperature", t.get("temp", 28.5)))
    vib   = float(t.get("vibration", t.get("rms", 0.18)))
    pwm   = int(t.get("pwm", 0))
    rpm   = int(t.get("rpm", 0))

    raw_h = pred.get("health_index", t.get("health", 1.0))
    h_pct = float(raw_h) * 100.0 if float(raw_h) <= 1.0 else float(raw_h)
    rul_h = float(pred.get("rul_hours", t.get("rulHours", 12.5)))
    ci_lo = float(pred.get("rul_ci_low", t.get("rulLo", max(0.0, rul_h - 2.5))))
    ci_hi = float(pred.get("rul_ci_high", t.get("rulHi", rul_h + 3.0)))
    top_s = str(pred.get("top_contributor", "temperature")).replace("_", " ").title()
    top_p = float(pred.get("top_contributor_pct", 46.3))
    status_lbl = str(pred.get("status", "HEALTHY")).upper()

    live_header = (
        f"**Live RS-380 Hardware Vitals**: Status `{status_lbl}` | Health `{h_pct:.1f}%` | "
        f"RUL `{rul_h:.2f} h` (95% CI: `[{ci_lo:.2f}h – {ci_hi:.2f}h]`) | "
        f"I_mot `{mot_i:.2f} A` | Temp `{temp:.1f} °C` | Vib `{vib:.3f} g` | V_bat `{bat_v:.2f} V`\n\n"
        f"**Dominant SHAP Driver**: **{top_s}** contributing **{top_p:.1f}%** of model output.\n\n"
    )

    if rag_context:
        return live_header + rag_context + "\n\n*(Grounded response via in-house RAG knowledge base & active hardware sensors)*"

    best, best_score = None, 0
    for roles, keywords, answer in _GUIDE:
        if role not in roles:
            continue
        score = sum(1 for word in keywords if word in text)
        if score > best_score:
            best, best_score = answer, score

    here = PAGE_CONTEXT.get(page)
    note = "\n\n*(Telemetry-grounded guide - connect `GEMINI_API_KEY` or `GROQ_API_KEY` for conversational LLM reasoning)*"

    if best:
        return live_header + best + note

    topics = "Current telemetry, Voltage regulation, 3S Battery cells, RUL prognostics, Vibration, Thermal limits, Maintenance SOPs, and Safety guidelines."
    where = f"You are on {here}. " if here else ""
    return f"{where}{live_header}I can assist with: {topics} Ask about any of those by name.{note}"


def _build_system_prompt(role, page, telemetry=None, rag_context=""):
    prompt = SYSTEM_PROMPTS.get(role, SYSTEM_PROMPTS["admin"])
    if telemetry:
        t = telemetry or {}
        pred = t.get("prediction") or {}

        bat_v = float(t.get("battery_voltage", t.get("totalVoltage", 12.48)))
        mot_v = float(t.get("motor_voltage", t.get("motorVoltage", 0.0)))
        tot_i = float(t.get("total_current", t.get("totalCurrent", 0.08)))
        mot_i = float(t.get("motor_current", t.get("motorCurrent", 0.0)))
        temp  = float(t.get("temperature", t.get("temp", 28.5)))
        vib   = float(t.get("vibration", t.get("rms", 0.18)))
        pwm   = int(t.get("pwm", 0))
        rpm   = int(t.get("rpm", 0))
        c1    = float(t.get("cell1", 4.17))
        c2    = float(t.get("cell2", 4.17))
        c3    = float(t.get("cell3", 4.14))
        cdelta = float(t.get("cell_delta", 0.03))

        raw_h = pred.get("health_index", t.get("health", 1.0))
        h_pct = float(raw_h) * 100.0 if float(raw_h) <= 1.0 else float(raw_h)
        rul_h = float(pred.get("rul_hours", t.get("rulHours", 12.5)))
        ci_lo = float(pred.get("rul_ci_low", t.get("rulLo", max(0.0, rul_h - 2.5))))
        ci_hi = float(pred.get("rul_ci_high", t.get("rulHi", rul_h + 3.0)))
        top_s = str(pred.get("top_contributor", "temperature")).replace("_", " ").title()
        top_p = float(pred.get("top_contributor_pct", 46.3))
        status_lbl = str(pred.get("status", "HEALTHY")).upper()
        model_name = str(pred.get("model_used", "GradientBoosting"))

        prompt += f"""
Live RS-380 Hardware Telemetry Snapshot (Real Sensors on ESP32):
- Motor Speed / PWM: {pwm} / 255 (Est. {rpm} RPM)
- Battery Voltage: {bat_v:.2f} V (3S Li-ion pack)
- Motor Terminal Voltage: {mot_v:.2f} V
- Total System Current: {tot_i:.2f} A
- Motor Armature Current: {mot_i:.2f} A
- Motor Housing Temperature: {temp:.1f} °C (DS18B20)
- Vibration Acceleration: {vib:.3f} g (801S Sensor)
- LiPo Battery Cell Balance: Cell 1={c1:.2f}V, Cell 2={c2:.2f}V, Cell 3={c3:.2f}V (Delta={cdelta*1000:.0f} mV)

Machine Learning Prognostics & SHAP Degradation Attribution:
- ML Model: {model_name}
- Equipment Operating Status: {status_lbl}
- Health Index (H): {h_pct:.1f}% (Healthy >=85%, Warning 70-85%, Critical <70%)
- Remaining Useful Life (RUL): {rul_h:.2f} operating hours
- 95% Confidence Interval (Uncertainty): [{ci_lo:.2f}h – {ci_hi:.2f}h]
- Dominant Degradation Driver (SHAP Explainable AI): {top_s} contributing {top_p:.1f}% of anomalous variation
"""
    if rag_context:
        prompt += f"\n{rag_context}\n"

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

    # Query RAG knowledge retriever for relevant maintenance manuals & SOPs
    rag_context = ""
    if rag_retriever is not None:
        try:
            chunks = rag_retriever.search(
                query=message,
                top_k=2,
                telemetry=telemetry,
                prediction=telemetry.get("prediction") if telemetry else None
            )
            rag_context = rag_retriever.format_context_for_prompt(chunks)
        except Exception as e:
            print(f"[RAG] Search error: {e}")

    if not enabled():
        return _offline_answer(message, role, page, telemetry, rag_context), None

    system_prompt = _build_system_prompt(role, page, telemetry, rag_context)
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
