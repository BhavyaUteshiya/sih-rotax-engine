# Replay Specification & Contract

Exported datasets (CSV and JSONL) can be replayed to reproduce historical telemetry ordering without re-executing physics calculations:

- Replay script reads exported `telemetry_dataset.jsonl` or `telemetry_dataset.csv`.
- Global in-memory sorting of multi-GB datasets is strictly prohibited to prevent OOM.
- Streams parsed records sequentially directly into the Phase 3 `TelemetryNormalizer`.
- The `TelemetryNormalizer` intrinsically enforces sequence ordering and safe frame assembly before records flow downstream to the Digital Twin Core.
