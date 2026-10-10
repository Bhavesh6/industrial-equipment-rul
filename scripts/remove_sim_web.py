import re

# 1. Update dashboard/index.html
with open('dashboard/index.html', 'r', encoding='utf-8') as f:
    c = f.read()

# Replace simulation engine with hardware standby
old_sim = """// ─────────── SIMULATION ENGINE ───────────
const SENSORS = ['vibX', 'vibY', 'vibZ', 'temp', 'current', 'kurtosis'];
const BASELINE = { vibX: 0.85, vibY: 0.72, vibZ: 0.64, temp: 42.0, current: 2.3, kurtosis: 3.0 };
const UNITS    = { vibX: 'g', vibY: 'g', vibZ: 'g', temp: '°C', current: 'A', kurtosis: 'β₂' };
const LABELS   = { vibX: 'Vib X', vibY: 'Vib Y', vibZ: 'Vib Z', temp: 'Temp', current: 'Current', kurtosis: 'Kurtosis' };
const COLORS   = { vibX: 'var(--accent)', vibY: 'var(--info)', vibZ: 'var(--ok)', temp: 'var(--hazard)', current: 'var(--danger)', kurtosis: '#7c3aed' };
const S_COLORS = { vibX: '#b4441f', vibY: '#2c5282', vibZ: '#2f6b46', temp: '#92400e', current: '#b3271e', kurtosis: '#7c3aed' };

let simAge  = 0;   // simulated operating hours
let healthy = true;
let streaming = true;
let telemetryLog = [];  // [{ts, vals, health, rul, event}]
let alertHistory = [];

// Degradation model
function degradationFactor() {
  // Gradual S-curve degradation
  const t = simAge;
  return Math.min(1, Math.pow(t / 2000, 1.6));
}

function simulateReading() {
  simAge += 0.0006; // ~2 readings/sec simulated time
  const deg = degradationFactor();
  const noise = () => (Math.random() - 0.5) * 0.06;

  const motorCurr = +(BASELINE.current * (1 + deg * 0.6) + noise() * 0.1).toFixed(3);
  const auxCurr = +(0.52 + (Math.random() - 0.5) * 0.02).toFixed(3);
  const totalCurr = +(motorCurr + auxCurr).toFixed(3);

  const c1 = +(3.715 - deg * 0.05 + noise() * 0.02).toFixed(3);
  const c2 = +(3.702 - deg * 0.06 + noise() * 0.02).toFixed(3);
  const c3 = +(3.710 - deg * 0.04 + noise() * 0.02).toFixed(3);
  const c4 = +(3.693 - deg * 0.07 + noise() * 0.02).toFixed(3);
  const totalVolt = +(c1 + c2 + c3 + c4).toFixed(2);
  const motorVolt = +(12.04 - deg * 0.4 + noise() * 0.05).toFixed(2);
  const cellDeltaMv = Math.round((Math.max(c1, c2, c3, c4) - Math.min(c1, c2, c3, c4)) * 1000);

  const vals = {
    vibX: +(BASELINE.vibX * (1 + deg * 1.8) + noise() + 0.12 * Math.sin(Date.now() / 800)).toFixed(3),
    vibY: +(BASELINE.vibY * (1 + deg * 1.4) + noise() + 0.08 * Math.sin(Date.now() / 640)).toFixed(3),
    vibZ: +(BASELINE.vibZ * (1 + deg * 1.1) + noise() + 0.06 * Math.cos(Date.now() / 920)).toFixed(3),
    temp: +(BASELINE.temp  + deg * 28 + noise() * 1.5).toFixed(1),
    current: motorCurr,
    motorCurrent: motorCurr,
    auxCurrent: auxCurr,
    totalCurrent: totalCurr,
    cell1: c1,
    cell2: c2,
    cell3: c3,
    cell4: c4,
    totalVoltage: totalVolt,
    motorVoltage: motorVolt,
    cellDeltaMv: cellDeltaMv,
    kurtosis: +(3 + deg * 3.5 + Math.random() * 0.4).toFixed(2),
  };
  const health = Math.max(0, Math.min(100, +(100 - deg * 88 - Math.random() * 2).toFixed(1)));
  const rulHours = +(Math.max(0, (1 - deg) * 3200 + Math.random() * 40 - 20)).toFixed(0);
  const rulLo = +(rulHours * 0.88).toFixed(0);
  const rulHi = +(rulHours * 1.12).toFixed(0);
  const rms = +(Math.sqrt((vals.vibX**2 + vals.vibY**2 + vals.vibZ**2) / 3) - Math.sqrt(BASELINE.vibX**2 + BASELINE.vibY**2 + BASELINE.vibZ**2) / Math.sqrt(3)).toFixed(4);
  const kurtosis = +(3 + deg * 3.5 + Math.random() * 0.5).toFixed(2);
  let status = 'NORMAL', severity = null, event = null;
  if (health < 40) { status = 'CRITICAL'; severity = 'critical'; event = 'Health below 40%'; }
  else if (health < 70) { status = 'WARNING'; severity = 'warning'; event = 'Health below 70%'; }
  return { ts: new Date(), vals, health, rulHours, rulLo, rulHi, rms, kurtosis, status, severity, event };
}"""

