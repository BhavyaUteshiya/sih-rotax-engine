# Phase 1F: Propeller Validation

## 1. Scope of Validation
The goal of validating the Phase 1F Propeller Model is to prove that the core dimensional structure, scaling logic, numerical stability, and interfaces are robust, and that the nominal operating point is compatible with the engine shaft-power envelope. It is **not** intended to match an exact proprietary manufacturer dataset, as one was not provided for this specific propeller.

## 2. Calibration Correction History
The initial Phase 1F implementation used D = 1.9 m and C_Q_static = 0.015, which produced approximately 116.7 kW absorbed power at the nominal operating point — exceeding the Rotax 914 rated power envelope.

The correction aligned the model to the canonical project engine data (`ROTAX_914_ENGINE_DATA.txt`):
- **D**: 1.9 m → 1.7 m
- **CT_STATIC**: 0.12 → 0.075
- **CQ_STATIC**: 0.015 → 0.0125
- **CT_J_COEFF**: -0.05 → -0.035
- **CQ_J_COEFF**: -0.01 → -0.008

## 3. Nominal Operating Point (Calibration Point)
The following values are ACTUAL runtime outputs at the calibration operating point:

| Parameter | Value |
|---|---|
| Engine RPM | 5800 |
| Propeller RPM | 2388.2 |
| Airspeed | 40.0 m/s |
| Air density | 1.225 kg/m³ |
| Diameter | 1.7 m |
| Advance ratio (J) | 0.591 |
| C_T at J | 0.0543 |
| C_Q at J | 0.00777 |
| **Thrust** | **880 N** |
| **Torque** | **214 Nm** |
| **Absorbed Power** | **53.6 kW** |
| **Efficiency** | **0.66** |

**Classification**: This is a calibration/sanity point, NOT a manufacturer-validated point.

## 4. Power Compatibility
The 1E shaft power at rated conditions (85.8 kW indicated, minus ~23.8 Nm friction at 607.4 rad/s) is approximately **71.3 kW**.

The propeller absorbed power of **53.6 kW** is well within this envelope, leaving appropriate margin for:
- gearbox losses (~2% per 1E)
- auxiliary loads (not yet modeled)
- the fact that the surrogate coefficients are generic calibration values

## 5. Test Suite
A suite of 31 tests (`scratch/test_propeller.py`) was executed to confirm:
- **Canonical Diameter**: Explicitly tested as 1.7 m.
- **Mathematical Correctness**: RPM/rev-s/rad-s conversions are strict.
- **Dimensional Stability**: All equations follow correct physical scaling.
- **Zero-RPM Edge Cases**: Thrust, torque, and power cleanly evaluate to 0.
- **Density Dependence**: Higher density → proportionally higher thrust and torque.
- **Airspeed Dependence**: Higher airspeed raises J, reducing coefficients via surrogate.
- **Power Consistency**: P = ωQ holds exactly.
- **Efficiency Constraints**: η stays between 0 and 1.0.
- **Power Envelope**: Absorbed power at nominal point does not exceed 1E shaft power (~71.3 kW).
- **Sign Convention**: Propeller torque is positive as an opposing load.
- **Integration Readiness**: Model cleanly consumes upstream phase outputs.

## 6. Results
All 31 tests pass. Full 1A–1F regression (137 tests) passes with no upstream regressions.

## 7. Limitations
- The exact coupled propeller for the Rotax 914 UAV application is not known from authoritative public data. The C_T and C_Q surrogates are generic calibration values, not a proprietary manufacturer map.
- Propulsive efficiency is a derived quantity from the surrogate model and should not be interpreted as exact measured performance.
