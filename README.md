# Industrial Equipment Health Monitoring & RUL Prediction SCADA System
### *Real-Time Digital Twin, Machine Learning Prognostics & IoT Telemetry for RS-380 DC Motors*

---

## 📌 Executive Summary

This project is an industrial-grade **IIoT Predictive Maintenance and Remaining Useful Life (RUL) Prognostics System** designed for electromechanical drive equipment (specifically the RS-380 / RP-380 brushed DC motor testbed). 

It bridges physical hardware telemetry acquired by an **ESP32 microcontroller** with a **Python SCADA edge server**, an **ensemble of Machine Learning models** (Gradient Boosting + Random Forest 95% CI + Isolation Forest + SHAP Explainability), a persistent **SQLite time-series historian**, a **Virtual Battery Management System (BMS)**, and a modern **web-based SCADA Digital Twin console** featuring an **AI Maintenance Copilot**.

```
+---------------------------------------------------------------------------------------------------+
|                                  PHYSICAL HARDWARE TESTBED                                        |
|  RS-380 Brushed DC Motor  |  3S 18650 Li-ion Pack (12.6V)  |  L298N Dual H-Bridge Driver          |
|  Dual ACS712 Current Sens |  DS18B20 Digital Temp Probe     |  801S Analog Vibration Accelerometer |
+---------------------------------------------------------------------------------------------------+
                                                │
                                    (Analog / 1-Wire / GPIO)
                                                ▼
+---------------------------------------------------------------------------------------------------+
|                                   ESP32 SENSOR NODE (MCU)                                         |
|  - 12-bit ADC1 Sampling (FreeRTOS)                         - PWM Speed & Direction Control        |
|  - Simultaneous Dual-Transport Streaming:                                                         |
|       * High-Speed USB Serial (115,200 baud)               * Wireless Wi-Fi UDP Broadcast (:8888)  |
+---------------------------------------------------------------------------------------------------+
                                                │
                                     (USB Serial / UDP Wi-Fi)
                                                ▼
+---------------------------------------------------------------------------------------------------+
|                               PYTHON SCADA EDGE SERVER & BACKEND                                  |
|  - Real-Time Serial/UDP Bridge (`dashboard/serve.py`)      - SQLite Historian (`equipment_health`) |
|  - Health Index Fusion Engine (0.0 - 1.0)                  - Virtual BMS Safety Interlock         |
|  - ML Pipeline: GBR + RF Regressor (R²=0.82)               - Anomaly Detection: Isolation Forest  |
|  - SHAP TreeExplainer Degradation Attribution              - AI Copilot: ISO 13374 RAG Engine     |
+---------------------------------------------------------------------------------------------------+
                                                │
                                     (REST APIs & WebSockets)
                                                ▼
+---------------------------------------------------------------------------------------------------+
|                                  SCADA WEB DIGITAL TWIN CONSOLE                                   |
|  - Live Oscilloscopes & Gauges (Chart.js 4 + Lucide)       - Remaining Useful Life (RUL) Gauge    |
|  - 3S Battery Cell Telemetry (Cell 1, 2, 3)                - Motor Speed & E-Stop Controls        |
|  - SHAP Feature Impact Visualizer                          - PDF / DOCX Technical Audit Reports   |
+---------------------------------------------------------------------------------------------------+
```

---

## ⚡ How Everything Works: Complete System Breakdown

### 1. Hardware Architecture & Sensor Array
The physical hardware rig consists of an **RS-380 brushed DC motor** driven under varying dynamic loads and powered by a **3S Lithium-Ion battery pack** (nominal 11.1 V, fully charged 12.6 V).

| Sensor / Module | Physical Function | ESP32 Pin | Signal Type | Calibration & Notes |
| :--- | :--- | :--- | :--- | :--- |
| **L298N Dual H-Bridge** | PWM motor speed control & directional H-bridge drive | GPIO 25 (ENA)<br>GPIO 26 (IN1)<br>GPIO 27 (IN2) | 5 kHz LEDC PWM | Frequency: 5,000 Hz, 8-bit resolution (0–255). High-frequency prevents audible coil whine. |
| **ACS712 (20A / 5A) #1** | Motor Armature Current | GPIO 36 (`SENSOR_VP`) | Analog (ADC1_CH0) | Calibrated zero-current baseline: 1.139 V via resistive voltage divider. Detects motor stall and armature overload. |
| **ACS712 (20A / 5A) #2** | Total Bus Current | GPIO 33 | Analog (ADC1_CH5) | Measures total power draw including motor, driver, and MCU logic. |
| **Battery Divider B1** | Battery Cell 1 Tap | GPIO 32 | Analog (ADC1_CH4) | 30kΩ / 4.7kΩ precision voltage divider (~3.7 V – 4.2 V). |
| **Battery Divider B2** | Battery Cell 1+2 Tap | GPIO 34 | Analog (ADC1_CH6) | 30kΩ / 4.7kΩ precision divider (~7.4 V – 8.4 V). Cell 2 voltage = $V_{B2} - V_{B1}$. |
| **Battery Divider B_PACK** | Full 3S Pack Voltage | GPIO 35 | Analog (ADC1_CH7) | 30kΩ / 4.7kΩ precision divider (~11.1 V – 12.6 V). Cell 3 voltage = $V_{PACK} - V_{B2}$. |
| **DS18B20 Sensor** | Motor Casing Temperature | GPIO 4 | Digital 1-Wire | 4.7 kΩ pull-up resistor. Accurate to ±0.5°C across −10°C to +85°C. |
| **801S Vibration Sensor** | Dynamic High-Frequency Shock & Vibration | GPIO 39 (`SENSOR_VN`) | Analog (ADC1_CH3) | Measures mechanical vibration amplitude and eccentricity. |
| **KY-040 Rotary Encoder** | Manual Speed & Emergency Override | GPIO 18 (CLK)<br>GPIO 19 (DT)<br>GPIO 23 (SW) | Digital Interrupts | Physical hardware knob for manual RPM dial-in and push-to-stop. |

