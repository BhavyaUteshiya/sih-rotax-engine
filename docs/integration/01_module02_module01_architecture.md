# Integration Architecture: Module 02 Simulator → Transport → Module 01 Ingestion

## Architecture Overview

The integration layer bridges the **Module 02 TAPAS-BH-201 Aero Piston Engine Simulator** to **Module 01 Data Acquisition & Ingestion Subsystem**.

```
┌───────────────────────────────┐
│ MODULE 02                     │
│ TAPAS-BH-201 ENGINE SIMULATOR │
└───────────────┬───────────────┘
                │ 100 Hz Physics
                ▼
        TELEMETRY GENERATOR
                │ 50 Hz CAN Frames
                ▼
         CAN / SOCKETCAN
                │ InMemoryTransport / SocketCANTransport
                ▼
┌───────────────────────────────┐
│ MODULE 01                     │
│ DATA ACQUISITION & INGESTION  │
│                               │
│ Raw Storage -> Decode ->      │
│ SI Normalization -> Validate  │
│ -> Normalized Persistence     │
└───────────────┬───────────────┘
                │
                ▼
       VALIDATED TELEMETRY
                │
                ▼
       CSV / JSONL DATASET
                │
                ▼
┌───────────────────────────────┐
│ FUTURE DIGITAL TWIN CORE      │
└───────────────────────────────┘
```

## Module 01 Immutability
Module 01 is 100% frozen. No files in `src/module01/` are modified. All adapters, bridges, encoders, and transports reside in `src/module02/integration/`.
