"""
RS-380 DC Motor Run-to-Failure Dataset Generator
=================================================
Generates physics-informed synthetic run-to-failure trajectories calibrated
to the RS-380/RP-380 brushed DC motor.

METHODOLOGY (based on academic literature):
  - Weibull distribution for lifetime variability (shape β=3.5, scale η=10h)
    → β>1 means wear-out failures, typical for mechanical components
    (Reference: FAIR Brushed DC Motor Dataset, Zenodo; PHM Society literature)
  - 4 realistic degradation modes matching the F.A.I.R. dataset fault taxonomy:
      1. healthy     → normal aging, brush wear
      2. overload    → mechanical bind, current surge, thermal acceleration
      3. imbalance   → eccentric rotor/shaft, vibration-dominant failure
      4. thermal_runaway → duty cycle exceeded, exponential thermal soak
  - Rolling statistical features (RMS, std, delta/rate-of-change, power)
    computed per-cycle to mirror industry-standard feature engineering
    (IEEE predictive maintenance literature, MDPI 2024)

SENSOR MAPPING TO HARDWARE:
  battery_voltage  → 12V supply via voltage divider (ADC on ESP32)
  motor_voltage    → Motor terminal voltage divider (ADC on ESP32)
  total_current    → ACS715-20A module #1
  motor_current    → ACS715-20A module #2
  temperature      → DS18B20 or NTC thermistor (OneWire/ADC)
  vibration        → 801S analog vibration module (ADC on ESP32)

Output: data/processed/run_to_failure.csv
        data/processed/dataset_meta.json
"""

import numpy as np
import pandas as pd
import os
import json
from pathlib import Path

# ──────────────────────────────────────────────────────────────────────────────
# Reproducibility
# ──────────────────────────────────────────────────────────────────────────────
RNG = np.random.default_rng(seed=42)

# ──────────────────────────────────────────────────────────────────────────────
# RS-380 Baseline Specs (Healthy Operating Envelope)
# Calibrated from RS-380 datasheet + common test-bench measurements
# ──────────────────────────────────────────────────────────────────────────────
BASELINE = {
    "battery_voltage": {"mean": 12.20, "std": 0.12},
    "motor_voltage":   {"mean": 11.80, "std": 0.15},
    "total_current":   {"mean": 2.10,  "std": 0.10},
    "motor_current":   {"mean": 1.85,  "std": 0.08},
    "temperature":     {"mean": 38.00, "std": 1.20},
    "vibration":       {"mean": 0.35,  "std": 0.05},
}

# Sensor weights for ground-truth Health Index labelling
# (Motor Current, Temperature, and Vibration have highest diagnostic weight
#  per brush-DC motor literature — commutator wear → current, thermal → temp,
#  rotor/bearing → vibration)
SENSOR_WEIGHTS = {
    "battery_voltage": 0.05,
    "motor_voltage":   0.15,
    "total_current":   0.05,
    "motor_current":   0.25,
    "temperature":     0.25,
    "vibration":       0.25,
}

NOMINAL_LIFETIME_H = 10.0        # hours — demo scale (adjustable)
FAILURE_THRESHOLD_H = 0.70       # H below this = failed
SAMPLES_PER_HOUR    = 20         # sensor snapshots per operating hour

SENSOR_KEYS = list(BASELINE.keys())


def _weibull_lifetime(n: int) -> np.ndarray:
    """
    Sample motor lifetimes from Weibull(β=3.5, η=10h).
    β=3.5 → wear-out failure regime (typical for brushed DC motors).
    """
    # scipy not guaranteed installed; use numpy Weibull with scaling
    # numpy's weibull_min ≡ Weibull(shape=β) — scale by η
    shape = 3.5
    scale = NOMINAL_LIFETIME_H
    raw = RNG.weibull(shape, size=n)
    # Scale to match Weibull(β, η): X = η * W^(1/β) is wrong;
    # correct: if W ~ Weibull(1), then X = η * W^(1/β)
    # numpy.random.weibull(a) returns X with CDF 1-exp(-x^a) i.e. η=1, β=a
    # so to get scale η: X_scaled = scale * raw
    # Clamp to physically sensible range [2.5h, 16h]
    return np.clip(raw * scale, 2.5, 16.0)


