# Module 01 — Data Acquisition & Ingestion: System Overview

## SIH26054 — AI-Enabled Real-Time Digital Twin System for Aero Piston Engines in MALE UAVs

### Purpose & Scope
Module 01 is the foundational subsystem of the SIH26054 Digital Twin platform. It is responsible for capturing raw telemetry streams from physical or simulated engine interfaces (SocketCAN, ECU/FADEC adapters, file logs), preserving raw forensic payload immutability with SHA-256 content verification, decoding protocol payloads, normalizing physical parameters to explicit SI canonical units, performing data validity and plausibility checks, tracking multi-domain timestamps and mission context, decorating telemetry with 5-dimensional provenance and 4-tier quality metadata, buffering multi-rate telemetry streams, and publishing versioned `TelemetryFrame v1.0.0` snapshots for downstream consumption by Module 02 (Simulation & Replay) and Module 03 (Digital Twin Core).

### Key Architectural Characteristics
- **Deep Immutability & Forensic Audit**: Raw bytes are captured in `DeepImmutableRawPacket` instances with SHA-256 payload content hashes (`payload_sha256`) and deterministic event packet identities (`packet_id`).
- **SI Unit Standardization**: All rotational speeds are converted to $\text{rad/s}$ ($\omega = \text{RPM} \cdot \frac{\pi}{30}$), temperatures to Kelvin ($K = ^\circ\text{C} + 273.15$), pressures to Pascal ($\text{Pa} = \text{bar} \cdot 100,000$), and fuel flows to kg/s.
- **Independent Physical vs. Temporal Usability**: Physical validity (`is_physically_valid`) is decoupled from timestamp resolution (`is_temporally_valid`), ensuring sound physical data is never discarded merely because UTC mapping is unavailable.
- **Causal Synchronization**: Real-time synchronization (`REALTIME_CAUSAL_MODE`) strictly forbids look-ahead linear interpolation to eliminate future-data leakage.
- **Non-Scope Integrity**: Module 01 strictly excludes engine physics simulation, fault diagnosis, health index calculation, anomaly detection, RUL estimation, or Digital Twin state estimation.
