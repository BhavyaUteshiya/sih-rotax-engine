# Phase 2E: Residual & Confidence Engine Design

## Overview
Phase 2E implements the final core component of the Digital Twin pipeline: The Residual and Confidence Engine.
This phase evaluates the deviations between expected physical behavior and observed/estimated actual behavior to determine the overall state and reliability of the engine representation.

## Architecture

The pipeline executes in the following sequence:

1. **Phase 1: Healthy Reference Model**
   Produces `HealthyExpectedState` derived purely from physical equations and inputs.
2. **Phase 2C: State Synchronization**
   Aligns asynchronous incoming telemetry (`ObservedState`) with the deterministic `HealthyExpectedState`.
3. **Phase 2D: State Estimation (UKF)**
   Fuses `HealthyExpectedState` and `ObservedState` to produce an `EstimatedActualState`, dealing with noise and hidden variables deterministically.
4. **Phase 2E: Residual & Confidence Analysis** (This Phase)
   Evaluates residuals between the expected reference and the actual state to generate `ResidualState`, trigger warnings/critical alerts, and assign a confidence score to the Digital Twin's accuracy.

## Residual Evaluation Mechanism

Residuals are defined as:
`Residual = Actual - Expected`

Where `Actual` is strictly prioritized as:
1. `EstimatedActualState` (if available and not prediction-only).
2. `ObservedState` (fallback if estimation is bypassed/unavailable).

### Thresholds & Configuration
Each of the 19 standard parameters defines specific tolerances in `configs/digital_twin_config.yaml`:
- `warning_threshold`: The magnitude of acceptable relative deviation. Exceeding this triggers a `WARNING`.
- `critical_threshold`: The magnitude of severe deviation. Exceeding this triggers a `CRITICAL` alert.
- `denominator_floor`: A numerical stabilizer to prevent divide-by-zero or hyperbolic spikes in relative error when expected values are near zero.

Relative Error Calculation:
`Relative_Error = abs(Residual) / max(abs(Expected), denominator_floor)`

### Status Propagation
Individual parameter statuses map to an overarching `DigitalTwinStatus`:
- If ANY parameter is `CRITICAL`: `DigitalTwinStatus.DEVIATION_DETECTED` (Confidence drops to 0.3).
- If ANY parameter is `WARNING`: `DigitalTwinStatus.DATA_QUALITY_DEGRADED` (Confidence drops to 0.7).
- If all are `GOOD` but sensor data was degraded: `DATA_QUALITY_DEGRADED` (Confidence drops to 0.85).
- If all are `GOOD` and sensors are valid: `SYNCHRONIZED` (Confidence derived from UKF, nominally 1.0).

## Causal Analyzer Integration
Residuals are propagated to the Causal Analyzer (`CausalAnalyzer`), which maps deviations onto a physical Directed Acyclic Graph (DAG) to determine if a deviation is a `PRIMARY_DEVIATION` (root cause) or a `PROPAGATED_DEVIATION` (downstream effect).

## Principles & Constraints
- **Strictly Deterministic:** No ML, AI, or statistical black-boxes.
- **Traceable Thresholds:** All thresholds must be justified numerical calibrations placed in standard configuration files.
- **Fail-Safe Confidence:** Unavailable data or invalid synchronization immediately degrades twin confidence to `0.0`.
