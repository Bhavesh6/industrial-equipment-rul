"""
Compute SHAP TreeExplainer Metrics & Export Explainer Artefacts
==============================================================
Loads the trained GBR model, calculates global SHAP feature importances
from the run-to-failure dataset, and populates models/metrics.json.
Also serializes the TreeExplainer for real-time live inference.
"""

import json
from pathlib import Path
import joblib
import numpy as np
import pandas as pd
import shap

ROOT = Path(__file__).resolve().parent.parent
MODEL_DIR = ROOT / "models"
DATA_PATH = ROOT / "data" / "processed" / "run_to_failure.csv"
METRICS_PATH = MODEL_DIR / "metrics.json"

def main():
    print("[SHAP] Loading dataset and model pipelines...")
    df = pd.read_csv(DATA_PATH)
    
    with open(METRICS_PATH, "r") as f:
        meta = json.load(f)
    feature_cols = meta["feature_cols"]

    pipe = joblib.load(MODEL_DIR / "rul_gbr_pipeline.joblib")
    model = pipe.named_steps["model"]
    scaler = pipe.named_steps["scaler"]

    X = df[feature_cols].values
    X_scaled = scaler.transform(X)

    print(f"[SHAP] Initializing TreeExplainer on GradientBoostingRegressor...")
    explainer = shap.TreeExplainer(model)

    # Subsample 1500 rows for global baseline SHAP summary
    sample_size = min(1500, len(X_scaled))
    rng = np.random.default_rng(42)
    sample_idx = rng.choice(len(X_scaled), sample_size, replace=False)
    X_sample = X_scaled[sample_idx]

    print(f"[SHAP] Computing Tree SHAP values on {sample_size} samples...")
    shap_vals = explainer.shap_values(X_sample)

    mean_abs_shap = np.abs(shap_vals).mean(axis=0)
    shap_dict = {
        feature_cols[i]: round(float(mean_abs_shap[i]), 6)
        for i in range(len(feature_cols))
    }

    # Sensor-level rollup
    core_sensors = [
        "vibration", "temperature", "motor_current",
        "total_current", "motor_voltage", "battery_voltage"
    ]
    sensor_shap = {}
    for s in core_sensors:
        s_total = sum(v for k, v in shap_dict.items() if k.startswith(s))
        sensor_shap[s] = round(float(s_total), 6)

    # Also compute relative percentage breakdown
    total_shap_sum = sum(sensor_shap.values()) or 1.0
    sensor_shap_pct = {
        s: round((val / total_shap_sum) * 100.0, 1)
        for s, val in sensor_shap.items()
    }

    print("[SHAP] Global Sensor-Level Attribution:")
    for s, pct in sorted(sensor_shap_pct.items(), key=lambda x: -x[1]):
        print(f"  {s:20s}: {pct}% (|SHAP| = {sensor_shap[s]:.4f})")

    meta["shap_summary"] = {
        "feature_level": shap_dict,
        "sensor_level": sensor_shap,
        "sensor_level_pct": sensor_shap_pct,
        "sample_size": sample_size
    }

    with open(METRICS_PATH, "w") as f:
        json.dump(meta, f, indent=2)
    print(f"[SHAP] Successfully updated {METRICS_PATH}")

    # Save explainer
    explainer_path = MODEL_DIR / "shap_explainer.joblib"
    joblib.dump(explainer, explainer_path, compress=3)
    print(f"[SHAP] Saved TreeExplainer to {explainer_path}")

if __name__ == "__main__":
    main()
