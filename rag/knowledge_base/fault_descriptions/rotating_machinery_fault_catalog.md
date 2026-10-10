# Industrial Rotating Equipment Fault Catalog (ISO 13374 / ISO 13379 Standard)

## Fault Category 1: Mechanical Faults

### Fault ID F-01: Rotor Unbalance & Coupling Misalignment
- **Physical Mechanism**: Mass eccentricity around rotor rotational axis or angular offset between motor shaft and dynamometer load coupling.
- **Sensor Manifestations**:
  - **Vibration**: Steep elevation in mechanical acceleration ($>0.40\,\text{g}$, peak-to-peak amplitude spikes).
  - **Current**: Mild periodic 1X/2X modulation in motor load current ($+10\text{--}15\%$).
  - **Temperature**: Normal or minor friction rise.
- **SHAP Feature Attribution**: Vibration dominates attribution ($\ge 45\%$).
- **Corrective Action**: Re-align shaft coupling per SOP-M03; inspect for bent shaft or missing set screw.

---

### Fault ID F-02: Bearing Wear & Bushing Clearance Loss
- **Physical Mechanism**: Wear of porous bronze sleeve bushings, oil depletion, or micro-spalling of raceways causing excessive radial play.
- **Sensor Manifestations**:
  - **Vibration**: High-frequency vibration noise and sudden step changes in vibration RMS ($>0.50\,\text{g}$).
  - **Temperature**: Rapid temperature climb ($>48.0\,^\circ\text{C}\to 60.0\,^\circ\text{C}$) due to metal-on-metal dry boundary friction.
  - **Current**: Moderate increase in no-load and rated current ($+0.30\,\text{A}$ to $+0.60\,\text{A}$).
- **SHAP Feature Attribution**: Shared high contribution between **Vibration** and **Temperature**.
- **Corrective Action**: Apply ISO VG 32 spindle oil per SOP-M01. If radial play exceeds 0.10 mm, replace motor bearing end cap.

---

## Fault Category 2: Electrical & Commutation Faults

### Fault ID F-03: Carbon Brush Wear & Commutator Pitting
- **Physical Mechanism**: Carbon brush erosion below minimum length, brush spring relaxation, or copper commutator bar oxidation/arcing.
- **Sensor Manifestations**:
  - **Motor Current**: Highly erratic current spikes, increased variance/standard deviation, high-frequency commutation noise.
  - **Motor Voltage**: High voltage ripple at motor terminals.
  - **Vibration**: Minor acoustic crackle; normal mechanical vibration.
- **SHAP Feature Attribution**: **Motor Current Rolling Std** and **Current Delta** dominate attribution.
- **Corrective Action**: Clean commutator copper bars with isopropyl alcohol and install new carbon brushes per SOP-M02.

---

### Fault ID F-04: Armature Inter-Turn Short Circuit & Overload
- **Physical Mechanism**: Thermal breakdown of polyurethane enamel wire insulation leading to turn-to-turn short circuit within rotor slot.
- **Sensor Manifestations**:
  - **Motor Current**: Sharp spike to $>3.20\,\text{A}$ under nominal load; rapidly approaching stall trip ($4.50\,\text{A}$).
  - **Temperature**: Extreme localized thermal rise ($>65.0\,^\circ\text{C}$).
  - **RPM**: Significant speed degradation under load ($>30\%$ drop in RPM).
- **SHAP Feature Attribution**: **Motor Current** and **Temperature** drive $\ge 80\%$ of SHAP anomaly.
- **Corrective Action**: Immediate de-energization! Conduct winding insulation resistance test per SOP-M04. Replace armature core if shorted.

---

## Fault Category 3: Power Distribution & Battery Faults

### Fault ID F-05: Battery Cell Imbalance & High Internal Resistance
- **Physical Mechanism**: Capacity divergence or degraded cell impedance in 3S/4S Lithium-ion pack.
- **Sensor Manifestations**:
  - **Cell Delta**: Cell voltage spread $\Delta V > 50\,\text{mV}$ under load.
  - **Battery Voltage**: Excessive voltage sag under motor acceleration ($>1.2\,\text{V}$ voltage drop).
- **SHAP Feature Attribution**: **Battery Voltage** and **Voltage Ratio** drive deviation.
- **Corrective Action**: Disconnect pack and perform balance charging at $0.5\,\text{C}$ CC/CV. Retire cell if $\Delta V > 100\,\text{mV}$ persists.
