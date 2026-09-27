# Industrial Equipment Health Monitoring & RUL Prediction

College‑level prototype for IIoT‑based health monitoring and Remaining Useful Life (RUL) prediction of a small DC motor (RS‑380) using sensor data from an ESP32.

## Features
- Dual current sensing (system & motor)  
- Voltage, temperature, vibration sensing  
- Rule‑based health index & RUL with uncertainty  
- SHAP‑like explainability (sensor contributions)  
- Live dashboard (Streamlit)  
- Maintenance chatbot powered by a free LLM API (OpenAI/Google)  
- Experimental fault demonstrations (imbalance, overload, temperature)

## Repository Structure
```
industrial-equipment-rul/
├── README.md
├── PROJECT_CONTEXT.md
├── requirements.txt
├── .env.example
├── docs/
│   ├── project_architecture.md
│   ├── dataset_notes.md
│   ├── hardware_wiring.md
│   └── experiments.md
├── firmware/
│   └── esp32_sensor_node/
├── data/
│   ├── raw/
│   ├── processed/
│   └── sample/
├── notebooks/
│   ├── 01_dataset_exploration.ipynb
│   ├── 02_preprocessing.ipynb
│   ├── 03_feature_engineering.ipynb
│   ├── 04_model_training.ipynb
│   └── 05_shap_and_uncertainty.ipynb
├── src/
│   ├── data/
│   ├── features/
│   ├── models/
│   ├── evaluation/
│   ├── explainability/
│   └── api/
├── models/
├── dashboard/
├── rag/
└── tests/
```

## Getting Started
1. Clone the repo and navigate to the root folder.  
2. Install Python dependencies: `pip install -r requirements.txt`  
3. Copy `.env.example` to `.env` and fill in your free LLM API key (OpenAI or Google).  
4. Run the baseline data collection script: `python scripts/collect_baseline.py`  
5. Start the backend API: `uvicorn src.api.main:app --reload` (or `python -m src.api.main`)  
6. Launch the dashboard: `streamlit run dashboard/app.py`  
7. Flash the ESP32 firmware (`firmware/esp32_sensor_node/main.ino`) and ensure it publishes MQTT/HTTP data.  

## License
This project is for educational purposes only.