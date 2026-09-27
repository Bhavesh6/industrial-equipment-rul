# Project Context

This file records key decisions, assumptions, and context for the industrial equipment health monitoring prototype.

## Key Decisions
- **Prototype motor**: RS‑380 / RP‑380 brushed DC motor (approx. 6000 RPM, 12 V).
- **Sensors**: 
  - Battery voltage (voltage divider)
  - Motor voltage (voltage divider)
  - Total system current (ACS715‑20A module)
  - Motor current (second ACS715‑20A module)
  - Temperature (DS18B20 or thermistor)
  - Vibration (801S analog module)
  - Optional RPM (Hall‑effect or optical encoder)
- **Communication**: ESP32 publishes JSON via Wi‑Fi (MQTT or HTTP POST).
- **Health/RUL method**: Rule‑based health index derived from healthy baseline (no ML training required).
- **Uncertainty**: Prediction interval based on baseline health‑score standard deviation.
- **Explainability**: Per‑sensor contribution to deviation score (SHAP‑like).
- **Dashboard**: Streamlit showing live gauges, trends, health/RUL with interval, feature contributions, and chatbot.
- **Chatbot**: Uses a free LLM API (OpenAI ChatGPT or Google Gemini) with prompt containing current health/RUL/top contributors.
- **Data storage**: SQLite database with `raw_sensor_data` and `features` (or `health_features`) tables.
- **Development philosophy**: Start simple, keep raw data immutable, avoid temporal leakage, version datasets/model metadata.

## Assumptions
- The ESP32 can sample all sensors at ≥ 50 Hz and transmit a compact JSON packet (< 200 bytes) at ≤ 10 Hz without loss.
- Healthy baseline (~2 min) provides stable mean/std for each sensor.
- Nominal lifetime (L₀) for RUL scaling is set to 10 hours for demo purposes; can be adjusted.
- Free LLM API quota is sufficient for intermittent chatbot usage during demos.
- Experimental faults (imbalance, overload, temperature rise) are induced safely and remain within motor mechanical limits.

## Open Questions / Future Work
- Calibration of nominal lifetime L₀ from accelerated life tests.
- Exploration of lightweight ML models (e.g., XGBoost) as alternative health index.
- Integration of OTA firmware updates for ESP32.
- Addition of pressure sensing if a pressure‑related use case emerges.