# Module 02 — 01. Architecture & Subsystem Boundaries

## 1. Modular Subsystem Architecture

```
USER / CONTROLS / ENVIRONMENT
             ↓
     ATMOSPHERE MODEL (ISA Moist Air)
             ↓
     AIRCRAFT FLIGHT DYNAMICS (Mass reduction via fuel burn)
             ↓
     PROPELLER MODEL (2-Sided Coupling: Thrust & Load)
        ↙         ↘
     THRUST       LOAD
        ↓            ↓
     AIRCRAFT <---> ENGINE
                     ↓
       DYNAMIC INTAKE MANIFOLD (dp_m/dt)
                     ↓
       CYLINDER HEAT & TORQUE SUMMATION (T_ind,total = Sum T_i)
                     ↓
       ROTATIONAL EQUATION OF MOTION (J d_omega/dt = T_ind - T_load - T_fric - T_pump - T_alt)
                     ↓
       THERMAL (CHT 1-4, EGT 1-4) & LUBRICATION (T_oil, P_oil)
                     ↓
       ELECTRICAL (I_alt, Battery SOC, T_alt Load) & VIBRATION (Time-Domain RMS)
                     ↓
       WEAR DEGRADATION VECTOR (D_bearing, D_injector, D_ring)
                     ↓
       SENSOR OBSERVATION LAYER (x_true -> y_obs)
                     ↓
       CONTINUOUS TELEMETRY GENERATOR & SIMULATION DASHBOARD
```

## 2. Module 01 Freeze Guarantee
Module 01 provides data acquisition, raw packet immutability, SHA-256 integrity verification, canonical SI unit normalization, multi-rate buffering, causal synchronization, storage recovery state machine, and public API contracts (`ISimulationTelemetrySink`). Module 01 is 100% frozen. Module 02 connects to Module 01 via `ISimulationTelemetrySink` using `PhysicalOrigin.SIMULATOR` and `StateCategory.SIMULATED`.
