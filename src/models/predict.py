"""
ML Model Inference Engine — Live SCADA Integration
===================================================
Loads trained joblib pipelines and exposes a clean interface for the
SCADA dashboard (serve.py) to call on every incoming sensor tick.

WHAT THIS REPLACES:
  The old HealthEngine used a manual formula:
    H = 1 - 0.12 * sqrt(Σ wᵢ * Zᵢ²)
  That formula is still used as a FALLBACK if no trained model exists.

WHAT THIS ADDS (REAL ML):
  - GradientBoostingRegressor prediction: model.predict([features])
  - Isolation Forest anomaly score: iso.score_samples([features])
  - 95% CI from Random Forest tree variance (std across estimators)

USAGE (from serve.py or dashboard):
    from src.models.predict import RULPredictor
    predictor = RULPredictor()
    result = predictor.predict(sensor_dict)
    # result = {
    #   "rul_hours": 7.42,
    #   "rul_ci_low": 6.85,
    #   "rul_ci_high": 7.99,
    #   "health_index": 0.814,
    #   "anomaly_score": 0.03,   # 0=normal, 1=anomaly
    #   "model_used": "GradientBoosting",
    #   "status": "WARNING"
    # }
"""

import json
import warnings
from pathlib import Path
from typing import Dict, Any, Optional

import joblib
import numpy as np

warnings.filterwarnings("ignore")

ROOT      = Path(__file__).resolve().parent.parent.parent
MODEL_DIR = ROOT / "models"
DATA_DIR  = ROOT / "data" / "processed"

# RS-380 Baseline (same as HealthEngine — fallback when no model loaded)
BASELINE = {
    "battery_voltage": {"mean": 12.20, "std": 0.12},
    "motor_voltage":   {"mean": 11.80, "std": 0.15},
    "total_current":   {"mean": 2.10,  "std": 0.10},
    "motor_current":   {"mean": 1.85,  "std": 0.08},
    "temperature":     {"mean": 38.00, "std": 1.20},
    "vibration":       {"mean": 0.35,  "std": 0.05},
}
SENSOR_WEIGHTS = {
    "battery_voltage": 0.05, "motor_voltage": 0.15,
    "total_current":   0.05, "motor_current": 0.25,
    "temperature":     0.25, "vibration":     0.25,
}

NOMINAL_LIFETIME_H  = 10.0
FAILURE_THRESHOLD_H = 0.70


