# Module 01 — Subsystem Scope & Non-Scope Boundaries

## Strict Scope Boundaries

### Module 01 Responsibilities
- Connection management & stream ingestion.
- Raw forensic packet immutability & SHA-256 content hashing.
- Deterministic `packet_id` canonicalization.
- CAN / JSON / CSV decoding & SI unit normalization ($\text{rad/s}$, $\text{K}$, $\text{Pa}$, $\text{kg/s}$).
- Physical plausibility range & rate-of-change validation.
- Multi-domain timestamp transformation & clock mapping.
- 5-dimensional provenance & 4-tier quality metadata decoration.
- Multi-rate channel ring buffering & causal grid synchronization.
- RawStore (Arrival) & NormalizedStore (Event) persistence & recovery.

### Non-Scope (Explicitly Excluded from Module 01)
- Engine physics simulation, combustion modeling, or performance maps (Module 02).
- Digital Twin state estimation, observer filters, or twin state storage (Module 03).
- Health Index calculation, degradation modeling, or wear tracking (Module 04).
- AI/ML anomaly detection or predictive models (Module 05).
- Fault diagnostics, sensor failure inference, or root-cause analysis (Module 06).
- Remaining Useful Life (RUL) estimation or maintenance decision support (Module 07).
