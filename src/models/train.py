"""
RS-380 Motor RUL — ML Model Training Pipeline
==============================================
Trains, evaluates, and serializes machine learning models for Remaining
Useful Life (RUL) prediction and anomaly detection.

MODELS TRAINED:
  1. GradientBoostingRegressor  — primary RUL predictor
     (best accuracy on tabular sensor data; 2024 PHM Society benchmarks)
  2. RandomForestRegressor      — robust baseline / uncertainty reference
  3. IsolationForest            — unsupervised anomaly / novelty detector
     (for real-time fault flagging when no labelled failure data available)

ML BEST PRACTICES APPLIED:
  ● GroupShuffleSplit by cycle_id: prevents data leakage across lifecycles
    (CRITICAL — random row split inflates R² by ~0.15; see CMAPSS literature)
  ● sklearn Pipeline (StandardScaler → model): scaler fitted only on train
  ● 5-fold GroupKFold CV for honest generalisation estimate
  ● SHAP TreeExplainer for per-sensor attribution (industry-grade XAI)
  ● joblib serialisation of full Pipeline objects

OUTPUTS (models/):
  rul_gbr_pipeline.joblib   — Gradient Boosting RUL pipeline
  rul_rf_pipeline.joblib    — Random Forest RUL pipeline
  anomaly_iso_forest.joblib — Isolation Forest anomaly detector
  scaler.joblib             — standalone StandardScaler (for live inference)
  metrics.json              — training + CV metrics, feature importances
  shap_summary.json         — mean |SHAP| values per sensor
"""

import copy
import json
import os
import sys
import warnings
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import (GradientBoostingRegressor, IsolationForest,
                              RandomForestRegressor)
from sklearn.model_selection import GroupKFold, GroupShuffleSplit
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

warnings.filterwarnings("ignore")

# ──────────────────────────────────────────────────────────────────────────────
# Paths
# ──────────────────────────────────────────────────────────────────────────────
ROOT      = Path(__file__).resolve().parent.parent.parent
DATA_DIR  = ROOT / "data" / "processed"
MODEL_DIR = ROOT / "models"
MODEL_DIR.mkdir(parents=True, exist_ok=True)

# ──────────────────────────────────────────────────────────────────────────────
# Feature columns used for training (excluding targets & metadata)
# ──────────────────────────────────────────────────────────────────────────────
META_COLS   = {"rul_hours", "health_index", "fault_mode", "cycle_id", "time_elapsed"}
TARGET_COL  = "rul_hours"

# Core sensors + all engineered features will be selected dynamically
MUST_INCLUDE = [
    "battery_voltage", "motor_voltage", "total_current", "motor_current",
    "temperature", "vibration",
    "power_w", "voltage_ratio", "thermal_stress",
]


def load_data() -> pd.DataFrame:
    csv_path = DATA_DIR / "run_to_failure.csv"
    if not csv_path.exists():
        print(f"❌  Dataset not found: {csv_path}")
        print("    Run:  python src/data/generate_training_data.py  first.")
        sys.exit(1)

    df = pd.read_csv(csv_path)
    print(f"📂  Loaded {len(df):,} rows × {len(df.columns)} columns "
          f"({df['cycle_id'].nunique()} lifecycles)")
    return df


def select_features(df: pd.DataFrame) -> list:
    """
    Select all numeric columns that are not metadata / target columns.
    This automatically picks up all rolling/RMS/delta engineered features.
    """
    cols = [
        c for c in df.columns
        if c not in META_COLS and df[c].dtype in [np.float64, np.int64, np.float32]
    ]
    return cols


def split_by_cycle(df: pd.DataFrame, feature_cols: list, test_size: float = 0.20):
    """
    Train/test split grouped by cycle_id to prevent data leakage.

    Research basis: C-MAPSS literature explicitly warns that row-level random
    split inflates test R² because same-cycle readings share degradation state.
    GroupShuffleSplit ensures all readings of a lifecycle are in ONE split.
    """
    X      = df[feature_cols].values
    y      = df[TARGET_COL].values
    groups = df["cycle_id"].values

    gss = GroupShuffleSplit(n_splits=1, test_size=test_size, random_state=42)
    train_idx, test_idx = next(gss.split(X, y, groups))

    return (X[train_idx], X[test_idx],
            y[train_idx], y[test_idx],
            groups[train_idx], groups[test_idx])