class RULPredictor:
    """
    Unified inference interface — tries trained ML models first,
    falls back to rule-based health index if models not yet trained.
    """

    def __init__(self):
        self._gbr_pipe   = None
        self._rf_pipe    = None
        self._iso_forest = None
        self._feature_cols: Optional[list] = None
        self._model_used  = "RuleBased"
        self._load_models()

    # ── Model Loading ──────────────────────────────────────────────────────
    def _load_models(self) -> None:
        """Load all trained model artefacts silently."""
        try:
            gbr_path = MODEL_DIR / "rul_gbr_pipeline.joblib"
            rf_path  = MODEL_DIR / "rul_rf_pipeline.joblib"
            iso_path = MODEL_DIR / "anomaly_iso_forest.joblib"
            meta_path = MODEL_DIR / "metrics.json"

            if not gbr_path.exists():
                return   # Models not trained yet — use fallback

            self._gbr_pipe   = joblib.load(gbr_path)
            self._rf_pipe    = joblib.load(rf_path)
            self._iso_forest = joblib.load(iso_path)
            self._model_used = "GradientBoosting"

            # Load feature column order from training metadata
            if meta_path.exists():
                with open(meta_path) as f:
                    meta = json.load(f)
                self._feature_cols = meta.get("feature_cols", None)

        except Exception as e:
            print(f"[RULPredictor] Model load warning: {e} — using rule-based fallback")
            self._gbr_pipe = None

    @property
    def is_ml_ready(self) -> bool:
        return self._gbr_pipe is not None

    # ── Feature Vector Construction ────────────────────────────────────────
    def _build_feature_vector(self, sensors: Dict[str, float]) -> np.ndarray:
        """
        Build the same feature vector that was used during training.
        For live inference, rolling features = current values (window=1).
        """
        s = sensors
        # Base sensors
        bv  = s.get("battery_voltage", BASELINE["battery_voltage"]["mean"])
        mv  = s.get("motor_voltage",   BASELINE["motor_voltage"]["mean"])
        tc  = s.get("total_current",   BASELINE["total_current"]["mean"])
        mc  = s.get("motor_current",   BASELINE["motor_current"]["mean"])
        tmp = s.get("temperature",     BASELINE["temperature"]["mean"])
        vib = s.get("vibration",       BASELINE["vibration"]["mean"])

        # Derived features
        power_w       = mv * mc
        voltage_ratio = mv / max(bv, 0.1)
        thermal_stress = tmp * mc

        # Rolling features (for single live reading, rolling = current value)
        # Order MUST match training feature_cols from dataset generator
        base_vals = [bv, mv, tc, mc, tmp, vib]
        base_keys = ["battery_voltage", "motor_voltage", "total_current",
                     "motor_current", "temperature", "vibration"]

        feats = list(base_vals)   # base sensors first

        # Rolling RMS = value (window=1), std=0, mean=value, delta=0
        for val in base_vals:
            feats += [val, val, 0.0, 0.0]   # rms, roll_mean, roll_std, delta

        feats += [power_w, voltage_ratio, thermal_stress]

        if self._feature_cols is not None:
            # Re-order to exactly match training column order
            col_map: Dict[str, float] = {}
            for i, k in enumerate(base_keys):
                col_map[k]                    = base_vals[i]
                col_map[f"{k}_rms"]           = base_vals[i]
                col_map[f"{k}_roll_mean"]     = base_vals[i]
                col_map[f"{k}_roll_std"]      = 0.0
                col_map[f"{k}_delta"]         = 0.0
            col_map["power_w"]        = power_w
            col_map["voltage_ratio"]  = voltage_ratio
            col_map["thermal_stress"] = thermal_stress

            feats = [col_map.get(c, 0.0) for c in self._feature_cols]

        return np.array(feats, dtype=np.float64).reshape(1, -1)

    # ── Rule-Based Fallback ────────────────────────────────────────────────
    def _rule_based(self, sensors: Dict[str, float]) -> Dict[str, Any]:
        """Classic weighted Z-score health index (used when ML not trained)."""
        sq_dev = sum(
            SENSOR_WEIGHTS[s] * ((sensors.get(s, BASELINE[s]["mean"]) - BASELINE[s]["mean"])
                                  / BASELINE[s]["std"]) ** 2
            for s in SENSOR_WEIGHTS
        )
        h = float(np.clip(1.0 - 0.12 * np.sqrt(sq_dev), 0.0, 1.0))

        if h > FAILURE_THRESHOLD_H:
            rul = NOMINAL_LIFETIME_H * (h - FAILURE_THRESHOLD_H) / (1.0 - FAILURE_THRESHOLD_H)
        else:
            rul = max(0.0, (h / FAILURE_THRESHOLD_H) * 0.5)

        baseline_h_std = 0.025
        sigma = (NOMINAL_LIFETIME_H / (1.0 - FAILURE_THRESHOLD_H)) * baseline_h_std
        ci_low  = max(0.0, rul - 1.96 * sigma)
        ci_high = max(0.0, rul + 1.96 * sigma)

        return {
            "rul_hours":     round(rul,    2),
            "rul_ci_low":    round(ci_low, 2),
            "rul_ci_high":   round(ci_high, 2),
            "health_index":  round(h,      3),
            "anomaly_score": 0.0,
            "model_used":    "RuleBased",
            "status":        self._status(h),
        }

    # ── ML Inference ───────────────────────────────────────────────────────
    def _ml_predict(self, sensors: Dict[str, float]) -> Dict[str, Any]:
        """Full ML inference — GBR point estimate + RF CI + Isolation Forest."""
        X = self._build_feature_vector(sensors)

        # Point estimate: Gradient Boosting
        rul_pred = float(np.clip(self._gbr_pipe.predict(X)[0], 0.0, NOMINAL_LIFETIME_H * 1.5))

        # Confidence interval: variance across RF trees
        rf_model  = self._rf_pipe.named_steps["model"]
        rf_scaler = self._rf_pipe.named_steps["scaler"]
        X_scaled  = rf_scaler.transform(X)
        tree_preds = np.array([t.predict(X_scaled)[0] for t in rf_model.estimators_])
        ci_std     = float(np.std(tree_preds))
        ci_low     = float(np.clip(rul_pred - 1.96 * ci_std, 0.0, None))
        ci_high    = float(np.clip(rul_pred + 1.96 * ci_std, 0.0, None))

        # Anomaly score: Isolation Forest
        # score_samples: lower = more anomalous; transform to [0, 1] where 1=anomaly
        iso_raw    = float(self._iso_forest.score_samples(X)[0])
        # Normalise: typical range is roughly [-0.5, 0.1]
        anomaly_01 = float(np.clip((iso_raw * -1.0 + 0.0) / 0.6, 0.0, 1.0))

        # Health index (derived from RUL for continuity with HealthEngine)
        h_from_rul = FAILURE_THRESHOLD_H + (rul_pred / NOMINAL_LIFETIME_H) * (1.0 - FAILURE_THRESHOLD_H)
        h = float(np.clip(h_from_rul, 0.0, 1.0))

        return {
            "rul_hours":     round(rul_pred,   2),
            "rul_ci_low":    round(ci_low,     2),
            "rul_ci_high":   round(ci_high,    2),
            "health_index":  round(h,          3),
            "anomaly_score": round(anomaly_01, 3),
            "model_used":    "GradientBoosting",
            "status":        self._status(h),
        }

    # ── Public Interface ───────────────────────────────────────────────────
    def predict(self, sensors: Dict[str, float]) -> Dict[str, Any]:
        """
        Main prediction entry point.
        Call with a dict of raw sensor readings:
            {"motor_current": 1.92, "temperature": 41.3, "vibration": 0.42, ...}
        """
        if self.is_ml_ready:
            try:
                return self._ml_predict(sensors)
            except Exception as e:
                print(f"[RULPredictor] ML inference error: {e} — falling back to rules")

        return self._rule_based(sensors)

    @staticmethod
    def _status(h: float) -> str:
        if h >= 0.85:
            return "HEALTHY"
        elif h >= FAILURE_THRESHOLD_H:
            return "WARNING"
        else:
            return "CRITICAL"
