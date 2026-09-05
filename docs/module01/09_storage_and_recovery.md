# Module 01 — Tiered Storage & Recovery Architecture

## Datastores & Authoritative Ordering
- **`RawStore`**: Append-only JSONL log with Base64 raw bytes. **`ARRIVAL_ORDER` is authoritative**. Idempotent by `packet_id`. Provides `get_by_packet_id(packet_id)` for raw lineage resolution.
- **`NormalizedStore`**: Time-series store of `SensorMeasurement` records. **`SOURCE_EVENT_ORDER` is authoritative**. Provides `get_ordered_records()` sorted deterministically by `(source_event_timestamp, stream_id, sequence_number, packet_id)`.

## Storage Recovery State Machine
Transitions:
`NORMAL` $\rightarrow$ `STORAGE_FAILURE` $\rightarrow$ `EMERGENCY_BUFFERING` $\rightarrow$ `STORAGE_RECOVERED` $\rightarrow$ `DRAINING_FLUSH` $\rightarrow$ `NORMAL`

- Under storage failures, raw packets enter a bounded emergency buffer.
- When storage recovers, `start_draining()` flushes buffered packets idempotently to `RawStore`.
- Any dropped packets during sustained buffer overflow are counted in `dropped_records_total`.
