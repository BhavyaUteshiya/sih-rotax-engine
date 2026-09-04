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
