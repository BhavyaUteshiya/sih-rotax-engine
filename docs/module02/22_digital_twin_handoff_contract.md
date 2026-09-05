# Module 02 — Digital Twin Handoff Contract

## 1. Overview & Architectural Role

The Digital Twin Core operates exclusively downstream of Module 01 data acquisition and validation. It accepts validated normalized telemetry data matching the exact schema and contracts produced during live flight operations.

$$\text{MODULE 02 SIMULATOR} \longrightarrow \text{CAN TRANSPORT} \longrightarrow \text{MODULE 01 INGESTION} \longrightarrow \text{VALIDATED NORMALIZED DATASET} \longrightarrow \text{DIGITAL TWIN CORE}$$

The Digital Twin Core does **NOT** need to know CAN encoding, byte structures, or transport mechanics. Its input is the validated, normalized telemetry stream.

---

## 2. Telemetry Schema & Metadata Contract

Every telemetry sample consumed by the Digital Twin Core contains:

| Field Name | Type | Description | Example |
|---|---|---|---|
| `timestamp` | `float` | UTC Epoch seconds (double precision) | `1787733205.120000` |
| `simulation_time` | `float` | Simulation elapsed time (seconds) | `5.120000` |
| `run_id` | `string` | Unique simulation run ID | `sim_run_001` |
| `engine_id` | `string` | Engine identifier (`engine_1` or `engine_2`) | `engine_1` |
| `parameter_id` | `string` | Standardized parameter identifier | `engine.rpm` |
| `display_value` | `float` | Engineering value | `2429.0` |
| `display_unit` | `string` | Engineering unit string | `RPM` |
| `canonical_value` | `float` | SI canonical float value | `254.36` |
| `canonical_unit` | `string` | SI canonical unit | `RAD_PER_SEC` |
| `validity` | `string` | Physical validity classification | `VALID` |
| `state_category` | `string` | Provenance classification | `SIMULATED` |
| `physical_origin` | `string` | Data origin tag | `SIMULATOR` |
| `scenario_id` | `string` | Mission/Flight scenario ID | `climb_phase` |
| `sequence_number` | `int` | Monotonically increasing sequence number | `256` |
| `schema_version` | `string` | Contract schema version | `1.0.0` |

---

## 3. Provenance Safeguards

- Data originating from Module 02 simulation is strictly tagged with `physical_origin = SIMULATOR`, `state_category = SIMULATED`, and `processing_context = SYNTHETIC_GENERATION`.
- These metadata tags persist through transport, decoding, SI normalization, storage, and dataset export, ensuring simulation outputs cannot be mistaken for real UAV flight measurements.
