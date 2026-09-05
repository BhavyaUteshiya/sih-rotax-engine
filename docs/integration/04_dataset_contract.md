# Dataset Exporter Contract

The Dataset Exporter converts normalized telemetry into ML-ready CSV and JSONL formats:

- `timestamp`: UTC Epoch timestamp
- `simulation_time`: Simulation time in seconds
- `run_id`: Simulation run identifier
- `engine_id`: `engine_1` or `engine_2`
- `parameter_id`: Parameter identifier
- `display_value`: Display engineering value
- `display_unit`: Display unit
- `canonical_value`: SI float value
- `canonical_unit`: SI unit string
- `validity`: `VALID` or `PHYSICALLY_INVALID`
- `state_category`: `SIMULATED`
- `physical_origin`: `SIMULATOR`
- `scenario_id`: Mission scenario ID
- `sequence_number`: Monotonically increasing integer
- `schema_version`: `1.0.0`
