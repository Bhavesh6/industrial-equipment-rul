import streamlit as st
import pandas as pd
import sqlite3
import plotly.express as px
from datetime import datetime, timedelta

st.set_page_config(page_title="Industrial Equipment Health Dashboard", layout="wide")

st.title("🔧 Industrial Equipment Health Monitoring")
st.caption("RS-380 motor prototype – live sensor data, health index, RUL, and maintenance assistant")

# Placeholder: simulate data or read from SQLite
def get_latest_data():
    # In real implementation, query SQLite for latest window
    # Here we return dummy values
    return {
        "health": 0.92,
        "rul": 8.5,
        "rul_low": 7.8,
        "rul_high": 9.2,
        "battery_voltage": 12.4,
        "motor_voltage": 11.8,
        "total_current": 2.1,
        "motor_current": 1.9,
        "temperature": 38.5,
        "vibration": 0.42,
        "timestamp": datetime.now()
    }

data = get_latest_data()

# Live gauges
col1, col2, col3, col4 = st.columns(4)
col1.metric("Battery Voltage (V)", f"{data['battery_voltage']:.2f}")
col2.metric("Motor Voltage (V)", f"{data['motor_voltage']:.2f}")
col3.metric("Total Current (A)", f"{data['total_current']:.2f}")
col4.metric("Motor Current (A)", f"{data['motor_current']:.2f}")

col5, col6, col7, col8 = st.columns(4)
col5.metric("Temperature (°C)", f"{data['temperature']:.1f}")
col6.metric("Vibration (g)", f"{data['vibration']:.3f}")
col7.metric("Health Index", f"{data['health']:.2f}")
col8.metric("RUL (h)", f"{data['rul']:.1f}", delta=f"[{data['rul_low']:.1f}–{data['rul_high']:.1f}]")

st.subheader("📈 Trends (placeholder)")
# Dummy trend data
times = [datetime.now() - timedelta(minutes=i) for i in range(60, 0, -1)]
health_trend = [0.9 + 0.05 * (i/60) for i in range(60)]
df_trend = pd.DataFrame({"time": times, "health": health_trend})
fig = px.line(df_trend, x="time", y="health", title="Health Index Trend")
st.plotly_chart(fig, use_container_width=True)

st.subheader("💬 Maintenance Assistant")
st.info("💡 Ask about the current state, possible faults, or maintenance steps.")
user_question = st.text_input("Your question:")
if user_question:
    st.write(f"**You:** {user_question}")
    # Placeholder response
    st.write("**Assistant:** Based on the current health index (0.92) and RUL (~8.5 h), the system appears healthy. Vibration is moderate; check for imbalance if it rises.")

st.caption("Data updates every second in a real implementation.")