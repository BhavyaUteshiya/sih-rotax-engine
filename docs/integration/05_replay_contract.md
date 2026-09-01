# Replay Specification & Contract

Exported datasets (CSV and JSONL) can be replayed to reproduce historical telemetry ordering without re-executing physics calculations:

- Replay script reads exported `telemetry_dataset.jsonl` or `telemetry_dataset.csv`.
- Sorts records strictly by `sequence_number` and `timestamp`.
- Streams ordered dataset records downstream to Digital Twin Core.