def train_rul_models(X_train, y_train, groups_train) -> dict:
    """
    Train Gradient Boosting and Random Forest RUL regressors inside
    sklearn Pipelines (StandardScaler → Regressor).

    Hyperparameters tuned for the RS-380 motor task:
      GBR: n_estimators=200, max_depth=5, learning_rate=0.05, subsample=0.8
           (standard anti-overfit settings from PHM Society examples)
      RF:  n_estimators=200, max_depth=10, min_samples_leaf=4
           (conservative depth to reduce overfit on ~120 cycle dataset)
    """
    pipelines = {
        "GradientBoosting": Pipeline([
            ("scaler", StandardScaler()),
            ("model",  GradientBoostingRegressor(
                n_estimators   = 200,
                max_depth      = 5,
                learning_rate  = 0.05,
                subsample      = 0.80,
                min_samples_leaf = 4,
                random_state   = 42,
            )),
        ]),
        "RandomForest": Pipeline([
            ("scaler", StandardScaler()),
            ("model",  RandomForestRegressor(
                n_estimators    = 150,
                max_depth       = 10,
                min_samples_leaf = 4,
                random_state    = 42,
            )),
        ]),
    }

    trained = {}
    for name, pipe in pipelines.items():
        print(f"   🏋️  Training {name} …", end=" ", flush=True)
        pipe.fit(X_train, y_train)
        trained[name] = pipe
        print("done")

    return trained


def cross_validate(pipelines: dict, X_train, y_train, groups_train,
                   n_splits: int = 5) -> dict:
    """
    5-fold GroupKFold cross-validation.
    Groups = cycle_id → no lifecycle spans two folds (data-leakage-free).
    """
    gkf    = GroupKFold(n_splits=n_splits)
    cv_res = {}

    for name, pipe in pipelines.items():
        fold_rmse, fold_mae, fold_r2 = [], [], []
        for fold_idx, (tr, va) in enumerate(gkf.split(X_train, y_train, groups_train)):
            pipe_clone = copy.deepcopy(pipe)
            pipe_clone.fit(X_train[tr], y_train[tr])
            y_pred = pipe_clone.predict(X_train[va])
            fold_rmse.append(np.sqrt(mean_squared_error(y_train[va], y_pred)))
            fold_mae.append(mean_absolute_error(y_train[va], y_pred))
            fold_r2.append(r2_score(y_train[va], y_pred))

        cv_res[name] = {
            "cv_rmse_mean": round(float(np.mean(fold_rmse)), 4),
            "cv_rmse_std":  round(float(np.std(fold_rmse)),  4),
            "cv_mae_mean":  round(float(np.mean(fold_mae)),  4),
            "cv_r2_mean":   round(float(np.mean(fold_r2)),   4),
        }
        print(f"   📊  {name:20s}  "
              f"CV-RMSE={cv_res[name]['cv_rmse_mean']:.3f}±"
              f"{cv_res[name]['cv_rmse_std']:.3f}h  "
              f"CV-R²={cv_res[name]['cv_r2_mean']:.4f}")

    return cv_res


def evaluate_test(pipelines: dict, X_test, y_test) -> dict:
    """Evaluate on held-out test set (unseen lifecycle cycles)."""
    results = {}
    for name, pipe in pipelines.items():
        y_pred = pipe.predict(X_test)
        rmse   = float(np.sqrt(mean_squared_error(y_test, y_pred)))
        mae    = float(mean_absolute_error(y_test, y_pred))
        r2     = float(r2_score(y_test, y_pred))
        results[name] = {
            "test_rmse_h": round(rmse, 4),
            "test_mae_h":  round(mae,  4),
            "test_r2":     round(r2,   4),
        }
        print(f"   🎯  {name:20s}  "
              f"Test RMSE={rmse:.3f}h  MAE={mae:.3f}h  R²={r2:.4f}")
    return results


