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

Where `Actual` is strictly prioritized based on parameter type:
1. **UKF-Estimated Fields (8 parameters)**: `[rpm, map_bar, turbo_rpm, airflow_kg_h, fuel_flow_kg_h, afr, cht_c, oil_temp_c]`
   - Uses `EstimatedActualState` if available and NOT prediction-only.
   - Fallback to `ObservedState`.
2. **Pass-Through Fields (11 parameters)**: (e.g. `oil_pressure_bar`, `thrust_n`)
   - Explicitly NEVER use `EstimatedActualState` since the UKF does not estimate them (they are healthy-reference pass-throughs).
   - Strictly uses `ObservedState`.

If an actual source is unavailable (or prediction-only for UKF), the actual value is set to `None` with source `NONE`, resulting in a `MISSING` status. It does NOT fabricate zero.

### Thresholds & Configuration
Each of the 19 standard parameters defines specific tolerances in `configs/digital_twin_config.yaml`:
- `warning_threshold`: The magnitude of acceptable relative deviation. Exceeding this triggers a `WARNING`.
- `critical_threshold`: The magnitude of severe deviation. Exceeding this triggers a `CRITICAL` alert.
- `denominator_floor`: A numerical stabilizer to prevent divide-by-zero or hyperbolic spikes in relative error when expected values are near zero.

Relative Error Calculation:
`Relative_Error = abs(Residual) / max(abs(Expected), denominator_floor)`

### Status Propagation & Confidence Semantics
Individual parameter statuses map to an overarching `DigitalTwinStatus`.
Confidence values are strictly deterministic engineering/calibration policy values reflecting the twin's confidence in its assessment of the engine state. They are NOT probabilities and do NOT imply ML/stochastic probability of engine health.

Aggregate priority is explicitly evaluated in this order to prevent conflating missing data with physical health:

1. **SYNC/INPUT FAILED** (e.g. `SYNC_FAILED`): Handled prior to residual analysis. Twin cannot evaluate. Confidence `0.0`.
2. **INSUFFICIENT/INVALID DATA**: If `missing_count + invalid_count > 0` (even if synchronized).
   - `DigitalTwinStatus.INSUFFICIENT_DATA`
   - Policy Confidence: `0.0` (Insufficient/invalid residual inputs block assessment. Data prevents meaningful evaluation).
3. **CRITICAL**: If `criticals_count > 0`.
   - `DigitalTwinStatus.DEVIATION_DETECTED`
   - Policy Confidence: `0.3` (Critical physical deviations severely degrade twin confidence).
4. **WARNING**: If `warnings_count > 0`.
   - `DigitalTwinStatus.DATA_QUALITY_DEGRADED`
   - Policy Confidence: `0.85` (Minor physical deviations slightly degrade twin confidence).
5. **DEGRADED OBSERVATION**: If all are `GOOD` but sensor data was degraded (`DEGRADED_OBSERVATION`).
   - `DigitalTwinStatus.DATA_QUALITY_DEGRADED`
   - Policy Confidence: `0.7` (Poor telemetry data quality caps overall confidence).
6. **SYNCHRONIZED**: Only when all are `GOOD` and sensors are valid.
   - `DigitalTwinStatus.SYNCHRONIZED`
   - Policy Confidence: Inherited from UKF estimator (nominally `1.0`).

## Causal Analyzer Integration
Residuals are propagated to the Causal Analyzer (`CausalAnalyzer`), which maps deviations onto a physical Directed Acyclic Graph (DAG) to determine if a deviation is a `PRIMARY_DEVIATION` (root cause) or a `PROPAGATED_DEVIATION` (downstream effect).

## Principles & Constraints
- **Strictly Deterministic:** No ML, AI, or statistical black-boxes.
- **Traceable Thresholds:** All thresholds must be justified numerical calibrations placed in standard configuration files.
- **Fail-Safe Confidence:** Unavailable data or invalid synchronization immediately degrades twin confidence to `0.0`.
