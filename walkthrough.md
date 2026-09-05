# Phase 1F: Propeller Physics & Aerodynamic Coupling

## Background
Phase 1F implements the final physical subsystem for the Phase 1 Physical Foundation: the propeller aerodynamic model. This module converts propeller RPM, derived from the engine through the gearbox, into aerodynamic thrust, torque, and power based on standard non-dimensional propeller physics. 

## Changes Made
### 1. Propeller Model (`src/digital_twin/physics/propeller.py`)
- Created `PropellerInput` and `PropellerState` dataclasses.
- Implemented `PropellerModel` to calculate advance ratio ($J$), thrust coefficient ($C_T$), and torque coefficient ($C_Q$) using a smooth surrogate polynomial suitable for fixed-pitch UAV propellers.
- Added explicit regularization to prevent division-by-zero or numerical instability when engine/propeller RPM approaches 0.
- Implemented strict formulas for aerodynamic thrust, aerodynamic drag torque, and absorbed power with precise dimensional scaling ($D^4$ for thrust, $D^5$ for torque).

### 2. Validation (`scratch/test_propeller.py`)
- Added a suite of 31 unit and integration tests enforcing dimensional strictness, zero-RPM stability, environmental scaling, and power-envelope compatibility.
- Ensured integration test readiness by proving the model cleanly accepts inputs from upstream phases (1A-Atmosphere, 1E-Engine Dynamics).

### 3. Documentation & Registries
- Wrote full documentation for the module in `docs/physics/1F_propeller/` covering theory, formulas, parameters, and deferred item implementation notes.
- Updated `docs/PHYSICS_FORMULA_REGISTRY.txt` with PROP-01 through PROP-07.
- Expanded the McCormick reference in `docs/REFERENCES.md` and added the Phase 1F Surrogate Model reference.

### 4. Deferred Items Handled
- **1D Rated-Condition Fuel Validation:** Tightened the fuel flow bounds in `test_combustion.py` to assert consumption closer to the ~33 L/h real-world Rotax metric.
- **1E Placeholder Tests:** Formally deferred the integration tests in `test_engine_dynamics.py` with docstrings explicitly moving system-wide regression into the Phase 1 Integration Phase.
- **1E Equivalent Inertia:** Documented the exact coupled inertia relationship ($J_{eq} = J_{engine} + J_{prop} / r_g^2$) in the implementation notes, enforcing architectural decoupling until full system integration.

### 5. Correction Pass — Calibration & Data Consistency
A post-implementation review found that the initial coefficients (D=1.9 m, CQ_static=0.015, CT_static=0.12) produced ~116.7 kW absorbed power at the nominal operating point — exceeding the Rotax 914 shaft-power envelope of ~71.3 kW.

**Corrections applied:**
- Diameter standardized to canonical 1.7 m (from `ROTAX_914_ENGINE_DATA.txt`).
- CT_STATIC recalibrated to 0.075 (from engine data).
- CQ_STATIC recalibrated to 0.0125 (from engine data).
- Decay slopes adjusted to CT_J_COEFF = -0.035, CQ_J_COEFF = -0.008.
- 1E `engine_dynamics.py` prop surrogate updated to match (D=1.7 m, CQ_STATIC=0.0125).
- All tests, documentation, and parameter files reconciled.

**Corrected nominal operating point (actual runtime values):**
- Thrust ≈ 880 N, Torque ≈ 214 Nm, Power ≈ 53.6 kW, Efficiency ≈ 0.66.
- Absorbed power is well within the 1E shaft-power envelope.

## Validation Results
All 137 tests across the physical foundation (Phases 1A through 1F) successfully pass, confirming that the entire physical stack is numerically stable, causally intact, and power-consistent.

---

# Digital Twin Phase 6b: Empirical Expected State
## Background
The previous Digital Twin implementation contained a critical architectural weakness: it generated the `ExpectedState` by directly copying the `sim_state` variables from the Module 01 physical model. Because the `ObservedState` (telemetry) is just the transmitted version of the exact same `sim_state`, the two states would always perfectly match—even if a fault occurred in the physical engine. This resulted in near-zero residuals at all times, making the Digital Twin incapable of independently detecting faults.

## Changes Made

### 1. Empirical Predictive Model (`src/digital_twin/physics/expected_behavior.py`)
We completely replaced the direct `sim_state` copying mechanism with an **Independent Empirical Baseline Model**. The `ExpectedState` is now generated *deterministically* based on the `operating_context` (e.g., pilot throttle command and ambient conditions). 

Key Engineering Approximations `[ENGINEERING_APPROXIMATION]` include:
- **MAP**: Linearly mapped from 0.35 bar (idle) to 1.15 bar (max continuous) based on the input throttle percentage.
- **RPM**: Linearly predicted based on MAP and assumed standard propeller load.
- **Airflow**: Volumetric efficiency estimate driven by expected RPM and MAP.
- **Fuel Flow**: Calculated to maintain an AFR of ~14.7 (scaling richer at high power).
- **Temperatures (EGT, CHT, etc.)**: Derived directly from the combustion heat (Fuel Flow).

### 2. Orchestrator Integration (`src/digital_twin/services/twin_engine.py`)
We updated `DigitalTwinEngine.process_step()` to pass the `operating_context` directly into `ExpectedBehaviorModel.from_simulation_state()`. This cleanly decouples the Expected State generation from the internal variables of the Module 01 physics simulation.

## Validation Results
We created a test script (`scratch/test_empirical_expected_state.py`) that inputs a 100% throttle command into the new model and intentionally injects a fault into the simulated telemetry where MAP drops to 0.50 bar.

The Digital Twin now successfully catches the anomaly because its independent Expected State predicts the correct values:

```
Testing Empirical Expected State Generation...

--- EXPECTED STATE (from Empirical Model with Throttle=100%) ---
MAP: 1.15 bar (Should be ~1.15)
RPM: 5800 (Should be ~5800)

--- OBSERVED STATE (from Telemetry / Faulted) ---
MAP: 0.50 bar (Faulted to 0.5)
RPM: 5000

--- RESIDUALS ---
MAP Residual: -0.65 (Warning: False)
RPM Residual: -800.00 (Warning: False)

--- TWIN STATUS ---
Status: DEVIATION_DETECTED
Confidence: 0.85
Active Warnings: 4
```

*(Note: The MAP and RPM residuals register correctly. The warnings flag reads false directly on the residual object because the 2.0-second debounce timer suppresses transient warnings, but the overall `Twin Status` correctly elevates to `DEVIATION_DETECTED` due to hard limits being breached).*

## Conclusion
The Digital Twin now functions as a true, independent baseline reference that can cross-check the physical engine's output against the pilot's commands and environmental conditions.
