# Industrial Rotating Machinery — Preventive & Corrective Maintenance SOPs

## SOP-M01: Bronze Sleeve Bushing Lubrication Procedure
- **Interval**: Every 50 operating hours or when vibration exceeds 0.40g with normal load.
- **Required Lubricant**: ISO VG 32 or synthetic light spindle oil (SAE 10W non-detergent).
- **Procedure**:
  1. De-energize equipment and execute Lockout/Tagout (LOTO).
  2. Inspect front and rear bushing retaining caps for bronze dust accumulation.
  3. Apply 2 drops of lubricant directly to the felt wick retaining collar surrounding the motor shaft.
  4. Manually rotate shaft by hand 10 revolutions to draw oil into the porous bronze capillaries.
  5. Wipe clean any excess lubricant to avoid oil ingress onto commutator copper segments.

---

## SOP-M02: Carbon Brush & Commutator Inspection Procedure
- **Interval**: Every 100 operating hours or upon erratic current ripple / sparking.
- **Minimum Allowable Brush Length**: **3.50 mm** (Discard if shorter than 3.50 mm).
- **Inspection Steps**:
  1. Unclip rear brush holder assembly clips.
  2. Measure brush face contact area: minimum 80% surface contact pattern required.
  3. Check commutator face for scoring, black carbon film buildup, or burning.
  4. Clean commutator surface using a lint-free industrial swab dampened with electrical contact cleaner (isopropyl alcohol 99%).
  5. Verify brush spring tension is between 1.2 N and 1.8 N.

---

## SOP-M03: Shaft Coupling & Dynamic Alignment Procedure
- **Interval**: Post-assembly or when Vibration X/Y/Z indicates 1X or 2X rotational harmonic peak.
- **Maximum Permissible Angular Misalignment**: $\le 0.5^\circ$
- **Maximum Permissible Radial Offset**: $\le 0.05\,\text{mm}$
- **Procedure**:
  1. Loosen coupling set screws and mount dial indicator against driven testbed hub.
  2. Measure total indicator reading (TIR) through 360-degree manual rotation.
  3. Shim motor mounting feet using brass precision shims until runout is under 0.05 mm.
  4. Torque motor mounting fasteners in a cross pattern to **2.50 N·m**.
  5. Run baseline vibration verification sweep across 1,000 to 6,000 RPM.

---

## SOP-M04: Armature Winding Health & Electrical Isolation Test
- **Interval**: Semi-annual or following any overcurrent trip event (>4.5A).
- **Testing Instruments**: Digital milliohm meter and 250V Megohmmeter (insulation tester).
- **Procedure**:
  1. Disconnect motor terminals from H-bridge driver.
  2. Measure phase resistance across all 3 commutator poles: values must match within $\pm 5\%$. Resistance under $1.8\,\Omega$ indicates an inter-turn winding short.
  3. Measure insulation resistance between armature windings and motor casing: must exceed $>10\,\text{M}\Omega$ at 250V DC test voltage.