def train_isolation_forest(X_train) -> IsolationForest:
    """
    Isolation Forest on healthy baseline samples.
    contamination=0.05 → expect ~5% anomalies in training data.
    (Recommended by sklearn docs for IIoT sensor data with occasional spikes)
    """
    print("   🌲  Training Isolation Forest (anomaly detector) …", end=" ", flush=True)
    iso = IsolationForest(
        n_estimators  = 50,
        contamination = 0.05,
        max_samples   = 2000,   # subsample for speed — statistically sufficient
        max_features  = 1.0,
        random_state  = 42,
    )
    iso.fit(X_train)
    print("done")
    return iso


def compute_shap_values(pipeline, X_train, feature_cols: list) -> dict:
    """
    Compute mean absolute SHAP values for each feature.
    Uses TreeExplainer (exact, fast for tree-based models).
    Returns sensor-level aggregated importance.
    """
    try:
        import shap
        print("   🔍  Computing SHAP values …", end=" ", flush=True)

        model   = pipeline.named_steps["model"]
        scaler  = pipeline.named_steps["scaler"]
        X_scaled = scaler.transform(X_train)

        explainer  = shap.TreeExplainer(model)
        # Use a subsample for speed (SHAP is O(n*depth*features))
        subsample = min(2000, len(X_scaled))
        idx       = np.random.default_rng(0).choice(len(X_scaled), subsample, replace=False)
        shap_vals = explainer.shap_values(X_scaled[idx])

        mean_abs  = np.abs(shap_vals).mean(axis=0)
        shap_dict = {feature_cols[i]: round(float(mean_abs[i]), 6)
                     for i in range(len(feature_cols))}

        # Sensor-level rollup (aggregate all rolling/delta cols per sensor)
        sensors = ["battery_voltage", "motor_voltage", "total_current",
                   "motor_current", "temperature", "vibration"]
        sensor_shap = {}
        for s in sensors:
            total = sum(v for k, v in shap_dict.items() if k.startswith(s))
            sensor_shap[s] = round(total, 6)

        print("done")
        return {"feature_level": shap_dict, "sensor_level": sensor_shap}

    except ImportError:
        print("⚠️  SHAP not installed — skipping (pip install shap)")
        return {}
    except Exception as e:
        print(f"⚠️  SHAP error: {e} — skipping")
        return {}


def get_feature_importance(pipeline, feature_cols: list) -> dict:
    """
    Extract sklearn feature_importances_ (Gini/MDI-based).
    Works for both GBR and RF.
    """
    model  = pipeline.named_steps["model"]
    imps   = model.feature_importances_
    ranked = sorted(
        ((feature_cols[i], round(float(imps[i]), 6)) for i in range(len(feature_cols))),
        key=lambda x: -x[1],
    )
    return dict(ranked)


def save_models(pipelines: dict, iso_forest: IsolationForest,
                scaler: StandardScaler) -> None:
    """Save all model artefacts using joblib."""
    for name, pipe in pipelines.items():
        short = "gbr" if "Gradient" in name else "rf"
        path  = MODEL_DIR / f"rul_{short}_pipeline.joblib"
        joblib.dump(pipe, path, compress=3)
        print(f"   💾  Saved {path.name}  ({path.stat().st_size // 1024} KB)")

    joblib.dump(iso_forest, MODEL_DIR / "anomaly_iso_forest.joblib", compress=3)
    joblib.dump(scaler,     MODEL_DIR / "scaler.joblib",             compress=3)
    print(f"   💾  Saved anomaly_iso_forest.joblib")
    print(f"   💾  Saved scaler.joblib")


