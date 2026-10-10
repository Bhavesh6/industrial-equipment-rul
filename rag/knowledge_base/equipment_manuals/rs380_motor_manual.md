# RS-380 Brushed DC Motor — Technical Specifications & Equipment Manual

## 1. Equipment Identification & Overview
- **Equipment Model**: Mabuchi RS-380 / RS-380PH Series Brushed DC Motor
- **Asset ID Tag**: `RS380-MOT-01`
- **Application**: Industrial Rotating Testbed / Actuator
- **Power Source**: 3S–4S Lithium-ion / Regulated Bench DC Supply (12.0 V nominal)
- **Drive Electronics**: L298N Dual Full-Bridge Driver / High-Current MOSFET H-Bridge
- **Data Acquisition Controller**: ESP32 dual-core Xtensa 32-bit MCU @ 240 MHz

---

## 2. Electrical Specifications
| Parameter | Minimum | Nominal | Maximum | Units |
| :--- | :--- | :--- | :--- | :--- |
| **Operating Voltage ($V_{\text{in}}$)** | 6.0 | 12.0 | 14.4 | V |
| **Terminal Voltage at Armature** | 5.0 | 11.8 | 12.5 | V |
| **No-Load Current ($I_0$)** | 0.28 | 0.42 | 0.50 | A |
| **Rated Load Operating Current ($I_{\text{rated}}$)** | 1.40 | 1.85 | 2.50 | A |
| **Overload Warning Current** | — | 3.20 | 3.80 | A |
| **Stall Current ($I_{\text{stall}}$)** | 4.20 | 4.80 | 5.50 | A |
| **Software E-Stop / Trip Threshold** | — | **4.50** | — | A |
| **Terminal Resistance ($R_a$)** | 2.1 | 2.4 | 2.8 | $\Omega$ |
| **Armature Inductance ($L_a$)** | 0.8 | 1.1 | 1.5 | mH |

---

## 3. Mechanical & Rotational Specifications
| Parameter | Value | Units | Notes |
| :--- | :--- | :--- | :--- |
| **Rated Speed (No-Load)** | 7,400 | RPM | at 12.0 V DC input |
| **Rated Speed (Nominal Load)** | 5,800 – 6,200 | RPM | with standard dynamometer coupling |
| **Rotor Shaft Diameter** | 2.30 | mm | Stainless steel ground shaft |
| **Shaft Extension Length** | 12.5 | mm | Flat D-cut face |
| **Rotor Inertia ($J$)** | 12.5 | $\text{g}\cdot\text{cm}^2$ | 3-slot armature core |
| **Direction of Rotation** | Bi-directional | — | Reversible via H-Bridge (IN1/IN2) |

---

## 4. Bearings, Brushes & Mechanical Construction
- **Bearings**: Dual sintered porous bronze sleeve bushings (self-aligning, oil-impregnated).
- **Carbon Brushes**: Dual carbon-graphite contact brushes with copper shunt wires and beryllium copper leaf springs.
- **Commutator**: 3-segment hard copper commutator ring insulated with mica.
- **Housing**: Zinc-coated deep drawn steel cylinder with integrated flux ring.
- **Ventilation**: Axial cooling airflow slots on front drive cap.

---

## 5. Environmental & Thermal Limits
- **Nominal Operating Temperature**: 25.0 °C to 45.0 °C
- **Thermal Warning Threshold**: **55.0 °C** (Casing temperature via DS18B20)
- **Critical Thermal Shutdown Threshold**: **70.0 °C** (Immediate firmware shutdown)
- **Baseline Vibration Envelope**: $0.15\,\text{g}$ to $0.35\,\text{g}$ (RMS mechanical acceleration)
- **Vibration Alarm Limit**: $>0.75\,\text{g}$ (Investigate bearing wear or shaft misalignment)
