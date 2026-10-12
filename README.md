# Industrial Equipment Health Monitoring & RUL Prediction SCADA System
### *Real-Time Digital Twin, Machine Learning Prognostics & IoT Telemetry for RS-380 DC Motors*

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](https://opensource.org/licenses/MIT)
[![Framework: FreeRTOS & ESP32](https://img.shields.io/badge/Firmware-ESP32%20FreeRTOS-red.svg)](https://www.espressif.com/)
[![Standards: ISO 10816-3 & ISO 13374](https://img.shields.io/badge/Standards-ISO%2010816--3%20%7C%20ISO%2013374-orange.svg)](#)

---

## 📌 Executive Summary

This project is an industrial-grade **IIoT Predictive Maintenance, Condition-Based Monitoring (CBM), and Remaining Useful Life (RUL) Prognostics System** engineered for electromechanical drive equipment (centered on an RS-380 / RP-380 brushed DC motor testbed).

It bridges physical hardware telemetry acquired by an **ESP32 DevKit microcontroller** with a **Python SCADA edge server**, an **ensemble of Machine Learning models** (Random Forest 95% CI + Gradient Boosting + Isolation Forest + SHAP Explainability), a persistent **SQLite time-series historian**, a **Virtual 3S Lithium-Ion Battery Management System (BMS)**, an **interactive Calibration & Safety Interlock Studio**, and a modern **web-based SCADA Digital Twin console** featuring an **AI Maintenance Copilot**.

```
+---------------------------------------------------------------------------------------------------+
|                                  PHYSICAL HARDWARE TESTBED                                        |
|  RS-380 Brushed DC Motor  |  3S 18650 Li-ion Pack (12.6V)  |  L298N Dual H-Bridge Driver          |
|  Dual ACS712 Current Sens |  DS18B20 Digital Temp Probe     |  801S Analog Vibration Accelerometer |
|  KY-040 Rotary Encoder    |  Precision Battery Dividers     |  Common GND & Power Rails            |
+---------------------------------------------------------------------------------------------------+
                                                │
                                    (Analog / 1-Wire / GPIO)
                                                ▼
+---------------------------------------------------------------------------------------------------+
|                                   ESP32 SENSOR NODE (MCU)                                         |
|  - 12-bit ADC1 Sampling (FreeRTOS)                         - PWM Speed & Direction Control        |
|  - Hardware Safety Thresholds                              - Soft-Start Slew Rate Limiter         |
|  - Simultaneous Dual-Transport Streaming:                                                         |
|       * High-Speed USB Serial (115,200 baud)               * Wireless Wi-Fi UDP Broadcast (:8888)  |
|       * Embedded HTTP REST Server (:80)                    * Standalone SoftAP (192.168.4.1)      |
+---------------------------------------------------------------------------------------------------+
                                                │
                                     (USB Serial / UDP Wi-Fi)
                                                ▼
+---------------------------------------------------------------------------------------------------+
|                               PYTHON SCADA EDGE SERVER & BACKEND                                  |
|  - Real-Time Dual Bridge (`dashboard/serve.py`)            - SQLite Historian (`equipment_health`) |
|  - Health Index Fusion Engine (0.0 - 1.0)                  - Virtual BMS Safety Interlock         |
|  - ML Pipeline: GBR + RF Regressor (R²=0.82)               - Anomaly Detection: Isolation Forest  |
|  - SHAP TreeExplainer Degradation Attribution              - AI Copilot: ISO 13374 RAG Engine     |
|  - Automated Calibration Dispatcher                        - Real-Time Watchdog Safety Cutoff     |
+---------------------------------------------------------------------------------------------------+
                                                │
                                     (REST APIs & WebSockets)
                                                ▼
+---------------------------------------------------------------------------------------------------+
|                                  SCADA WEB DIGITAL TWIN CONSOLE                                   |
|  - SCADA Overview & KPI Rail (Chart.js 4 + Lucide)         - Interactive RUL & Health Trajectory  |
|  - Hardware Controls: Rotary Dial, PWM Slider, Presets     - Real-Time Multi-Channel Oscilloscope |
|  - Calibration Studio: Overcurrent, Vibration, Temp, BMS  - PDF & CSV Technical Audit Reports    |
|  - 1m / 5m / 15m / 1h / 24h Time-Range Telemetry Filters   - AI Maintenance Copilot Dialog Window |
+---------------------------------------------------------------------------------------------------+
```

---

## ⚡ Hardware Architecture & Wiring Guide

### 1. Sensor & Actuator Pin Assignment Map

The hardware testbed utilizes an **ESP32 DevKit V1 (30-pin or 38-pin)**.

| Component / Subsystem | Function / Measurement | ESP32 Pin | Signal Type | Hardware Wiring & Electrical Notes |
| :--- | :--- | :--- | :--- | :--- |
| **L298N Motor Driver** | ENA (PWM Speed Control) | **GPIO 25** | LEDC PWM | 5 kHz PWM carrier frequency, 8-bit resolution (0–255). Quiet motor operation. |
| **L298N Motor Driver** | IN1 (Direction Forward) | **GPIO 26** | Digital OUT | Logic HIGH for CW rotation; interlocked against concurrent IN1/IN2 conduction. |
| **L298N Motor Driver** | IN2 (Direction Reverse) | **GPIO 27** | Digital OUT | Logic HIGH for CCW rotation. |
| **ACS712 (20A / 5A) #1** | Motor Armature Current | **GPIO 36** (`SENSOR_VP`) | Analog (ADC1_CH0) | Measures motor load current. Scaled via 1kΩ/2kΩ divider to stay within 0–3.3V ADC range. |
| **ACS712 (20A / 5A) #2** | Total System Bus Current | **GPIO 33** | Analog (ADC1_CH5) | Measures total current drawn by motor, driver, and auxiliary logic. |
| **Battery Divider B1** | Cell 1 Voltage Tap | **GPIO 32** | Analog (ADC1_CH4) | 30kΩ / 4.7kΩ precision divider tap (~3.7V – 4.2V nominal). |
| **Battery Divider B2** | Cell 1+2 Voltage Tap | **GPIO 34** | Analog (ADC1_CH6) | 30kΩ / 4.7kΩ precision divider tap (~7.4V – 8.4V). $V_{\text{cell2}} = V_{B2} - V_{B1}$. |
| **Battery Divider B_PACK** | Full 3S Pack Voltage | **GPIO 35** | Analog (ADC1_CH7) | 30kΩ / 4.7kΩ precision divider tap (~11.1V – 12.6V). $V_{\text{cell3}} = V_{B\_PACK} - V_{B2}$. |
| **DS18B20 Temp Probe** | Motor Core / Casing Temp | **GPIO 4** | Digital 1-Wire | Requires a 4.7kΩ pull-up resistor between DATA and 3.3V. Accuracy ±0.5°C. |
| **801S Vibration Sensor** | Mechanical Vibration Shock | **GPIO 39** (`SENSOR_VN`) | Analog (ADC1_CH3) | Measures high-frequency dynamic acceleration amplitude and mechanical eccentricity. |
| **KY-040 Rotary Encoder** | CLK (Phase A) | **GPIO 18** | Digital IN | Hardware interrupt line for rotary knob rotation tracking. |
| **KY-040 Rotary Encoder** | DT (Phase B) | **GPIO 19** | Digital IN | Direction phase evaluation. |
| **KY-040 Rotary Encoder** | SW (Push Button) | **GPIO 23** | Digital IN | Emergency stop / speed zero toggle button. |

> ⚠️ **CRITICAL ELECTRICAL & RF DESIGN RULE**:
> All analog sensor lines are strictly connected to **ADC1 pins** (`GPIO 32, 33, 34, 35, 36, 39`). 
> **Never connect analog sensors to ADC2 on ESP32**, because the ESP32 Wi-Fi peripheral locks and disables the ADC2 multiplexer whenever Wi-Fi is active. ADC1 operates with zero interference during active wireless transmission.

---

### 2. Power Supply & Ground Distribution
1. **3S 18650 Li-ion Pack (11.1V – 12.6V)** connects to L298N `12V / VCC` and `GND`.
2. **Common Ground**: All grounds (Battery Negative, L298N GND, ESP32 GND, Sensor GNDs) **MUST be tied together** to establish a single common reference plane.
3. **ESP32 Power**: Powered via USB cable (recommended for development) or via an external step-down buck converter (5.0V into `VIN`).

---

## 💻 Quickstart & Setup Guide

### Option 1: 1-Click Launch on Windows (Recommended)
This repository includes a 1-click launcher that automatically detects Python, installs any missing dependencies, boots the SCADA bridge, and opens your default web browser:

1. Clone or download this repository:
   ```bash
   git clone https://github.com/Bhavesh6/industrial-equipment-rul.git
   cd industrial-equipment-rul
   ```
2. Double-click **`START_SYSTEM.bat`**.
3. The launcher will automatically start the SCADA server and open **`http://localhost:8000`**.

---

### Option 2: Manual Terminal Execution (Windows / macOS / Linux)

1. **Clone the repository**:
   ```bash
   git clone https://github.com/Bhavesh6/industrial-equipment-rul.git
   cd industrial-equipment-rul
   ```

2. **Create a virtual environment (optional but recommended)**:
   ```bash
   python -m venv .venv
   # Windows:
   .venv\Scripts\activate
   # Linux/macOS:
   source .venv/bin/activate
   ```

3. **Install production dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Launch the SCADA Edge Server**:
   ```bash
   python -u dashboard/serve.py 8000
   ```

5. **Open the SCADA Console**:
   Navigate to **[http://localhost:8000](http://localhost:8000)** in Google Chrome, Microsoft Edge, or Mozilla Firefox.

---

## 🔌 ESP32 Firmware Setup & Flashing (Optional)

> ℹ️ **NOTE**: If your ESP32 is already programmed, **you do NOT need to re-flash it!**
> The SCADA system dynamically synchronizes calibration settings, safety limits, and motor speeds over USB Serial and Wi-Fi UDP.

If you are setting up a brand-new ESP32 board from scratch:

1. Open the **Arduino IDE 2.x**.
2. Install the **esp32 by Espressif Systems** board package in the Boards Manager.
3. Install required libraries from the Library Manager:
   - `OneWire` (by Paul Stoffregen)
   - `DallasTemperature` (by Miles Burton)
4. Open the firmware sketch:
   [`firmware/esp32_motor_scada_node/esp32_motor_scada_node.ino`](file:///c:/Users/GHOST/Desktop/ECG/industrial-equipment-rul/firmware/esp32_motor_scada_node/esp32_motor_scada_node.ino)
5. Select Board: **ESP32 Dev Module**.
6. Select Port: **COM5** (or whichever port your ESP32 enumerates as).
7. Click **Upload**.

---

## 🎛️ SCADA Web Digital Twin Features

The web console is built with a responsive layout featuring an adaptive collapsible sidebar and zero-overlap scaling across all monitor sizes and mobile tablets.

### 1. Operations Overview (`#sec-overview`)
* **Real-Time KPI Rail**: Instant readouts for Health Index (%), Remaining Useful Life (RUL hours), Motor Current (A), Total Current (A), Core Temperature (°C), RMS Vibration ($g$), and Pack Voltage (V).
* **Interactive Health & RUL Trajectory**: Real-time degradation trajectory curves with **1 min, 5 min, 15 min, 1 hr, and 24 hrs** historical time-range filters hydrated from the persistent SQLite database.
* **Top Status Badge**: Shows hardware connection state (`USB COM5` or `Wi-Fi AP 192.168.4.1`), baud rate, UDP port, and wireless signal strength (RSSI).

### 2. Hardware Controls Console (`#sec-controls`)
* **Interactive Rotary Jog Dial**: Interactive 270° dial to set PWM motor speed from 0 to 255 with physical KY-040 hardware knob synchronization.
* **Precision Slider & Speed Presets**: Quick-select presets for **150** (breakaway torque), **180**, **200**, **220**, and **255** (full power).
* **Direction & Motion**: Toggle Forward (CW) or Reverse (CCW) rotation with soft-start slew rate ramp limiting.
* **Emergency Stop (E-Stop)**: Big red physical/software cutoff button and Safety Trip Reset.
* **Virtual BMS Override**: Demo mode toggle to test low-voltage cutoff behavior safely.
* **Automated Speed Sweep**: Runs an automated 150 $\rightarrow$ 255 $\rightarrow$ 0 PWM diagnostic cycle for baseline calibration.
* **Raw Hardware Command Console**: Directly send AT-style commands over the serial/UDP link.

### 3. Calibration & Safety Interlock Studio (`#sec-calibration`)
Full interactive studio allowing engineers to customize all safety protection parameters:
* **Current Limits**: Motor Overcurrent Trip ($I_{\text{max}}$), Total Bus Cutoff, High Current Warning, ACS712 Sensitivity, Zero Offset.
* **Vibration & Shock Dynamics**: Vibration Trip ($g$), ISO 10816-3 Warning Threshold, Good Condition Limit, Kurtosis Shock Limit ($\beta_2$), Radial/Axial Ratio.
* **Thermal Cutoff**: Motor Core Thermal Trip (°C), Warning Threshold, Ambient Reference.
* **Virtual BMS 3S Safety**: Cell Minimum Cutoff floor ($V_{\text{min}}$), Pack Under-Voltage Alarm, Pack Max Cutoff, Max Cell $\Delta V$ Imbalance Trip ($mV$).
* **Actuator Dynamics**: Max PWM clamp, Breakaway Startup PWM floor, Slew Rate Limiter ramp speed ($PWM/100\,\text{ms}$), Slew toggle.
* **AI Prognostics Tuning**: Isolation Forest Anomaly Sensitivity (%), Rolling Decay Window (days), Critical RUL Alarm threshold ($h$).
* **Two-Way Synchronization**: Dual sliders and precision number input fields with instant visual unit badges (`A`, `g`, `°C`, `V`, `mV`, `PWM`, `h`, `d`).
* **Live Automated Watchdog Interlock**: If live telemetry breaches any configured trip limit, the watchdog actively engages an emergency motor shutoff (`STOP`/`ESTOP`) and logs an incident.
* **Storage**: Two-way persistence across `localStorage`, [`config/calibration.json`](file:///c:/Users/GHOST/Desktop/ECG/industrial-equipment-rul/config/calibration.json), and dynamic live hardware command dispatch.

### 4. Technical Maintenance Reports (`#sec-reports`)
* **Time-Filtered PDF Audit Reports**: Generates distinct maintenance PDFs tailored to the selected window (Last 1 Hour, Last 24 Hours, or Full Lifetime History).
* **CSV Telemetry Export**: One-click download of all raw historical time-series data.

### 5. Multi-Channel Waveforms (`#sec-waveforms`)
* Real-time oscilloscope rendering vibration waveform dynamics, electrical current ripple, and battery discharge curves.

### 6. AI Maintenance Copilot (`#sec-copilot`)
* Integrated RAG-based diagnostic assistant trained on **ISO 13374 Condition Monitoring** and motor failure troubleshooting SOPs.

---

## 🧠 Machine Learning & Prognostics Pipeline

The machine learning subsystem implements a multi-model architecture for condition-based maintenance:

```
Raw Telemetry (V, I, T, Vib, RPM) 
       │
       ▼
Feature Engineering Pipeline (33 Features: RMS, Kurtosis, Crest Factor, ΔT, Sag)
       │
       ├─────────────────────────────────┬─────────────────────────────────┐
       ▼                                 ▼                                 ▼
Gradient Boosting Regressor       Random Forest Regressor          Isolation Forest
(RUL Mean Prediction)            (95% Confidence Interval)       (Zero-Day Anomaly Detection)
       │                                 │                                 │
       └────────────────┬────────────────┘                                 │
                        ▼                                                  ▼
             Remaining Useful Life (RUL)                     Anomaly Score & Warning Flags
             "142.8 hours [95% CI: 138.2 - 147.4 h]"
                        │
                        ▼
             SHAP TreeExplainer Attribution
             (Isolates dominant root cause: Thermal vs. Mechanical vs. Electrical)
```

1. **Remaining Useful Life (RUL) Regression**:
   - **Random Forest Pipeline** (`models/rul_rf_pipeline.joblib`): $R^2 = 0.8227$, $\text{RMSE} = \pm 1.331\text{ h}$, $\text{MAE} = \pm 0.989\text{ h}$.
   - **Gradient Boosting Pipeline** (`models/rul_gbr_pipeline.joblib`): $R^2 = 0.8194$, $\text{RMSE} = \pm 1.343\text{ h}$.
   - **Dynamic 95% Confidence Intervals** computed from tree ensemble variance.
2. **Leakage-Free Validation**:
   - Trained on 21,300 run-to-failure snapshots across 120 degradation lifecycles.
   - Evaluated using **GroupKFold** cross-validation grouped strictly by `cycle_id` to guarantee zero data leakage between training and testing folds.
3. **SHAP TreeExplainer**:
   - Calculates exact game-theoretic contributions for each feature in real-time to explain why the health index is degrading.

---

## 🌐 REST API & SCADA Protocol Reference

The Python SCADA server exposes the following HTTP endpoints on port `8000`:

| Method | Endpoint | Description | Payload / Response |
| :--- | :--- | :--- | :--- |
| `GET` | `/api/telemetry` | Retrieves the latest live hardware sensor frame, connection status, and ML prediction. | Returns JSON with `telemetry`, `prediction`, `connected`, `port`. |
| `GET` | `/api/history?limit=N` | Retrieves the last $N$ historical records from the SQLite database. | Returns JSON array of timestamped telemetry frames. |
| `GET` | `/api/calibration` | Reads current calibration parameters and safety trip limits. | Returns JSON containing all active thresholds. |
| `POST` | `/api/calibration` | Saves calibration settings to `config/calibration.json` and syncs hardware over serial/UDP. | JSON payload with updated thresholds. |
| `POST` | `/api/motor/control` | Transmits an actuator control command to the motor driver. | `{"action": "start"|"stop"|"speed"|"reverse"|"estop"|"reset"|"sweep"|"raw_cmd", "value": ...}` |
| `POST` | `/api/wifi/config` | Configures ESP32 Station Wi-Fi credentials over serial. | `{"ssid": "...", "password": "..."}` |
| `POST` | `/api/chat` | Queries the AI Maintenance Copilot RAG assistant. | `{"message": "..."}` $\rightarrow$ returns assistant diagnostic reply. |

---

## 📂 Repository File Structure

```
industrial-equipment-rul/
├── START_SYSTEM.bat              # 1-Click launcher for Windows (auto-installs & starts)
├── INSTALL_DEPENDENCIES.bat      # 1-Click dependency installer
├── requirements.txt              # Python production dependencies manifest
├── README.md                     # Comprehensive architecture, wiring & user manual
│
├── config/
│   └── calibration.json          # Persistent active safety trip & calibration thresholds
│
├── dashboard/                    # SCADA Web Operations Center
│   ├── index.html                # Main Digital Twin Dashboard & UI Studio
│   ├── serve.py                  # SCADA HTTP Server, Serial/UDP Bridge & ML Engine
│   ├── css/
│   │   ├── app.css               # Core layout and styling
│   │   ├── pro.css               # Enterprise PPE design system, responsive rules & calibration styles
│   │   └── fonts.css             # Local typographic definitions
│   └── js/
│       ├── chart.umd.min.js      # High-performance Chart.js 4 library
│       └── lucide.min.js         # Feather-based industrial icon set
│
├── firmware/                     # ESP32 Microcontroller Firmware
│   └── esp32_motor_scada_node/
│       └── esp32_motor_scada_node.ino # FreeRTOS ADC1 sampling, Dual-Transport Serial/UDP & L298N drive
│
├── models/                       # Trained Machine Learning Models
│   ├── rul_rf_pipeline.joblib    # Random Forest Regressor Pipeline
│   ├── rul_gbr_pipeline.joblib   # Gradient Boosting Regressor Pipeline
│   ├── anomaly_iso_forest.joblib # Isolation Forest Anomaly Detector
│   ├── scaler.joblib             # Feature Normalizer
│   └── metrics.json              # Model evaluation metrics & validation scores
│
├── backend/                      # AI Maintenance Assistant
│   └── chatbot.py                # RAG Copilot with ISO 13374 SOP playbooks
│
├── data/                         # Historian Database & Datasets
│   ├── equipment_health.db       # Active SQLite Time-Series Historian
│   ├── baseline_stats.json       # Operating envelopes & safety baselines
│   └── processed/                # 21,300 run-to-failure degradation samples
│
└── src/                          # Core Machine Learning Training Source Code
    ├── data/
    │   └── generate_training_data.py # Physics-informed Weibull degradation generator
    ├── features/
    │   └── health.py             # Feature extraction & Health Index computation
    └── models/
        ├── predict.py            # Real-time inference engine
        └── train.py              # GroupKFold leakage-free model training
```

---

## 📜 Standards & Compliance
* **ISO 10816-3**: Mechanical vibration evaluation standard for industrial rotating machinery.
* **ISO 13374**: Condition monitoring and diagnostics of machine systems (Open System Architecture).
* **JEDEC / IEC 61960**: Secondary lithium cells and battery health monitoring guidelines.

---

## 📄 License
This project is released under the **MIT License**. Feel free to use, modify, and distribute for academic, research, and industrial automation purposes.