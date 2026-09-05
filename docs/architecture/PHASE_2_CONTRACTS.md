# Phase 2A: Digital Twin Data Contracts

## Overview
Phase 2A establishes the authoritative data contracts for the Digital Twin Core. This phase resolves the ambiguity of previous dictionary-based states and imposes a strict type-safe, explicitly segregated schema for the Twin's lifecycle.

These contracts serve as the foundation for Phase 2B (Telemetry Ingestion & Calibration), Phase 2C (State Estimation UKF), and Phase 3 (Machine Learning).

## Architectural Principles

1. **Strict Separation of Concerns**:
   - The **Physical Twin** (real-world engine) produces observations via sensors.
   - The **Digital Twin Physics** (Module 01) produces expected baseline behaviors.
   - The **Digital Twin State Estimator** produces an estimated actual state (the authoritative "Twin").
   - These three concepts must never be merged or overwritten in place.

2. **Strong Typing & Dataclasses**:
   - Previously, states were managed as loosely-typed Python dictionaries (`Dict[str, float]`).
   - Phase 2A mandates Python `@dataclass` structures for all boundaries. 

3. **Data Quality Awareness**:
   - Every observation and the final twin state must explicitly declare its data quality and confidence bounds.

## Contract Definitions

All models reside in `src/digital_twin/models/`.

### 1. `DigitalTwinState` (The Master Container)
The root object that aggregates the entire state of the twin at a specific timestamp.
- **Timestamp & IDs**: Temporal and spatial identity.
- **Status & Confidence**: Overall health and data quality of the twin.
- **Sub-states**:
  - `operating_context`: Environmental and control inputs.
  - `health_state`: Degradation and fault injection profiles.
  - `observed_state`: Raw or pre-processed telemetry (The Physical Twin).
  - `healthy_expected_state`: Baseline physical targets (The Expected Twin).
  - `estimated_actual_state`: Best estimate of reality (The Actual Twin).
  - `residual_state`: Delta between observed and expected.

### 2. `OperatingContext`
Environmental variables (altitude, ambient temp/pressure) and pilot control inputs (throttle, pitch).

### 3. `HealthState`
Tracks physical degradation (e.g., turbo efficiency loss, sensor bias) and injected faults. Used primarily for simulations and health tracking.

### 4. `ObservedState`
The *truth* as reported by the physical engine's telemetry (Module 02). 
- All parameters are `Optional[float]` because sensor data may drop out.
- Contains an explicit `data_quality` string ("GOOD", "MISSING", "DEGRADED").
- **Crucial Rule**: Telemetry ingestion logic is strictly separated from the schema definition.

### 5. `HealthyExpectedState`
The *truth* as reported by the Module 01 Physics models, assuming a perfectly healthy engine.
- Contains all 19 Category C parameters.
- Default values are physical zeros or baseline ISA day constants, not `None`.

### 6. `EstimatedActualState`
The *truth* as estimated by the Digital Twin core (e.g., via UKF or Alpha Filter).
- Represents the true current state of the engine, accounting for degradation, faults, and measurement noise.

### 7. `ResidualState` & `ParameterResidual`
Explicitly tracks the difference between `ObservedState` and `HealthyExpectedState` for each parameter.
- `ParameterResidual`: Dataclass containing `expected`, `observed`, `residual`, `relative_error`, and `quality`.
- Handles `NaN`, `Inf`, and `None` gracefully without crashing the analysis pipeline.

## Migration from Phase 1
- `twin_internal_state.py` has been completely deleted and superseded by `EstimatedActualState` and `HealthState`.
- `expected_state.py` has been deleted and replaced by `HealthyExpectedState` to clarify its role as a healthy baseline.
- `twin_engine.py` orchestrator has been updated to ingest telemetry externally rather than tightly coupling to a pipeline inside the state classes.

## Next Steps (Phase 2B & 2C)
With these contracts in place, the system is ready to implement Unscented Kalman Filters (UKF) for state estimation, robust telemetry synchronization, and eventually, failure prognostics.
