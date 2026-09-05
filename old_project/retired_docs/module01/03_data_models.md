# Module 01 — Data Models Specification

## Core Data Models

### 1. `DeepImmutableRawPacket`
Represents an un-mutated wire payload captured upon pipeline entry.
- `packet_id`: Deterministic canonical identity string computed via SHA-256 over `f"{stream_id}:{sequence_number}:{source_timestamp_repr}:{payload_sha256}"`.
- `payload_sha256`: Lower-case 64-character hex SHA-256 hash over `raw_bytes`.
- `raw_bytes`: Immutable byte string.
- `metadata`: Frozen defensive copy dictionary (`MappingProxyType`).

### 2. `SensorMeasurement`
Granular representation of a single telemetry measurement.
- `value`: Canonical SI value (or `None` if physically invalid).
- `engineering_value`: Display value in engineering units (e.g. 5200.0 RPM).
- `unit_metadata`: `UnitMetadata` (raw, engineering, canonical SI, scale, offset).
- 4-Tier Quality: `ValidityStatus`, `TemporalQuality`, `TransformationMetadata`, `IntegrityStatus`.
- Usability Flags: `is_physically_valid`, `is_temporally_valid`, `is_sync_eligible`.
- Provenance: `PhysicalOrigin`, `TransportProtocol`, `ProcessingContext`, `StateCategory`.
- `timestamps`: `TimestampModel`.
- `lineage`: `MeasurementLineage`.

### 3. `TelemetryFrame` v1.0.0
Synchronized consumer transport snapshot aligned to a grid timestamp.
- `frame_time`: `FrameTime` multi-domain frame timestamp.
- `state_category`: **Derived summary convenience state field ONLY**. It MUST NOT override individual `SensorMeasurement.state_category` objects. Downstream modules MUST inspect `SensorMeasurement.state_category` for authoritative provenance.
- `measurements`: Mapping of `parameter_id` to `SensorMeasurement`.
- `sync_metadata`: `SyncMetadata`.
