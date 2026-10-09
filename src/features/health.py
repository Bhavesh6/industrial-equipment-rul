"""
Health Index, RUL, Uncertainty Quantification, and Explainability Engine
========================================================================
Integrates trained Machine Learning pipelines (Gradient Boosting & Random Forest)
for Remaining Useful Life (RUL) prediction, Isolation Forest anomaly scoring,
and per-sensor diagnostic attribution against the RS-380 healthy baseline.
"""

import json
import os
from typing import Dict, Any, Optional
import numpy as np

# Import ML inference engine
try:
    from src.models.predict import RULPredictor
except ImportError:
    try:
        from models.predict import RULPredictor
    except ImportError:
        RULPredictor = None


class HealthEngine:
    """
    Computes Health Index (H), Remaining Useful Life (RUL) with 95% Confidence Bounds,
    and Feature Contribution (Explainability) using trained ML models or baseline heuristics.
    """

    def __init__(self, baseline_config_path: str = None):
        if baseline_config_path and os.path.exists(baseline_config_path):
            with open(baseline_config_path, "r") as f:
                config = json.load(f)
            self.sensors = config.get("sensors", {})
            self.nominal_lifetime = config.get("nominal_lifetime_hours", 10.0)
            self.failure_threshold = config.get("failure_threshold_h", 0.70)
        else:
            # Default baseline statistics
            self.sensors = {
                "battery_voltage": {"mean": 12.20, "std": 0.12, "weight": 0.05},
                "motor_voltage":   {"mean": 11.80, "std": 0.15, "weight": 0.15},
                "total_current":   {"mean": 2.10,  "std": 0.10, "weight": 0.05},
                "motor_current":   {"mean": 1.85,  "std": 0.08, "weight": 0.25},
                "temperature":     {"mean": 38.00, "std": 1.20, "weight": 0.25},
                "vibration":       {"mean": 0.35,  "std": 0.05, "weight": 0.25},
            }
            self.nominal_lifetime = 10.0
            self.failure_threshold = 0.70

        self.h_initial = 1.0
        self.baseline_h_std = 0.025

        # Initialize ML Predictor
        self.ml_predictor = RULPredictor() if RULPredictor is not None else None

    def evaluate(self, readings: Dict[str, float]) -> Dict[str, Any]:
        """
        Calculates health metrics given a dictionary of raw sensor readings.
        Uses trained ML pipeline (GradientBoosting / RF) when available,
        falling back to rule-based formulas.
        """
        weighted_sq_deviations = {}
        total_weighted_sq_dev = 0.0

        for sensor, params in self.sensors.items():
            x_i = readings.get(sensor, params["mean"])
            mu_i = params["mean"]
            sigma_i = params["std"]
            w_i = params["weight"]

            z_sq = ((x_i - mu_i) / sigma_i) ** 2
            weighted_dev = w_i * z_sq
            weighted_sq_deviations[sensor] = weighted_dev
            total_weighted_sq_dev += weighted_dev

        rms_deviation = float(np.sqrt(total_weighted_sq_dev))

        # Check ML prediction first
        ml_res = None
        if self.ml_predictor and self.ml_predictor.is_ml_ready:
            try:
                ml_res = self.ml_predictor.predict(readings)
            except Exception as e:
                ml_res = None

        if ml_res:
            health_index = ml_res["health_index"]
            rul_hours = ml_res["rul_hours"]
            rul_ci_low = ml_res["rul_ci_low"]
            rul_ci_high = ml_res["rul_ci_high"]
            anomaly_score = ml_res.get("anomaly_score", 0.0)
            model_used = ml_res.get("model_used", "GradientBoosting")
        else:
            # Rule-based fallback
            health_index = float(max(0.0, min(1.0, 1.0 - (rms_deviation * 0.12))))
            if health_index > self.failure_threshold:
                rul_fraction = (health_index - self.failure_threshold) / (self.h_initial - self.failure_threshold)
                rul_hours = max(0.0, self.nominal_lifetime * rul_fraction)
            else:
                rul_hours = max(0.0, (health_index / self.failure_threshold) * 0.5)

            sigma_rul = (self.nominal_lifetime / (self.h_initial - self.failure_threshold)) * self.baseline_h_std
            rul_ci_low = max(0.0, rul_hours - 1.96 * sigma_rul)
            rul_ci_high = max(0.0, rul_hours + 1.96 * sigma_rul)
            anomaly_score = float(min(1.0, rms_deviation * 0.2))
            model_used = "RuleBasedFallback"

        # Sensor attribution percentages
        contributions = {}
        if total_weighted_sq_dev > 0:
            for sensor, dev in weighted_sq_deviations.items():
                contributions[sensor] = round((dev / total_weighted_sq_dev) * 100.0, 1)
        else:
            equal_pct = round(100.0 / len(self.sensors), 1)
            for sensor in self.sensors:
                contributions[sensor] = equal_pct

        top_contributor = max(contributions, key=contributions.get)

        # State label
        if health_index >= 0.85:
            status_label = "HEALTHY"
        elif health_index >= self.failure_threshold:
            status_label = "WARNING"
        else:
            status_label = "CRITICAL"

        return {
            "health_index": round(health_index, 3),
            "rms_deviation": round(rms_deviation, 3),
            "rul_hours": round(rul_hours, 2),
            "rul_ci_low": round(rul_ci_low, 2),
            "rul_ci_high": round(rul_ci_high, 2),
            "anomaly_score": round(anomaly_score, 3),
            "model_used": model_used,
            "contributions": contributions,
            "top_contributor": top_contributor,
            "top_contributor_pct": contributions[top_contributor],
            "status_label": status_label,
        }
