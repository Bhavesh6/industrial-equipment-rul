-- SQLite Schema for Industrial Equipment Health Monitoring (RS-380 Prototype)

-- 1. Raw High-Frequency Sensor Stream
CREATE TABLE IF NOT EXISTS raw_sensor_data (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    device_id TEXT NOT NULL DEFAULT 'RS380-ESP32-01',
    battery_voltage REAL NOT NULL,
    motor_voltage REAL NOT NULL,
    total_current REAL NOT NULL,
    motor_current REAL NOT NULL,
    temperature REAL NOT NULL,
    vibration REAL NOT NULL,
    operating_mode TEXT DEFAULT 'NORMAL'
);

-- Index for timestamp query optimization
CREATE INDEX IF NOT EXISTS idx_raw_sensor_ts ON raw_sensor_data (timestamp);

-- 2. Aggregated Windowed Health & Diagnostics Features
CREATE TABLE IF NOT EXISTS health_features (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    device_id TEXT NOT NULL DEFAULT 'RS380-ESP32-01',
    window_seconds INTEGER NOT NULL DEFAULT 5,
    health_index REAL NOT NULL,
    rul_hours REAL NOT NULL,
    rul_ci_low REAL NOT NULL,
    rul_ci_high REAL NOT NULL,
    rms_deviation REAL NOT NULL,
    top_contributor TEXT NOT NULL,
    top_contributor_pct REAL NOT NULL,
    status_label TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_health_features_ts ON health_features (timestamp);
