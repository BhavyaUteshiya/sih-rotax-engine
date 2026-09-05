# Module 02 — 09. TAPAS-BH-201 Reference Configuration & Final Provenance Audit

## 1. Overview & Information Taxonomy
Module 02 is a **generic, configurable aero piston engine simulation framework**. It uses the **TAPAS-BH-201 (Rustom-II)** MALE UAV platform and the **DRDO Indigenous 180 HP Aero Engine** as its primary reference configuration.

### Multi-Tier Information Taxonomy
To avoid misattribution, the architecture maintains strict separation between four information categories:

1. **Category A — TAPAS-BH-201 Aircraft Information**: Official DRDO airframe capabilities (MALE UAV, twin-engine ISR platform, target ceiling 30,000 ft, demonstrated altitude 28,000 ft, target endurance 24 h, demonstrated endurance 18 h).
2. **Category B — Historical/Imported Propulsion Information**: Historical developmental test configurations (e.g. Austro 180 HP class engines used during early flight trials).
3. **Category C — Indigenous DRDO 180 HP UAV Engine Information**: Official DRDO indigenous 180 HP engine facts (180 HP class, 4-stroke, 4-cylinder, turbocharged, liquid-cooled, FADEC, Constant-Power Alt ~11,000 ft, Demonstrated Test Alt ~17,664 ft).
4. **Category D — Engineering Estimates**: Internal physics coefficients ($2.0\text{ L}$ displacement, $0.55\text{ kg}\cdot\text{m}^2$ inertia, compression ratio 17.5, MAP max $220\text{ kPa}$, gear speed ratio $0.65$). All Category D parameters are explicitly tagged `ESTIMATED` with `calibration_required: true`.

---

## 2. Complete Source Traceability Matrix