> **Critical Design Engineering Note**: All analog sensor inputs are strictly connected to **ADC1** channels (`GPIO 32, 33, 34, 35, 36, 39`). This guarantees that active Wi-Fi operation does not cause ADC lockouts or channel conflicts (which occurs if ADC2 is used while Wi-Fi is active).

---

### 2. Firmware Implementation (`firmware/esp32_sensor_node/`)
The ESP32 firmware executes a high-speed telemetry pipeline:
1. **Concurrent Dual-Transport Streaming**:
   - **USB Serial Telemetry**: Streams structured JSON frames at **115,200 baud** directly to the host computer.
   - **Wireless Wi-Fi UDP Broadcast**: Streams concurrent telemetry packets over **UDP port 8888** at 5–10 Hz with sub-5ms latency. Can operate in standalone SoftAP mode (`RS380-SCADA-WIFI`, IP: `192.168.4.1`) or Station mode.
2. **Virtual BMS Undervolt Interlock**:
   - Continuously monitors Individual Cell Voltages ($V_{cell1}, V_{cell2}, V_{cell3}$).
   - If any individual cell drops below **3.00 V** or the total pack drops below **9.00 V**, the firmware triggers an immediate safety shutdown to prevent irreversible lithium cell damage.
3. **Smooth PWM Slew-Rate Acceleration**:
   - Prevents abrupt in-rush current spikes when starting the motor or stepping up speed, protecting the motor commutators and H-bridge transistors.

---

### 3. Backend & SCADA Architecture (`dashboard/serve.py`)
The backend is a high-performance Python 3 SCADA server providing REST APIs, hardware communication bridges, and real-time ML inference:
- **Serial Bridge**: Automatically connects to the ESP32 on `COM5` (configurable) at 115,200 baud with auto-reconnection and exponential backoff.
- **UDP Listener**: Listens on UDP port `8888` for wireless telemetry packets.
- **Fallback Simulation Engine**: If hardware is disconnected, the server seamlessly generates physics-accurate synthetic degradation telemetry so development, demonstration, and evaluation never stall.
- **Persistent Data Historian (`data/equipment_health.db`)**: Logs sensor readings at 1 Hz into SQLite tables (`telemetry_history`, `alerts_log`, `motor_events`) for long-term auditability.

---

### 4. Machine Learning & RUL Prognostics Pipeline
The machine learning subsystem implements a multi-model architecture for condition-based maintenance:

```
Raw Telemetry (V, I, T, Vib, RPM) 
       │
       ▼
Feature Engineering Pipeline (33 Features: RMS, Std, Δ, Power, Thermal Stress)
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
   - **Uncertainty Quantification**: Calculates dynamic 95% Confidence Intervals from the ensemble tree variance.
2. **Leakage-Free Validation**:
   - Trained on 21,300 run-to-failure snapshots across 120 degradation lifecycles.
   - Evaluated using **GroupShuffleSplit** and 5-fold **GroupKFold** cross-validation grouped strictly by lifecycle cycle (`cycle_id`), preventing temporal data leakage.
3. **SHAP (SHapley Additive exPlanations)**:
   - Uses `shap.TreeExplainer` to calculate exact mathematical game-theoretic contributions for each feature in real-time, explaining **why** the motor's health index is decreasing.
4. **AI Prognostics Copilot (`backend/chatbot.py`)**:
   - Context-grounded Retrieval-Augmented Generation (RAG) assistant referencing **ISO 13374 Condition Monitoring standards** and mechanical engineering maintenance SOPs.

---

## 💻 1-Click Handover & Setup Guide (For Any Laptop)

This project has been packaged so that **anyone on any Windows computer can set up and run the entire project with a single click**, without manually installing Python libraries or typing terminal commands.

### Option 1: 1-Click Automatic Run (Recommended)
1. Download or clone this repository to the computer.
2. Double-click **`START_SYSTEM.bat`**.
3. The script will:
   - Detect Python automatically.
   - Automatically install all required libraries from `requirements.txt` if missing.
   - Start the SCADA server and hardware connection.
   - Automatically launch the browser at **`http://localhost:8000`**.

