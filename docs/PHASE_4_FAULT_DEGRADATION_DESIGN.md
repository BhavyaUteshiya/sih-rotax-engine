# Phase 4 - Fault & Degradation Injection Layer Design

## 1. Purpose
The Fault & Degradation Injection Layer (Phase 4) creates a controlled, phenomenological simulation mechanism for generating realistic engine fault scenarios. It allows the Digital Twin system to transition a healthy engine physics simulation (`HealthyExpectedState`) into a degraded observation (`ObservedState`) that accurately reflects typical aero piston engine failure modes. 

This layer does NOT modify the approved baseline Phase 1 physics model nor does it alter the Phase 2 Digital Twin core. It functions entirely as a wrapper layer preparing data for later detection pipelines (Phase 5 ML and Phase 2 Health Aggregation).

## 2. Architecture
The architecture introduces two new components:
- `FaultScenario`: A configuration dataclass representing a specific deterministic fault (type, severity, start time, ramp duration).
- `FaultInjector`: A stateless service that accepts a `HealthyExpectedState` (Phase 1 output), applies the configured `FaultScenario` list, and produces an `ObservedState` containing the simulated degraded telemetry.

```text
[Phase 1] HealthyReferenceModel -> HealthyExpectedState
                                        ↓
                                  [FaultInjector] <--- [FaultScenario(s)]
                                        ↓
                                   ObservedState
                                        ↓
[Phase 2] DigitalTwinEngine (processes ObservedState & HealthyExpectedState)
```

## 3. Fault Model
The fault model relies on deterministic phenomenological shifts rather than deep micro-physical simulation. This avoids unnecessary complexity while providing perfectly controlled, explainable degradation data for the digital twin. 

## 4. Fault Scenarios
Four primary scenarios are currently supported:
1. **COOLING_DEGRADATION**: Simulates reduced coolant efficiency or radiator blockage.
2. **LUBRICATION_DEGRADATION**: Simulates oil pump wear, oil leaks, or filter blockage.
3. **AIRFLOW_RESTRICTION**: Simulates air filter blockage or intake manifold obstruction.
4. **TORQUE_DEGRADATION**: Simulates generic loss of mechanical output (e.g. friction, combustion efficiency loss not captured purely by airflow).

## 5. Severity Semantics
`severity` is a dimensionless simulation control variable strictly bounded between `0.0` (no effect) and `1.0` (maximum configured effect). It scales the phenomenological deviations linearly. 
**Note:** A severity of `1.0` does not necessarily mean "100% engine failure" in a physical sense. It represents the maximum extent of the *simulated deviation* configured for that scenario.

## 6. Instant vs Gradual Degradation
A scenario can be configured to occur instantaneously (by setting `ramp_duration=0.0`) or gradually over time. If `ramp_duration > 0.0`, the `effective_severity` linearly interpolates from `0.0` at `start_time` to `severity` at `start_time + ramp_duration`.

## 7. Parameter Effects
- **COOLING_DEGRADATION**: Increases `cht_c` (max +50.0°C) and `oil_temp_c` (max +20.0°C).
- **LUBRICATION_DEGRADATION**: Reduces `oil_pressure_bar` (max -2.0 bar, bounded at 0.0) and increases `oil_temp_c` (max +15.0°C).
- **AIRFLOW_RESTRICTION**: Reduces `airflow_kg_h` (max -50%), `map_bar` (max -40%), and `indicated_power_kw` (max -40%).
- **TORQUE_DEGRADATION**: Reduces `torque_n_m` (max -30%) and `thrust_n` (max -30%).

## 8. Assumption/Source Classification
All numerical constants defining the maximum parameter shifts (e.g., +50.0°C CHT) are **Engineering/Simulation Assumptions**. They do not represent official Rotax 914 UL/F limits. They are calibrated to provide clearly distinguishable signal deviations for the prototype's validation phases.

## 9. Integration with Telemetry / ObservedState
The output of the `FaultInjector` is an exact match for the `ObservedState` class, completely compatible with the Phase 2 `StateSynchronizer` and `DigitalTwinEngine` orchestrator. The Fault Injector leaves environmental parameters uncopied since they belong to the `OperatingContext`.

## 10. Test/Acceptance Matrix
The suite validates:
- Baseline copy integrity.
- Expected vector movement for all four faults.
- Severity scaling proportionally.
- Gradual and instant onset timing.
- Multiple simultaneous, overlapping faults.
- Safety clipping (preventing severity > 1.0 or oil pressure < 0.0).
- State immutability for disabled faults.

## 11. Known Limitations
- Environmental and context parameters (e.g. ambient temperature) are not explicitly copied through the injector.
- Complex cascading feedback loops (e.g. high CHT eventually reducing volumetric efficiency) are not simulated directly by the injector, as it operates statically on a snapshot of the expected state.

## 12. What Phase 4 Does NOT Implement
- Phase 4 does not perform ML training, fault detection, or anomaly isolation.
- It does not modify physical differential equations.
- It does not calculate Remaining Useful Life (RUL) or prescribe maintenance.

## 13. Interface Expected by Future Phase 5
Phase 5 (Machine Learning Anomaly Detection) will generate training data by running the Phase 1 physics model over various mission profiles, passing the `HealthyExpectedState` through the `FaultInjector` with randomly sampled `FaultScenario` arrays, and storing the resulting `[HealthyExpectedState, ObservedState, TrueFaultLabels]` tuples for supervised learning.
