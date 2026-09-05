# Module 02 — Aero Piston Engine Simulator & Continuous Telemetry Generator

## Overview
Module 02 is the primary data generation engine for the SIH26054 Digital Twin platform. It simulates the two-way causal physical graph of a 4-stroke aero piston propulsion system operating on a MALE UAV platform.

---

## Phase 1 Implementation Status
- **Status**: Phase 1 Foundation & Configuration Layer COMPLETE.
- **Components**: Configuration Loader, Unit Converter System (Canonical SI), Enumerations & State Dataclasses, Deterministic Simulation Clock ($dt=0.01\text{ s}$), Master Deterministic RNG, Parameter Registry (45 parameters with causal metadata), Versioning (`v1.3.0`), Unit & Integrity Test Suite.
- **Module 01 Freeze Guarantee**: Module 01 (`src/module01/`) remains 100% frozen and untouched.
