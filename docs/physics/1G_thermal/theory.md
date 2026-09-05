# Phase 1G: Engine Thermal Physics - Theory

## 1. Subsystem Purpose
The Rotax 914 engine thermal physics model (Phase 1G) establishes a reduced-order digital twin for the engine's internal temperatures. Its core purpose is to provide dynamic tracking of the Cylinder Head Temperature (CHT) and Engine Oil Temperature without resorting to full 3D CFD, finite element analysis, or complex empirical maps.

This supports health monitoring by creating a realistic expectation of thermal behavior under varying loads, ambient conditions, and airspeeds. Future algorithms will compare these digital twin expectations to actual telemetry to detect anomalies (e.g., degraded cooling, fouled fins, low oil).

## 2. Theoretical Architecture

The model uses a **Lumped-Capacitance Two-Node Thermal Network**:

1. **Node 1: Cylinder Head (CHT)**
   Represents the thermal mass of the engine block and heads. It receives a fraction of the unused combustion heat loss, transfers heat to the oil, and rejects heat directly to the environment.

2. **Node 2: Engine Oil**
   Represents the thermal mass of the engine oil. It absorbs heat from the CHT node and rejects heat to the environment via the oil cooler.

### Energy Ownership
- Combustion chemical energy release is calculated strictly in Phase 1D.
- Phase 1G consumes only the **heat-loss residual** ($P_{\text{heat\_loss}}$) produced by 1D.
- There is no double-counting of fuel energy, indicated work, or exhaust enthalpy.

## 3. Dynamic Heat Transfer Mechanics

### Thermal Capacity
The temperature rate of change for each node is governed by its total thermal capacity ($C_{th} = m \cdot c_p$):
$$ \frac{dT}{dt} = \frac{\sum Q}{C_{th}} $$

### Internal Heat Transfer
Heat flows between the CHT block and the oil based on a simple linear thermal resistance:
$$ Q_{\text{CHT}\to\text{Oil}} = \frac{T_{\text{CHT}} - T_{\text{Oil}}}{R_{\text{CHT-Oil}}} $$
This formulation naturally reverses direction if the oil becomes hotter than the CHT.

### Environmental Heat Rejection
Cooling is modeled via a convective surrogate that scales with ambient density and aircraft airspeed.
- Higher density $\to$ greater mass flow of cooling air $\to$ higher cooling conductance.
- Higher airspeed $\to$ greater ram air pressure $\to$ higher cooling conductance.
- At zero airspeed, a minimal baseline conductance represents natural convection and radiation.

### Integration
The states are advanced dynamically using an explicit Euler numerical integration scheme over the simulation timestep ($dt$).
