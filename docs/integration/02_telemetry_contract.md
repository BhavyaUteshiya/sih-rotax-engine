# Telemetry Contract Specification

Every telemetry sample produced by the Phase 2A Telemetry simulator and transported to Phase 1 Simulator includes:

- `simulation_timestamp`: Elapsed time in seconds (`dt_telemetry = 0.02 s`)
- `engine_index`: Engine 1 or Engine 2
- `parameter_id`: Standardized telemetry key
- `value`: Engineering value
- `unit`: Display unit
- `canonical_value`: SI float value
- `canonical_unit`: SI unit string
- `physical_origin`: `SIMULATOR`
- `state_category`: `SIMULATED`
- `processing_context`: `SYNTHETIC_GENERATION`
- `sequence_number`: Monotonically increasing sequence number
