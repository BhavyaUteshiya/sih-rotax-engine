# Module 01 — Quality Metadata & Provenance

## 5-Dimensional Provenance
Every measurement carries explicit origin metadata:
1. `PhysicalOrigin`: `SENSOR`, `ECU`, `FADEC`, `SIMULATOR`, `DERIVED`, `UNKNOWN`.
2. `TransportProtocol`: `CAN`, `SOCKETCAN`, `FILE`, `MEMORY`, `API`, `NONE`.
3. `ProcessingContext`: `LIVE_STREAM`, `HISTORICAL_FILE`, `FLIGHT_REPLAY`, `SIMULATION_RUN`, `SYNTHETIC_GENERATION`.
4. `StateCategory`: `ACTUAL_MEASURED`, `DERIVED`, `SIMULATED`, `ESTIMATED`, `PREDICTED`.
5. `Lineage`: `MeasurementLineage` linking back to `raw_packet_id` and input sample IDs.

## Synthetic Demonstration Provenance Rule
Demonstration data adapters (`DemonstrationCanAdapter` and `MockEcuAdapter`) generate synthetic demonstration telemetry. They are explicitly tagged with:
- `PhysicalOrigin.SIMULATOR`
- `StateCategory.SIMULATED`
- `ProcessingContext.SYNTHETIC_GENERATION`

They NEVER claim to contain real hardware ECU/FADEC measurements.

## Simulation Injection Provenance Rule
`ISimulationTelemetrySink.inject_simulated_measurement()` enforces strict provenance rules:
- Requires BOTH `PhysicalOrigin.SIMULATOR` AND `StateCategory.SIMULATED`.
- If either condition is violated, the injection is REJECTED to prevent provenance corruption.