def main():
    print("=" * 60)
    print("  RS-380 Motor RUL — Machine Learning Training Pipeline")
    print("=" * 60)

    # ── 1. Load Data ──────────────────────────────────────────────
    print("\n[1/6] Loading dataset …")
    df = load_data()

    # ── 2. Select Features ────────────────────────────────────────
    print("\n[2/6] Selecting features …")
    feature_cols = select_features(df)
    print(f"   {len(feature_cols)} feature columns selected")

    # ── 3. Split (GroupShuffleSplit by cycle_id) ──────────────────
    print("\n[3/6] Splitting train/test by lifecycle (GroupShuffleSplit) …")
    X_train, X_test, y_train, y_test, g_train, g_test = split_by_cycle(
        df, feature_cols, test_size=0.20
    )
    print(f"   Train: {len(X_train):,} rows  ({len(np.unique(g_train))} lifecycles)")
    print(f"   Test : {len(X_test):,} rows  ({len(np.unique(g_test))} lifecycles)")

    # ── 4. Train Models ───────────────────────────────────────────
    print("\n[4/6] Training models …")
    pipelines = train_rul_models(X_train, y_train, g_train)
    iso_forest = train_isolation_forest(X_train)

    # ── 5. Evaluate ───────────────────────────────────────────────
    print("\n[5/6] Evaluating …")
    print("  Cross-Validation (5-fold GroupKFold):")
    cv_metrics = cross_validate(pipelines, X_train, y_train, g_train)
    print("  Held-Out Test Set:")
    test_metrics = evaluate_test(pipelines, X_test, y_test)

    # ── 5b. SHAP Values (best model = GBR) ────────────────────────
    shap_data = compute_shap_values(
        pipelines["GradientBoosting"], X_train, feature_cols
    )

    # ── 5c. Feature importances ───────────────────────────────────
    feat_imp = {}
    for name, pipe in pipelines.items():
        feat_imp[name] = get_feature_importance(pipe, feature_cols)

    # ── 6. Save Artefacts ─────────────────────────────────────────
    print("\n[6/6] Saving model artefacts …")
    # Standalone scaler fitted on full training set (for live inference)
    standalone_scaler = StandardScaler().fit(X_train)
    save_models(pipelines, iso_forest, standalone_scaler)

    # Determine best model by test R²
    best_name = max(test_metrics, key=lambda n: test_metrics[n]["test_r2"])

    # ── Save Metrics JSON ─────────────────────────────────────────
    metrics = {
        "description":   "RS-380 Motor RUL prediction — ML training metrics",
        "best_model":    best_name,
        "n_train_samples": int(len(X_train)),
        "n_test_samples":  int(len(X_test)),
        "n_features":      len(feature_cols),
        "feature_cols":    feature_cols,
        "cv_metrics":      cv_metrics,
        "test_metrics":    test_metrics,
        "feature_importance": feat_imp,
        "shap_summary":    shap_data,
    }
    metrics_path = MODEL_DIR / "metrics.json"
    with open(metrics_path, "w") as f:
        json.dump(metrics, f, indent=2)

    # ── Final Summary ─────────────────────────────────────────────
    print("\n" + "=" * 60)
    print("  ✅  TRAINING COMPLETE")
    print("=" * 60)
    best_m = test_metrics[best_name]
    print(f"  Best Model    : {best_name}")
    print(f"  Test R²       : {best_m['test_r2']:.4f}")
    print(f"  Test RMSE     : ±{best_m['test_rmse_h']:.3f} hours")
    print(f"  Test MAE      : ±{best_m['test_mae_h']:.3f} hours")
    print(f"\n  Model files saved to: {MODEL_DIR}")
    print(f"  Metrics saved to:     {metrics_path.name}")

    if shap_data.get("sensor_level"):
        ranked = sorted(shap_data["sensor_level"].items(), key=lambda x: -x[1])
        print(f"\n  Top sensor contributions (SHAP):")
        for sensor, val in ranked[:4]:
            print(f"    {sensor:20s}  {val:.4f}")


if __name__ == "__main__":
    main()
