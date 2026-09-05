# Phase 2C Synchronization Layer

The `StateSynchronizer` forms the Phase 2C boundary of the Digital Twin Core. Its primary responsibility is to ensure that the generated `HealthyExpectedState` (from the physics models) is temporally and contextually aligned with the inbound `ObservedState` (from telemetry) *before* any residual analysis or fault detection occurs.

## Design Philosophy
1. **Determinism over Heuristics**: If the timestamp mismatch exceeds a specified tolerance (default: 0.1s), synchronization explicitly fails rather than "guessing" or interpolating.
2. **Quality Propagation**: If the incoming `ObservedState` is marked `INVALID` or `INSUFFICIENT_DATA`, synchronization aborts, preventing polluted data from triggering false-positive causal deviations.
3. **No Upstream Feedback**: The synchronization layer reads from the `ObservedState`, but it does *not* feed this back into the `HealthyReferenceModel`. The physics baseline remains pure.

## Synchronization Rules

The `StateSynchronizer` executes a rigid checklist. Any failure returns `is_synchronized = False` with an explicit status enum.

1. **Missing Observation**: 
   - Rule: If `observed` is None.
   - Output: `MISSING_OBSERVATION`
2. **Engine Identity Mismatch**:
   - Rule: If `observed.engine_id != expected.engine_id`.
   - Output: `ENGINE_MISMATCH`
3. **Data Quality Checks**:
   - Rule: If `observed.data_quality` is `INVALID` or `INSUFFICIENT_DATA`.
   - Output: `INVALID_OBSERVATION` or `INSUFFICIENT_DATA` respectively.
4. **Out-of-Order Sequences**:
   - Rule: If `observed.sequence_number <= last_sequence_number` (excluding 0, which is treated as a reset).
   - Output: `OUT_OF_ORDER`
5. **Stale Observations**:
   - Rule: If `observed.timestamp < expected.timestamp - tolerance`
   - Output: `STALE_OBSERVATION`
6. **Future / Unaligned Timestamps**:
   - Rule: If `abs(observed.timestamp - expected.timestamp) > tolerance`
   - Output: `TIMESTAMP_MISMATCH`

If all rules pass, the result is `SYNC_SUCCESS` (or `DEGRADED_OBSERVATION` if data quality was `DEGRADED`).

## Downstream Impact

In `DigitalTwinEngine.process_step`:
- If `is_synchronized == False`: The `ResidualAnalyzer` and `CausalAnalyzer` are entirely bypassed. The final `DigitalTwinState` will report a status of `SYNC_FAILED` (or `INSUFFICIENT_DATA`), maintaining system safety against noisy inputs.
- If `is_synchronized == True`: Residual calculation and causal analysis proceed identically as they did in Phase 2B.
