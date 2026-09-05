# Module 01 — Public API Contracts & Downstream Interfaces

## Core Ingestion Interfaces
- `TelemetryIngestor`: `ingest_raw_packet(packet) -> bool`.
- `TelemetryPublisher`: `publish_frame(frame)`.
- `TelemetryConsumer`: `get_latest_frame()`, `get_frame_range(time_range)`.
- `LineageResolver`: `resolve_raw_packet(raw_packet_id)`, `resolve_measurement_lineage(measurement_id)`.
- `MetricsProvider`: `get_ingestion_metrics()`.

## Module 02 Contract (Simulation & Replay)
- `ISimulationTelemetrySink`: `inject_simulated_measurement(measurement)` (enforces `PhysicalOrigin.SIMULATOR` and `StateCategory.SIMULATED`), `inject_simulated_frame(frame)`.
- `IReplayTelemetryProvider`: `get_historical_stream(mission_id, time_range)`.
  > [!NOTE]
  > Module 01 provides the interface contract (`IReplayTelemetryProvider`) only. Mission-aware historical replay and physics reconstruction are deferred to Module 02.

## Module 03 Contract (Digital Twin Core Stream)
- `IDigitalTwinTelemetryStream`: `subscribe_actual_state(callback)` (subscribes strictly to `ACTUAL_MEASURED` telemetry streams), `unsubscribe(subscription_id)`.
  > [!NOTE]
  > Module 01 publishes actual telemetry streams; Module 01 DOES NOT perform digital twin estimation or store twin states.