| Parameter | Value | Unit | Classification | Source | Confidence | Calibration Req? | Implementation Status |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Engine Identity** | `TAPAS_BH201_INDIGENOUS_180HP_DIESEL` | Text | `OFFICIAL` | DRDO_PUBLIC_RELEASE | HIGH | No | CONFIGURED |
| **Engine Class** | 180 HP-Class UAV Diesel | Text | `OFFICIAL` | DRDO_PUBLIC_RELEASE | HIGH | No | CONFIGURED |
| **Cycle Type** | 4-Stroke Reciprocating | Text | `OFFICIAL` | DRDO_PUBLIC_RELEASE | HIGH | No | CONFIGURED |
| **Fuel Type** | Diesel / Kerosene (Jet-A) | Text | `REPORTED` | DEFENSE_TECHNICAL_REPORTS | HIGH | No | CONFIGURED |
| **Cooling** | Liquid Cooled | Text | `OFFICIAL` | DRDO_PUBLIC_RELEASE | HIGH | No | CONFIGURED |
| **Aspiration** | Turbocharged | Text | `OFFICIAL` | DRDO_PUBLIC_RELEASE | HIGH | No | CONFIGURED |
| **Control System** | FADEC | Text | `OFFICIAL` | DRDO_PUBLIC_RELEASE | HIGH | No | CONFIGURED |
| **Cylinder Count** | 4 | Count | `OFFICIAL` | DRDO_PUBLIC_RELEASE | HIGH | No | CONFIGURED |
| **Takeoff Rated Power** | 180.0 | HP | `OFFICIAL` | DRDO_PUBLIC_RELEASE | HIGH | No | CONFIGURED |
| **Takeoff Power (SI)** | 134,226.0 | W | `DERIVED` | UNIT_CONVERSION | HIGH | No | DERIVED |
| **Constant Power Alt** | 3352.8 (11,000 ft) | m | `OFFICIAL` | DRDO_PUBLIC_RELEASE | HIGH | No | CONFIGURED |
| **Demonstrated Test Alt** | 5384.0 (17,664 ft) | m | `OFFICIAL` | DRDO_PUBLIC_RELEASE | HIGH | No | CONFIGURED |
| **Target Operating Alt** | 9144.0 (30,000 ft) | m | `OFFICIAL` | DRDO_PUBLIC_RELEASE | HIGH | No | CONFIGURED |
| **Demonstrated Alt** | 8534.4 (28,000 ft) | m | `OFFICIAL` | DRDO_PUBLIC_RELEASE | HIGH | No | CONFIGURED |
| **Target Endurance** | 24.0 | Hours | `OFFICIAL` | DRDO_PUBLIC_RELEASE | HIGH | No | CONFIGURED |
| **Demonstrated Endurance**| 18.0 | Hours | `OFFICIAL` | DRDO_PUBLIC_RELEASE | HIGH | No | CONFIGURED |
| **Engine Count** | 2 (Twin-Engine) | Count | `OFFICIAL` | DRDO_PUBLIC_RELEASE | HIGH | No | CONFIGURED |
| **Engine Displacement** | 0.0020 (2.0 L) | m³ | `ESTIMATED` | ENGINEERING_ESTIMATE | MEDIUM | **Yes** | CONFIGURED |
| **Rotational Inertia** | 0.55 | kg·m² | `ESTIMATED` | ENGINEERING_ESTIMATE | LOW | **Yes** | CONFIGURED |
| **Compression Ratio** | 17.5 | Ratio | `ESTIMATED` | ENGINEERING_ESTIMATE | MEDIUM | **Yes** | CONFIGURED |
| **Max MAP (MAP_max)** | 220,000.0 (2.2 bar) | Pa | `ESTIMATED` | ENGINEERING_ESTIMATE | MEDIUM | **Yes** | CONFIGURED |
| **Compressor Ratio** | 2.4 | Ratio | `ESTIMATED` | ENGINEERING_ESTIMATE | MEDIUM | **Yes** | PLANNED |
| **Compressor Efficiency**| 0.78 | Ratio | `ESTIMATED` | ENGINEERING_ESTIMATE | LOW | **Yes** | PLANNED |
| **Turbine Efficiency** | 0.75 | Ratio | `ESTIMATED` | ENGINEERING_ESTIMATE | LOW | **Yes** | PLANNED |
| **Speed Ratio (N_prop/N_eng)**| 0.65 | Ratio | `ESTIMATED` | ENGINEERING_ESTIMATE | MEDIUM | **Yes** | CONFIGURED |
| **Reduction Ratio (N_eng/N_prop)**| 1.53846 | Ratio | `DERIVED` | MATHEMATICAL_RECIPROCAL | HIGH | No | DERIVED |
| **Gearbox Efficiency** | 0.97 | Ratio | `ESTIMATED` | ENGINEERING_ESTIMATE | HIGH | **Yes** | CONFIGURED |
| **Propeller Diameter** | 1.85 | m | `REPORTED` | PUBLIC_DEFENSE_LITERATURE | MEDIUM | No | CONFIGURED |
| **Propeller Blade Count**| 3 | Count | `REPORTED` | PUBLIC_DEFENSE_LITERATURE | HIGH | No | CONFIGURED |
| **Propeller Torque Coeff C_q**| 0.014 | Coeff | `ESTIMATED` | ENGINEERING_ESTIMATE | LOW | **Yes** | PLANNED |
| **Propeller Thrust Coeff C_t**| 0.085 | Coeff | `ESTIMATED` | ENGINEERING_ESTIMATE | LOW | **Yes** | PLANNED |

---

## 3. Strict Provenance Validation Rules

1. **`OFFICIAL` Rule**: Parameter is classified `OFFICIAL` **only** if supported by an explicit DRDO public release source (`source: "DRDO_PUBLIC_RELEASE"`).
2. **`ESTIMATED` Rule**: All engineering assumptions and estimates **must** be marked `calibration_required: true`.
3. **`DERIVED` Rule**: All derived parameters must state their mathematical origin (`source: "UNIT_CONVERSION"` or `"MATHEMATICAL_RECIPROCAL"`).
4. **Target vs. Demonstrated Rule**: Design requirements (target altitude 30,000 ft, target endurance 24 h) are strictly separated from demonstrated flight test performance (demonstrated altitude 28,000 ft, demonstrated endurance 18 h).
