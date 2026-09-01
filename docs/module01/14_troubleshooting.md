# Module 01 — Troubleshooting & Diagnostic Guide

## Common Ingestion Issues & Remedies

### 1. `unresolved_clock_total` Metric Increments
- **Symptom**: `unresolved_clock_total` counter increases; `normalized_source_utc` is `None`.
- **Cause**: Source timestamp domain is `ECU_BOOT` or `MONOTONIC` but no active `ClockMapping` calibration has been provided, or calibration is expired (`now_utc > valid_until_utc`).
- **Remedy**: Provide a valid `ClockMapping` instance via `ClockMapper.set_clock_mapping()`. Note: Physical measurement validity (`is_physically_valid = True`) remains unaffected.

### 2. `records_physically_invalid_total` Metric Increments
- **Symptom**: Incoming measurement is marked `INVALID`, `OUT_OF_RANGE`, or `RATE_OF_CHANGE_VIOLATION`.
- **Cause**: Signal value violates min/max physical plausibility limits or max rate-of-change step delta configured in `configs/limits/sensor_validity_limits.yaml`.
- **Remedy**: Check sensor calibration or update plausibility limits if configured bounds are overly strict for test conditions.

### 3. `duplicate_total` / `conflicting_payload_total` Metric Increments
- **Symptom**: `duplicate_total` or `conflicting_payload_total` metric increases.
- **Cause**: Network adapter retransmitted packets or payload sequence numbers arrived out of order.
- **Remedy**: Check network connection or stream adapter sequence generation. Raw packets are recorded safely in `RawStore`.
