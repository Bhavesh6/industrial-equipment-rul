# Industrial Electrical & Rotating Machinery Safety Guidelines

## Guideline SAF-01: Lockout / Tagout (LOTO) & Safe Isolation
1. **Primary Energy Isolation**: Before opening any motor enclosure or reaching into the dynamometer coupling zone, disconnect the master DC power knife switch / battery XT60 connector.
2. **Verify Zero Energy State**: Confirm motor terminal voltage is $0.00\,\text{V}$ and total system current reads $0.00\,\text{A}$ on the SCADA dashboard.
3. **Mechanical Restraint**: Ensure rotating shaft has coasted to a complete mechanical standstill before touching bearings or coupling.

---

## Guideline SAF-02: Overcurrent Safety Trip & E-Stop Recovery
1. **Hardware Safety Trip Logic**: The ESP32 firmware continuously monitors motor current at high frequency. If $I_{\text{motor}} \ge 4.50\,\text{A}$ for $>50\,\text{ms}$, the system immediately clamps PWM to $0$, trips the safety relay, and sets `safety_tripped = true`.
2. **Post-Trip Protocol**:
   - Do NOT immediately clear the trip.
   - Inspect rotor and driven load for mechanical binding, foreign object obstruction, or seized bearings.
   - Check motor casing temperature. If $T > 60.0\,^\circ\text{C}$, allow 15 minutes of convective cooling.
3. **Trip Reset**: To clear the trip, press the physical rotary encoder knob switch once or send `RESET_TRIP` from the SCADA web console.

---

## Guideline SAF-03: Thermal Hazard & Burn Protection
- The RS-380 casing can reach temperatures up to $70.0\,^\circ\text{C}$ during prolonged high-load operation.
- **PPE Requirement**: Wear certified heat-resistant mechanic gloves when touching the motor housing if the DS18B20 sensor indicates temperature exceeding $50.0\,^\circ\text{C}$.
- **Ventilation Requirement**: Ensure cooling vents on the testbed chassis remain unobstructed by cabling or tooling.

---

## Guideline SAF-04: Lithium Battery Pack Operating Envelope
- **Minimum Safe Discharge Cutoff**: $3.20\,\text{V}$ per cell ($9.6\,\text{V}$ for 3S, $12.8\,\text{V}$ for 4S).
- **Maximum Safe Voltage**: $4.20\,\text{V}$ per cell ($12.6\,\text{V}$ for 3S, $16.8\,\text{V}$ for 4S).
- **Maximum Cell-to-Cell Imbalance ($\Delta V$)**: $0.050\,\text{V}$ ($50\,\text{mV}$). If $\Delta V > 50\,\text{mV}$, stop test cycle and balance pack.
- **Fire Safety**: Never leave lithium-polymer packs unattended while discharging above 3C continuous load. Store in a fireproof LiPo safe bag when not installed in the testbed.
