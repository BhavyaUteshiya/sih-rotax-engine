# Module 01 — Temporal Synchronization Service

## Synchronization Grid Alignment
`TimestampSynchronizer` generates synchronized `TelemetryFrame v1.0.0` snapshots at target grid timestamp $T_{\text{grid}}$.

## Synchronization Modes

### 1. `REALTIME_CAUSAL_MODE` (Default)
- Strictly forbids future look-ahead samples ($t_{\text{sample}} > T_{\text{grid}}$).
- Consumes ONLY samples where `is_sync_eligible == True`.
- Allowed alignment methods: `EXACT`, `HOLD_LAST`, `MISSING`.
- **`LINEAR_INTERPOLATE` is strictly FORBIDDEN** in causal mode to prevent future-data leakage.

### 2. `OFFLINE_REPLAY_MODE`
- Retrospective alignment permitted.
- Allows `LINEAR_INTERPOLATE` between enclosing samples $t_i \le T_{\text{grid}}$ and $t_{i+1} > T_{\text{grid}}$.