def _degradation_signals(t: np.ndarray, mode: str) -> dict:
    """
    Physics-informed degradation model for each fault mode.
    t ∈ [0, 1]  (0 = new, 1 = at-failure)

    Polynomial/power-law exponents chosen to match published degradation
    curves for brushed DC motor faults (FAIR dataset, ResearchGate papers).
    """
    n = len(t)
    noise = lambda sigma: RNG.normal(0, sigma, n)

    if mode == "healthy":
        # Gradual aging: brush wear → slow current drift, low thermal rise,
        # mild vibration escalation from commutator groove wear
        return dict(
            vibration       = 0.35 + 0.40 * t**1.6  + noise(0.025),
            temperature     = 38.0 + 11.0 * t**1.3  + noise(0.90),
            motor_current   = 1.85 + 0.45 * t**1.4  + noise(0.055),
            total_current   = 2.10 + 0.50 * t**1.4  + noise(0.065),
            motor_voltage   = 11.80 - 0.65 * t       + noise(0.10),
            battery_voltage = 12.20 - 0.45 * t       + noise(0.09),
        )

    elif mode == "overload":
        # Mechanical bind (stall) → high current draw → exponential thermal.
        # Voltage sags significantly under overload.
        return dict(
            vibration       = 0.35 + 0.30 * t         + noise(0.050),
            temperature     = 38.0 + 26.0 * t**1.5   + noise(1.40),
            motor_current   = 1.85 + 1.35 * t**1.1   + noise(0.120),
            total_current   = 2.10 + 1.45 * t**1.1   + noise(0.140),
            motor_voltage   = 11.80 - 1.35 * t        + noise(0.200),
            battery_voltage = 12.20 - 1.10 * t        + noise(0.160),
        )

    elif mode == "imbalance":
        # Eccentric rotor / brush fragment → vibration-dominated degradation.
        # Characteristic: vibration grows as t² (progressive mechanical wear),
        # while thermal/electrical signals remain near-nominal.
        return dict(
            vibration       = 0.35 + 1.80 * t**2.1   + noise(0.090),
            temperature     = 38.0 +  9.0 * t**1.3   + noise(0.80),
            motor_current   = 1.85 + 0.65 * t         + noise(0.065),
            total_current   = 2.10 + 0.70 * t         + noise(0.075),
            motor_voltage   = 11.80 - 0.45 * t        + noise(0.10),
            battery_voltage = 12.20 - 0.38 * t        + noise(0.09),
        )

    elif mode == "thermal_runaway":
        # Duty cycle exceeded → exponential thermal soak → voltage collapse.
        # High temperature dramatically accelerates insulation degradation.
        return dict(
            vibration       = 0.35 + 0.60 * t          + noise(0.055),
            temperature     = 38.0 + 40.0 * t**1.8    + noise(2.20),
            motor_current   = 1.85 + 0.90 * t**1.6    + noise(0.100),
            total_current   = 2.10 + 1.00 * t**1.6    + noise(0.120),
            motor_voltage   = 11.80 - 2.20 * t**1.3   + noise(0.280),
            battery_voltage = 12.20 - 1.90 * t**1.3   + noise(0.230),
        )

    else:
        raise ValueError(f"Unknown degradation mode: {mode}")


def _compute_health_index(row: dict) -> float:
    """
    Ground-truth Health Index for dataset labelling.
    H = clip(1 - 0.12 * sqrt(Σ wᵢ * Zᵢ²), 0, 1)

    Formula referenced in:
      - PHM Society RUL literature (weighted Mahalanobis-style distance)
      - Our own baseline_stats.json (HealthEngine implementation)
    """
    sq_dev = sum(
        SENSOR_WEIGHTS[s] * ((row[s] - BASELINE[s]["mean"]) / BASELINE[s]["std"]) ** 2
        for s in SENSOR_KEYS
    )
    return float(np.clip(1.0 - 0.12 * np.sqrt(sq_dev), 0.0, 1.0))


