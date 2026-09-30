"""
Database Interface Module for SQLite
Manages raw sensor streams and health feature time-series.
"""

import sqlite3
import os
from typing import Dict, Any, List, Optional
from datetime import datetime
import pandas as pd

DEFAULT_DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data", "equipment_health.db")
SCHEMA_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data", "schema.sql")


class DatabaseManager:
    def __init__(self, db_path: str = DEFAULT_DB_PATH):
        self.db_path = db_path
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self.init_schema()

    def get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def init_schema(self):
        """Initializes tables using schema.sql if available, or inline DDL."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            if os.path.exists(SCHEMA_PATH):
                with open(SCHEMA_PATH, "r") as f:
                    cursor.executescript(f.read())
            else:
                cursor.execute("""
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
                """)
                cursor.execute("""
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
                """)
            conn.commit()

    def insert_telemetry(self, telemetry: Dict[str, Any], health_results: Optional[Dict[str, Any]] = None):
        """Stores a telemetry snapshot and computed health metrics."""
        ts = telemetry.get("timestamp")
        if isinstance(ts, datetime):
            ts_str = ts.strftime("%Y-%m-%d %H:%M:%S")
        elif ts is None:
            ts_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        else:
            ts_str = str(ts)

        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO raw_sensor_data (
                    timestamp, device_id, battery_voltage, motor_voltage,
                    total_current, motor_current, temperature, vibration, operating_mode
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                ts_str,
                telemetry.get("device_id", "RS380-ESP32-01"),
                telemetry.get("battery_voltage"),
                telemetry.get("motor_voltage"),
                telemetry.get("total_current"),
                telemetry.get("motor_current"),
                telemetry.get("temperature"),
                telemetry.get("vibration"),
                telemetry.get("condition", "NORMAL")
            ))

            if health_results:
                cursor.execute("""
                    INSERT INTO health_features (
                        timestamp, device_id, health_index, rul_hours,
                        rul_ci_low, rul_ci_high, rms_deviation,
                        top_contributor, top_contributor_pct, status_label
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    ts_str,
                    telemetry.get("device_id", "RS380-ESP32-01"),
                    health_results.get("health_index"),
                    health_results.get("rul_hours"),
                    health_results.get("rul_ci_low"),
                    health_results.get("rul_ci_high"),
                    health_results.get("rms_dev", health_results.get("rms_deviation")),
                    health_results.get("top_contributor"),
                    health_results.get("top_contributor_pct", health_results.get("contributions", {}).get(health_results.get("top_contributor"), 0)),
                    health_results.get("status_label", "HEALTHY")
                ))
            conn.commit()

    def fetch_recent_telemetry(self, limit: int = 100) -> pd.DataFrame:
        """Retrieves the most recent telemetry combined with health data."""
        query = """
            SELECT 
                r.id, r.timestamp, r.device_id, r.battery_voltage, r.motor_voltage,
                r.total_current, r.motor_current, r.temperature, r.vibration, r.operating_mode,
                h.health_index, h.rul_hours, h.rul_ci_low, h.rul_ci_high, h.rms_deviation,
                h.top_contributor, h.top_contributor_pct, h.status_label
            FROM raw_sensor_data r
            LEFT JOIN health_features h ON r.timestamp = h.timestamp
            ORDER BY r.id DESC
            LIMIT ?
        """
        with self.get_connection() as conn:
            df = pd.read_sql_query(query, conn, params=(limit,))
            if not df.empty:
                df["timestamp"] = pd.to_datetime(df["timestamp"])
                df = df.sort_values(by="timestamp").reset_index(drop=True)
            return df

    def clear_all(self):
        """Clears test tables."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM raw_sensor_data;")
            cursor.execute("DELETE FROM health_features;")
            conn.commit()
