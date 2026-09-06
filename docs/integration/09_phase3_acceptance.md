# Phase 3: Telemetry & Ingestion Architecture

## 1. Architecture
The Phase 3 telemetry ingestion pipeline safely receives serialized telemetry data and integrates it into the Phase 2 Digital Twin Engine.

**Live Path:**
`TelemetryPacket (Source) → JSON Serialization → InMemoryTransport → JSON Deserialization → TelemetryValidator → TelemetryNormalizer → ObservedState → DigitalTwinEngine`

**Replay Path:**
`JSONL/CSV Dataset → DatasetReplayer → TelemetryPacket → TelemetryValidator → TelemetryNormalizer → ObservedState → DigitalTwinEngine`

## 2. Telemetry Packet
The `TelemetryPacket` is a frozen dataclass mapping precisely to the `docs/integration/02_telemetry_contract.md`. It preserves engineering values, unit metadata, simulator context, and absolute timestamps/sequence tracking.

## 3. Serialization
Deterministic JSON UTF-8 byte serialization isolates the transport layer from runtime Python object states.

## 4. Validation
`TelemetryValidator` actively intercepts physically invalid frames (NaN, +/- Infinity, None) or malformed packets without corrupting `DigitalTwinEngine` state. Zero (0.0) and missing channels are safely handled.

## 5. Normalization & Frame Assembly
`TelemetryNormalizer` reconstructs scattered parameter-level packets into unified `ObservedState` multi-channel frames. Missing telemetry channels remain safely mapped as `None`.
*   **Sequence Safety**: Out-of-order and strictly stale packets are dropped immediately at the boundary.
*   **Multi-Engine**: Sequence state tracking is strictly partitioned by engine identity. Engine 1 sequences will never contaminate Engine 2 frames.

## 6. Transport
`InMemoryTransport` guarantees thread-safe FIFO packet routing. Exact input `raw_bytes` are encapsulated inside a `DeepImmutableRawPacket` along with an explicit SHA-256 byte digest, strictly isolating interpretation logic from transport mechanics. 

## 7. Replay
The `DatasetReplayer` deterministically parses historical JSONL/CSV outputs natively back into `ObservedState` via the same Phase 3 Validator and Normalizer, maintaining total parity with live paths.

## 8. ObservedState Handoff
Phase 3 delegates all physics, estimations, and health decisions fully to Phase 2. `DigitalTwinEngine.process_step()` natively accepts the assembled Phase 3 output untouched.

## 9. Limitations
*   No physical SocketCAN / CAN hardware implementation.
*   Data Quality metrics (total published/received/dropped counters) are omitted from Phase 3 Transport to prevent scope bloat, delegating data quality safety fully to Phase 2.

## 10. Future Hardware Boundary
The isolated `InMemoryTransport` interface provides an exact drop-in hook for future `SocketCANTransport` extensions without requiring Phase 3 reconstruction.