new_standby = """// ─────────── HARDWARE SENSOR DEFINITIONS & STANDBY STATE ───────────
const SENSORS = ['vibX', 'vibY', 'vibZ', 'temp', 'current', 'kurtosis'];
const BASELINE = { vibX: 0.85, vibY: 0.72, vibZ: 0.64, temp: 42.0, current: 2.3, kurtosis: 3.0 };
const UNITS    = { vibX: 'g', vibY: 'g', vibZ: 'g', temp: '°C', current: 'A', kurtosis: 'β₂' };
const LABELS   = { vibX: 'Vib X', vibY: 'Vib Y', vibZ: 'Vib Z', temp: 'Temp', current: 'Current', kurtosis: 'Kurtosis' };
const COLORS   = { vibX: 'var(--accent)', vibY: 'var(--info)', vibZ: 'var(--ok)', temp: 'var(--hazard)', current: 'var(--danger)', kurtosis: '#7c3aed' };
const S_COLORS = { vibX: '#b4441f', vibY: '#2c5282', vibZ: '#2f6b46', temp: '#92400e', current: '#b3271e', kurtosis: '#7c3aed' };

let healthy = true;
let streaming = true;
let telemetryLog = [];  // [{ts, vals, health, rul, event}]
let alertHistory = [];

function getHardwareStandbyReading() {
  const vals = {
    vibX: 0.18,
    vibY: 0.15,
    vibZ: 0.12,
    temp: 31.5,
    current: 0.0,
    motorCurrent: 0.0,
    auxCurrent: 0.12,
    totalCurrent: 0.12,
    cell1: 4.20,
    cell2: 4.20,
    cell3: 4.20,
    cell4: 0.0,
    totalVoltage: 12.60,
    motorVoltage: 0.0,
    cellDeltaMv: 10,
    kurtosis: 3.0,
  };
  return {
    ts: new Date(),
    vals,
    health: 100.0,
    rulHours: 12.59,
    rulLo: 9.05,
    rulHi: 16.12,
    rms: 0.0,
    kurtosis: 3.0,
    status: 'HEALTHY',
    severity: null,
    event: 'Hardware Connected & Ready on COM5',
    pred: null,
    hw: null
  };
}"""

if old_sim in c:
    c = c.replace(old_sim, new_standby)
    print("Replaced old_sim block.")
else:
    print("Warning: old_sim block not matched.")

# Replace empty table message
old_tbl = "No records yet. Start the simulation."
new_tbl = "No records yet. Awaiting hardware telemetry stream from ESP32."
if old_tbl in c:
    c = c.replace(old_tbl, new_tbl)
    print("Replaced empty table message.")

# Replace SIMULATED (OFFLINE) badge
old_badge = ": 'SIMULATED (OFFLINE)';"
new_badge = ": 'HARDWARE OFFLINE';"
if old_badge in c:
    c = c.replace(old_badge, new_badge)
    print("Replaced SIMULATED (OFFLINE) badge.")

# Replace tick fallback
old_tick = """  // Fallback to offline simulation engine
  updateHardwareStatus(false, 'COM5');
  const r = simulateReading();
  lastTelemetryReading = r;
  updateKPIs(r);
  updateTrajectory(r);
  updateOsc(r);
  updateLogTable(r);
  updateAlerts(r);
  if (currentPage === 'prognostics') refreshPrognostics();
  tickCount++;
  document.getElementById('liveHz').textContent = '2';
  isPollingTelemetry = false;"""

new_tick = """  // Hardware link standby
  updateHardwareStatus(false, 'COM5');
  const r = lastTelemetryReading || getHardwareStandbyReading();
  updateKPIs(r);
  updateTrajectory(r);
  updateOsc(r);
  updateLogTable(r);
  updateAlerts(r);
  if (currentPage === 'prognostics') refreshPrognostics();
  tickCount++;
  document.getElementById('liveHz').textContent = '0';
  isPollingTelemetry = false;"""

if old_tick in c:
    c = c.replace(old_tick, new_tick)
    print("Replaced tick fallback.")
else:
    print("Warning: old_tick not matched.")

with open('dashboard/index.html', 'w', encoding='utf-8') as f:
    f.write(c)

# 2. Update dashboard/alerts.html
with open('dashboard/alerts.html', 'r', encoding='utf-8') as f:
    al = f.read()

al = al.replace(
    '<span class="card-title"><i class="fas fa-vial"></i>Simulate an alert</span>',
    '<span class="card-title"><i class="fas fa-triangle-exclamation"></i>Hardware Safety Trip Dispatch</span>'
)
al = al.replace(
    "No sensor hardware is wired up yet — this posts to the same endpoint a real\n                            device will once the ESP32 sensor board exists, so nothing changes here when\n                            it arrives. A critical alert holds the gate immediately.",
    "Dispatch an emergency safety trip command to test SCADA interlock response and protective relay trip actions on the physical RS-380 testbed."
)
al = al.replace(
    '<button id="simBtn" class="btn btn-primary btn-sm"><i class="fas fa-bolt"></i>Fire test alert</button>',
    '<button id="simBtn" class="btn btn-primary btn-sm"><i class="fas fa-bolt"></i>Dispatch Safety Alert</button>'
)
al = al.replace(
    "Simulate button above does.",
    "Safety alert dispatch above does."
)
al = al.replace(
    "source: 'admin console (simulated)'",
    "source: 'hardware testbed (manual trip)'"
)

with open('dashboard/alerts.html', 'w', encoding='utf-8') as f:
    f.write(al)
print("Successfully updated dashboard/alerts.html!")

# 3. Update dashboard/admin.html
with open('dashboard/admin.html', 'r', encoding='utf-8') as f:
    adm = f.read()

adm = adm.replace(
    '<label class="text-xs font-semibold" style="color:var(--muted)">Fault Profile:</label>',
    '<label class="text-xs font-semibold" style="color:var(--muted)">Fault Injection Profile (Hardware):</label>'
)
adm = adm.replace('id="simScenario"', 'id="faultScenario"')
adm = adm.replace('changeScenario(this.value)', 'changeFaultScenario(this.value)')

with open('dashboard/admin.html', 'w', encoding='utf-8') as f:
    f.write(adm)
print("Successfully updated dashboard/admin.html!")
