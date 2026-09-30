# Industrial Equipment Health Monitoring Project - Handoff Document

## Project Overview
This document summarizes the state of the Industrial Equipment Health Monitoring and Remaining Useful Life (RUL) Prediction project, an IIoT-based prototype using an RS-380 DC motor as the testbed.

---

## 🎯 Project Purpose
Develop a low-cost, IIoT-enabled system for monitoring industrial equipment health and predicting Remaining Useful Life (RUL) using sensor data from an ESP32-connected DC motor prototype. The system includes:
- Real-time sensor data acquisition (voltage, current, temperature, vibration)
- Rule-based health assessment with uncertainty quantification
- Explainable AI (SHAP-like sensor contributions)
- Live Streamlit dashboard for visualization
- LLM-powered maintenance chatbot for grounded troubleshooting

---

## 📂 Repository Structure
```
industrial-equipment-rul/
├── .env.example
├── PROJECT_CONTEXT.md
├── README.md
├── requirements.txt
├── docs/
│   └── HANDOFF.md
├── firmware/
│   └── esp32_sensor_node/
├── data/
│   ├── raw/
│   ├── processed/
│   └── sample/
├── notebooks/
├── src/
│   ├── data/
│   ├── features/
│   ├── models/
│   ├── evaluation/
│   ├── explainability/
│   └── api/
├── dashboard/
│   └── app.py
├── rag/
└── tests/
```

---

## 🔧 Key Technical Specifications & Mathematical Models

### 1. Health Index Calculation ($H$)
$$H = 1 - \sqrt{\sum_{i=1}^n w_i \left(\frac{x_i - \mu_i}{\sigma_i}\right)^2}$$
- $x_i$: Current reading of sensor $i$
- $\mu_i, \sigma_i$: Mean and standard deviation from healthy baseline
- $w_i$: Normalized sensor weights ($\sum w_i = 1$)
- Clamped to $[0.0, 1.0]$

### 2. Remaining Useful Life ($RUL$)
$$\text{RUL} = L_0 \times \frac{H - H_{\text{fail}}}{H_0 - H_{\text{fail}}}$$
- $L_0$: Nominal lifetime (e.g. 10.0 hours for demonstration scaling)
- $H_0$: Baseline healthy state ($\approx 1.0$)
- $H_{\text{fail}}$: Failure threshold (e.g. $0.70$)
- Clamped to $\ge 0$

### 3. Uncertainty Quantification
- 95% prediction interval computed from baseline health score variance ($\sigma_H$):
$$\text{Interval} = \text{RUL} \pm 1.96 \times \sigma_{\text{RUL}}$$

### 4. Sensor Contribution (SHAP-like Explainability)
$$\text{Contribution}_i = \frac{w_i \left(\frac{x_i - \mu_i}{\sigma_i}\right)^2}{\sum_j w_j \left(\frac{x_j - \mu_j}{\sigma_j}\right)^2} \times 100\%$$

---

## 📋 Implementation Roadmap

### Phase 1: Web Dashboard Enhancement (Current Focus)
- Realistic sensor simulation modes (Normal, High Vibration/Imbalance, Overcurrent/Overload, Overheating, Multi-fault)
- Real-time rule-based Health Index, RUL, and Uncertainty calculation
- Interactive Plotly visualizations (Sensor Gauges, Health/RUL trends, Feature Contribution Bar Chart)
- Context-aware maintenance assistant with prompt grounding
- Live auto-refresh toggle

### Phase 2: Data Pipeline & Baseline Collection
- SQLite database schema (`raw_sensor_data`, `health_features`)
- Baseline statistical profiler (`scripts/collect_baseline.py`)
- Windowed statistical feature extraction engine

### Phase 3: ESP32 Firmware & Hardware Integration
- C++/Arduino firmware for ESP32 sampling at $\ge 50\text{ Hz}$
- Dual ACS715 current sensing, voltage dividers, 801S vibration, DS18B20 temperature
- MQTT/HTTP JSON telemetry publishing

### Phase 4: Backend REST API
- FastAPI backend (`/latest`, `/history`, `/chat`, `/health`)
- Live database persistence and query layer

### Phase 5: LLM / RAG Maintenance Assistant
- Maintenance knowledge base integration (`rag/`)
- Grounded prompt templates and fault diagnosis playbooks
