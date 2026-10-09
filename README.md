# Industrial Equipment Health Monitoring & RUL Prediction

An industrial-grade IIoT predictive maintenance and Remaining Useful Life (RUL) prognostics system for small electromechanical equipment (RS-380 / RP-380 brushed DC motors). Connects ESP32 multi-sensor telemetry to a machine learning edge engine and real-time SCADA digital dashboard.

---

## ⚡ Key Highlights & ML Architecture

- **Machine Learning Prognostics**:
  - **Random Forest Regressor** ($R^2 = 0.8227$, $\text{RMSE} = \pm 1.331\text{ hours}$, $\text{MAE} = \pm 0.989\text{ hours}$)
  - **Gradient Boosting Regressor** ($R^2 = 0.8194$, $\text{RMSE} = \pm 1.343\text{ hours}$)
  - **Isolation Forest** unsupervised anomaly detector for zero-day fault signature detection.
- **Leakage-Free Validation**:
  - `GroupShuffleSplit` & 5-fold `GroupKFold` cross-validation grouped strictly by **motor lifecycle unit** (`cycle_id`), preventing temporal data leakage across degradation cycles.
- **33 Engineered Signal Features**:
  - Rolling window Root-Mean-Square (RMS), standard deviation, rate-of-change ($\Delta$), electrical power ($P = V \cdot I$), voltage efficiency ratio, and thermal-stress interaction terms.
- **Real-Time SCADA Digital Dashboard**:
  - 13 electrical channels, 4S LiPo battery cell balancing, live telemetry oscilloscope feeds, and acoustic alert limits.
- **GenAI Maintenance Copilot**:
  - Context-grounded technical root cause analysis (RCA) and SOP playbooks powered by Google Gemini, Groq, and offline heuristic fallbacks.

---

## 📊 Model Evaluation Benchmarks

Trained on 21,300 multi-sensor snapshots across 120 run-to-failure lifecycles (calibrated using Weibull wear-out lifetime distributions $\beta = 3.5, \eta = 10\text{h}$ and 4 fault modes: Healthy Aging, Mechanical Overload, Rotor Imbalance, and Thermal Runaway).

| Model | 5-Fold CV $R^2$ | 5-Fold CV RMSE | Test $R^2$ | Test RMSE | Test MAE |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **Random Forest Regressor** | **0.7326** | **±1.641 h** | **0.8227** | **±1.331 h** | **±0.989 h** |
| **Gradient Boosting Regressor** | 0.7248 | ±1.664 h | 0.8194 | ±1.343 h | ±1.006 h |
| **Isolation Forest (Anomaly)** | — | — | Contamination: 0.05 | — | — |

Model weights and feature scalers are serialized to [`models/`](models/):
- `rul_rf_pipeline.joblib` (Random Forest scikit-learn Pipeline with StandardScaler)
- `rul_gbr_pipeline.joblib` (Gradient Boosting scikit-learn Pipeline with StandardScaler)
- `anomaly_iso_forest.joblib` (Isolation Forest anomaly model)
- `scaler.joblib` (Feature normalizer)
- `metrics.json` (Full validation metrics and feature importance rankings)

---

## 🛠️ Hardware & Telemetry Channels

| Sensor Module | Signal Name | Engineering Unit | Physical Pin / Bus |
| :--- | :--- | :--- | :--- |
| **ACS715 (20A)** #1 | `motor_current` | Amperes (A) | ESP32 ADC1 |
| **ACS715 (20A)** #2 | `total_current` | Amperes (A) | ESP32 ADC1 |
| **Precision Divider** #1 | `battery_voltage` | Volts (V) | ESP32 ADC1 |
| **Precision Divider** #2 | `motor_voltage` | Volts (V) | ESP32 ADC1 |
| **DS18B20 / NTC** | `temperature` | Celsius (°C) | OneWire / GPIO |
| **801S Module** | `vibration` | g-force (g) | ESP32 ADC2 / Comparator |

---

## 📁 Repository Structure

```
industrial-equipment-rul/
├── backend/
│   └── chatbot.py            # Multi-tier Gemini & Groq maintenance copilot
├── dashboard/
│   ├── css/                  # Industrial SCADA UI styling
│   ├── js/                   # Telemetry charts and chatbot frontend
│   ├── index.html            # Main SCADA operations center
│   └── serve.py              # Server with /api/predict, /api/model-info, /api/chat
├── data/
│   ├── baseline_stats.json   # Healthy motor operating envelope stats
│   ├── schema.sql            # Telemetry SQLite schema
│   └── processed/            # Run-to-failure dataset (21,300 samples)
├── models/
│   ├── rul_rf_pipeline.joblib
│   ├── rul_gbr_pipeline.joblib
│   ├── anomaly_iso_forest.joblib
│   ├── scaler.joblib
│   └── metrics.json
├── src/
│   ├── data/
│   │   └── generate_training_data.py # Physics-informed Weibull degradation generator
│   ├── features/
│   │   └── health.py         # Health index & ML engine bridge
│   └── models/
│       ├── predict.py        # Real-time inference engine
│       └── train.py          # Leakage-free GroupShuffleSplit ML training
├── run_training.py           # Single-command end-to-end dataset generation & training
├── requirements.txt          # Python dependencies
└── README.md
```

---

## 🚀 Quick Start

### 1. Installation
```bash
git clone https://github.com/Bhavesh6/industrial-equipment-rul.git
cd industrial-equipment-rul
pip install -r requirements.txt
```

### 2. Retrain ML Models (Optional)
To regenerate run-to-failure trajectories and retrain the tree ensembles from scratch:
```bash
python run_training.py
```

### 3. Launch the SCADA Dashboard & Edge API
```bash
python dashboard/serve.py 8000
```
Open **[http://localhost:8000](http://localhost:8000)** in your browser.

### 4. Test Live ML Inference
```bash
# Query model metrics
curl http://localhost:8000/api/model-info

# Run real-time RUL inference
curl -X POST http://localhost:8000/api/predict \
  -H "Content-Type: application/json" \
  -d '{"telemetry": {"motor_current": 2.4, "temperature": 48.5, "vibration": 0.85, "motor_voltage": 11.2, "battery_voltage": 11.9, "total_current": 2.8}}'
```

---

## 📜 License
This project is open-source under the MIT License for educational and industrial research.