def generate_dataset(n_lifecycles: int = 120) -> pd.DataFrame:
    """
    Generate n_lifecycles run-to-failure trajectories.

    Fault mode distribution (based on brushed DC motor failure statistics):
      - healthy:          40%  (normal aging, brush/commutator wear)
      - overload:         25%  (mechanical overload, binding)
      - imbalance:        25%  (rotor imbalance, bearing play)
      - thermal_runaway:  10%  (thermal overstress, duty cycle abuse)
    """
    modes        = ["healthy", "overload", "imbalance", "thermal_runaway"]
    mode_weights = [0.40,       0.25,       0.25,        0.10]

    # Sample all lifetimes upfront (Weibull)
    lifetimes = _weibull_lifetime(n_lifecycles)

    records = []
    for cycle_id in range(n_lifecycles):
        mode     = str(RNG.choice(modes, p=mode_weights))
        lifetime = float(lifetimes[cycle_id])
        n_samp   = max(30, int(lifetime * SAMPLES_PER_HOUR))

        t       = np.linspace(0, 1, n_samp)
        rul_arr = lifetime * (1.0 - t)    # true RUL at every sample point

        signals = _degradation_signals(t, mode)

        for i in range(n_samp):
            row = {s: float(signals[s][i]) for s in signals}

            # ── Physical clamp (sensor measurement limits) ─────────────────
            row["battery_voltage"] = float(np.clip(row["battery_voltage"],  8.0, 13.5))
            row["motor_voltage"]   = float(np.clip(row["motor_voltage"],    5.0, 13.0))
            row["motor_current"]   = float(np.clip(row["motor_current"],    0.3,  6.5))
            row["total_current"]   = float(np.clip(row["total_current"],    0.5,  7.5))
            row["temperature"]     = float(np.clip(row["temperature"],     20.0, 95.0))
            row["vibration"]       = float(np.clip(row["vibration"],        0.05, 4.0))

            row["rul_hours"]    = float(np.clip(rul_arr[i], 0.0, lifetime))
            row["health_index"] = _compute_health_index(row)
            row["fault_mode"]   = mode
            row["cycle_id"]     = cycle_id
            row["time_elapsed"] = float(lifetime * t[i])
            records.append(row)

    df = pd.DataFrame(records)

    # ── Rolling Statistical Features (per-cycle) ───────────────────────────
    # Industry standard: RMS, std, delta (rate-of-change) for each sensor
    # (IEEE predictive maintenance literature, MDPI Sensors journal)
    W = 5   # 5-sample rolling window (≈ 15 seconds at 20 Hz ESP32 sample rate)

    for col in SENSOR_KEYS:
        grp = df.groupby("cycle_id")[col]
        df[f"{col}_rms"]        = grp.transform(
            lambda x: x.pow(2).rolling(W, min_periods=1).mean().pow(0.5)
        )
        df[f"{col}_roll_mean"]  = grp.transform(lambda x: x.rolling(W, min_periods=1).mean())
        df[f"{col}_roll_std"]   = grp.transform(lambda x: x.rolling(W, min_periods=1).std().fillna(0))
        df[f"{col}_delta"]      = grp.transform(lambda x: x.diff().fillna(0))

    # ── Derived Features ───────────────────────────────────────────────────
    # Apparent power (W): proxy for mechanical load × efficiency
    df["power_w"]        = df["motor_voltage"] * df["motor_current"]
    # Voltage efficiency ratio: motor terminal / supply
    df["voltage_ratio"]  = df["motor_voltage"] / df["battery_voltage"].clip(lower=0.1)
    # Thermal current stress: temperature × motor_current (interaction term)
    df["thermal_stress"] = df["temperature"] * df["motor_current"]

    return df.reset_index(drop=True)


def main():
    # Resolve output path relative to this script
    script_dir = Path(__file__).resolve().parent
    out_dir    = script_dir.parent.parent / "data" / "processed"
    out_dir.mkdir(parents=True, exist_ok=True)

    print("⚙️  RS-380 Run-to-Failure Dataset Generator")
    print("    Weibull(β=3.5, η=10h) lifetime distribution")
    print("    4 fault modes: healthy / overload / imbalance / thermal_runaway")
    print()

    df = generate_dataset(n_lifecycles=120)

    csv_path  = out_dir / "run_to_failure.csv"
    meta_path = out_dir / "dataset_meta.json"

    df.to_csv(csv_path, index=False)

    feature_cols = [c for c in df.columns
                    if c not in ("rul_hours", "fault_mode", "cycle_id",
                                 "health_index", "time_elapsed")]

    meta = {
        "description": "RS-380 brushed DC motor run-to-failure dataset (physics-informed synthetic)",
        "methodology": "Weibull degradation curves + rolling statistical feature engineering",
        "n_samples":   int(len(df)),
        "n_lifecycles": int(df["cycle_id"].nunique()),
        "fault_modes": df["fault_mode"].unique().tolist(),
        "mode_counts": df.groupby("fault_mode")["cycle_id"].nunique().to_dict(),
        "rul_min_h":   round(float(df["rul_hours"].min()), 4),
        "rul_max_h":   round(float(df["rul_hours"].max()), 4),
        "health_range": [round(float(df["health_index"].min()), 4),
                         round(float(df["health_index"].max()), 4)],
        "sensors":      SENSOR_KEYS,
        "feature_cols": feature_cols,
        "baseline":     {k: v for k, v in BASELINE.items()},
        "sensor_weights": SENSOR_WEIGHTS,
    }

    with open(meta_path, "w") as f:
        json.dump(meta, f, indent=2)

    print(f"✅  Saved {len(df):,} samples → {csv_path.name}")
    print(f"    Lifecycles : {df['cycle_id'].nunique()} "
          f"(RUL range: {df['rul_hours'].min():.2f}h – {df['rul_hours'].max():.2f}h)")
    print(f"    Fault modes:")
    for mode, count in meta["mode_counts"].items():
        print(f"      {mode:20s}  {count:3d} lifecycles")
    print(f"    Feature columns : {len(feature_cols)}")
    print(f"    Saved metadata  → {meta_path.name}")

    return df


if __name__ == "__main__":
    main()
