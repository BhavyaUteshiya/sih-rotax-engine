# Phase 1: Digital Twin Engine Core Architecture

## Overview
Phase 1 implements a physical Digital Twin of the Rotax 914 UL-F aero piston engine. The simulation consists of 7 isolated physical modules (1A-1G), executed in a deterministic causal chain.

## Modules & Causality Chain

1. **1A: Atmosphere** (`AtmosphereModel`)
   - Determines ambient density and temperature based on altitude (ISA standard).
   - Driven by: Altitude.

2. **1B: Turbo Intake** (`TurboIntakeModel`)
   - Compresses ambient air using exhaust enthalpy.
   - Calculates target MAP bounded by atmospheric and throttle states.
   - Driven by: Atmosphere (1A) and Exhaust (from previous 1D step).

3. **1C: Airflow** (`AirflowModel`)
   - Calculates speed-density volumetric efficiency and cylinder mass airflow.
   - Driven by: Engine RPM (1E), Turbo Manifold (1B), Throttle.

4. **1D: Combustion** (`CombustionModel`)
   - Converts fuel and air into thermal energy and exhaust gas. Calculates residual heat loss.
   - Driven by: Airflow (1C), Engine RPM (1E).

5. **1F: Propeller** (`PropellerModel`)
   - Models aerodynamic load torque for a 1.7m canonical propeller based on advance ratio.
   - Driven by: Engine RPM (1E), True Airspeed (TAS), Atmosphere (1A).

6. **1E: Engine Dynamics** (`EngineDynamicsModel`)
   - Solves the coupled rotational inertia system ($J_{eq} = J_{engine} + J_{prop} / r_g^2$).
   - Calculates angular acceleration based on net torque (Combustion Torque - Propeller Load - Friction).
   - Driven by: Combustion (1D), Propeller (1F).

7. **1G: Thermal** (`ThermalModel`)
   - Tracks heat capacitance, convection, and Cylinder Head Temperature (CHT).
   - Driven by: Combustion residual heat (1D), Airflow speed (TAS), Atmosphere (1A).

## Orchestrator (`DigitalTwinSimulator`)
The `DigitalTwinSimulator` acts as the master orchestrator, maintaining a `SimulationState` object and executing each physics module sequentially with a timestep `dt`. It strictly enforces data flow causality without any circular dependencies.

## Key Design Principles
- **Strict Single Ownership:** Each physical quantity (e.g., mass flow, torque) has exactly one authoritative source.
- **Physical Accuracy:** Conservation of mass and energy are maintained across interfaces. No magic constants without physical backing.
- **No Internal Coupling:** Physics modules are purely functional (where applicable) and decoupled. They receive simple input structs and return output structs.
