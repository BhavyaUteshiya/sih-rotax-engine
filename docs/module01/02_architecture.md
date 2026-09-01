# Module 01 Architecture Specification

## Pipeline Flow Diagram
```
+-----------------------------------------------------------------------------------+
| 1. RAW ACQUISITION STAGE                                                          |
|    Capture DeepImmutableRawPacket, compute payload_sha256 & deterministic packet_id|
+-----------------------------------------------------------------------------------+
                                          │
                                          ▼
+-----------------------------------------------------------------------------------+
| 2. DECODING & NORMALIZATION STAGE                                                 |
|    Decode protocol payload -> DecodedSignal -> UnitNormalizer (SI Conversion)     |
+-----------------------------------------------------------------------------------+
                                          │
                                          ▼
+-----------------------------------------------------------------------------------+
| 3. VALIDATION & QUALITY STAGE                                                     |
|    ValidityValidator (Plausibility & Rate-of-Change checks)                       |
|    Assign ValidityStatus, TemporalQuality, TransformationMetadata, IntegrityStatus  |
+-----------------------------------------------------------------------------------+
                                          │
                                          ▼
+-----------------------------------------------------------------------------------+
| 4. BUFFERING & STORAGE STAGE                                                      |
|    RingBuffer per channel -> Append RawStore (Arrival) & NormalizedStore (Event)   |
+-----------------------------------------------------------------------------------+
                                          │
                                          ▼
+-----------------------------------------------------------------------------------+
| ON-DEMAND TEMPORAL SYNCHRONIZATION                                                |
|    TimestampSynchronizer -> TelemetryFrame v1.0.0 (Consumer View)                |
+-----------------------------------------------------------------------------------+
```

## Subsystem Component Boundaries
- **Acquisition**: `CanInterface`, `EcuInterface`, `FileSourceInterface`.
- **Decoding**: `CanDecoder`, `JsonDecoder`, `CsvDecoder`.
- **Normalization**: `UnitNormalizer`.
- **Validation**: `ValidityValidator`.
- **Timestamps**: `ClockMapper`.
- **Buffering**: `RingBuffer`.
- **Synchronization**: `TimestampSynchronizer`.
- **Storage**: `RawStore`, `NormalizedStore`, `StorageRecoveryStateMachine`.
- **Observability**: `MetricsTracker`.