### Option 2: Pre-Install Dependencies Only
- Double-click **`INSTALL_DEPENDENCIES.bat`** to install all required libraries in one click.

### Option 3: Manual Terminal Command
```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Start the SCADA Server
python dashboard/serve.py 8000
```
Open **[http://localhost:8000](http://localhost:8000)** in Google Chrome, Microsoft Edge, or any modern web browser.

---

## 🌐 Public Live Demonstration (Zero Setup Required)

If you need to show the complete working project to evaluators, clients, or stakeholders **without them touching code or installing anything**, you can share the active Cloudflare Tunnel URL:

🔗 **Live SCADA Web Dashboard**: `https://pine-impose-turning-alexandria.trycloudflare.com`

- Real-time live sensor feeds and telemetry streaming.
- Real-time RUL countdown and health index gauge.
- Full 3S battery pack cell monitoring (Cell 1, 2, 3) and Virtual BMS status.
- Interactive AI Maintenance Copilot.
- One-click exportable PDF & DOCX Technical Audit Reports.

---

## 🔒 Intellectual Property, Security & Repository Privacy Notice

### How to Protect Your Code on GitHub:
1. **GitHub Repository Visibility**:
   - If your GitHub repository is currently **Public**, anyone with the link can clone and copy all source code, models, and data.
   - **To make it Private immediately**:
     1. Go to your repository on GitHub.
     2. Click **Settings** (top right tab).
     3. Scroll down to the bottom **Danger Zone**.
     4. Click **Change repository visibility** &rarr; Select **Make private**.
     5. Type your repository name to confirm.
   - *Once private, only you (and people you explicitly invite as Collaborators) can see, clone, or download the repository.*

2. **Demonstrating Without Giving Code**:
   - Use the **Live Cloudflare link** above to demonstrate the full application. Evaluators can test and verify all functionality live in their browser while your code and models remain 100% secure on your computer.

3. **Packaging as Standalone Binary (`.exe`)**:
   - If an evaluator needs to run the project offline on their laptop without viewing the raw Python source code, the server can be bundled into a compiled executable using `pyinstaller --onefile dashboard/serve.py`.

---

## 📂 Project Directory Structure

```
industrial-equipment-rul/
├── START_SYSTEM.bat              # 1-Click launcher for Windows (auto-installs & runs)
├── INSTALL_DEPENDENCIES.bat      # 1-Click dependency installer
├── requirements.txt              # Production Python package manifest
├── README.md                     # Comprehensive project documentation & architecture guide
│
├── dashboard/                    # SCADA Web Operations Center
│   ├── index.html                # Main Digital Twin Dashboard (Single RS-380 Testbed)
│   ├── serve.py                  # SCADA HTTP Server, Serial/UDP Bridge & ML Engine
│   ├── css/                      # Industrial SCADA UI stylesheets (app.css, pro.css)
│   └── js/                       # Charting, WebSocket handlers & Lucide icons
│
├── firmware/                     # ESP32 Microcontroller Firmware
│   └── esp32_sensor_node/
│       └── esp32_sensor_node.ino # Multi-Sensor sampling, Dual-Transport Serial/UDP & BMS
│
├── models/                       # Serialized Machine Learning Pipelines
│   ├── rul_rf_pipeline.joblib    # Random Forest Regressor Pipeline
│   ├── rul_gbr_pipeline.joblib   # Gradient Boosting Regressor Pipeline
│   ├── anomaly_iso_forest.joblib # Isolation Forest Anomaly Model
│   ├── scaler.joblib             # Feature Normalizer
│   └── metrics.json              # Model evaluation metrics & validation benchmarks
│
├── backend/                      # AI Maintenance Assistant
│   └── chatbot.py                # RAG Copilot with ISO 13374 SOP playbooks
│
├── data/                         # Data Historian & Datasets
│   ├── equipment_health.db       # Active SQLite Time-Series Historian
│   ├── baseline_stats.json       # Operating envelopes & safety thresholds
│   └── processed/                # 21,300 run-to-failure degradation samples
│
└── src/                          # Core Machine Learning Source Code
    ├── data/
    │   └── generate_training_data.py # Physics-informed Weibull degradation generator
    ├── features/
    │   └── health.py             # Feature extraction & Health Index computation
    └── models/
        ├── predict.py            # Real-time inference engine
        └── train.py              # GroupKFold leakage-free model training
```

---

## ⚖️ Legal Notice & Copyright

**Copyright &copy; 2026 Bhavesh & Authors. All Rights Reserved.**

This software, its machine learning architectures, firmware algorithms, and datasets constitute proprietary intellectual property. Unauthorized copying, distribution, decompilation, public re-hosting, or uncredited academic submission of this codebase without express written authorization is strictly prohibited.