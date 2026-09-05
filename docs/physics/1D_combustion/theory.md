# Phase 1D: Fuel Flow & Combustion Theory

## Overview
Phase 1D implements the Rotax 914 fuel flow and combustion physics. It bridges the Engine Airflow (Phase 1C) to the Thermodynamic Exhaust conditions (used by Phase 1B) and the eventual indicated power used for shaft dynamics (Phase 1E). It operates as a 0-D Mean Value Engine Model (MVEM).

## Fuel Flow & Mixture
Since proprietary complete Engine Maps for AFR are unavailable, the model utilizes an **Airflow-Driven Mixture Surrogate**. 
The fuel delivery is directly linked to the air mass flow using the relationship $\dot{m}_{fuel} = \dot{m}_{air} / AFR$.
The AFR is determined by a smooth, bounded equivalence ratio ($\phi$) surrogate. This surrogate mimics typical aerospace carburetor enrichment behaviors: leaning out slightly for cruise efficiency at low-to-mid loads, and enriching significantly at high loads (takeoff power) and high speeds for knock suppression and component cooling.

## Fuel Pressure Constraints
The Rotax 914 fuel system documentation establishes nominal operating fuel pressure boundaries (15 kPa to 35 kPa differential to the airbox). 
This model exposes the differential fuel pressure as a monitored state, allowing downstream fault models (e.g., Phase 5) to inject anomalies (like fuel pump degradation or filter clogging) and evaluate the system's response without requiring a complex, unverified sub-component hydraulic model of the carburetor bowls.

## Energy Accounting
The model performs rigorous chemical energy accounting. The Lower Heating Value (LHV) of generic gasoline (~43.5 MJ/kg) establishes the total available chemical power.
A portion of this power is left unreleased (combustion inefficiency), while the released energy is partitioned strictly into:
1. **Indicated Power**: Mechanical work produced in the cylinder.
2. **Exhaust Sensible Power**: Enthalpy carried away by the exhaust gas.
3. **Heat Loss**: Residual energy transferred to the cylinder walls, oil, and coolant.

This closure prevents non-physical infinite energy loops.

## Wiebe Combustion Surrogate
A 0-D Wiebe burn-fraction formula is included to represent the time-history of the fuel mass fraction burned ($x_b$). While the full model currently operates as a cycle-averaged MVEM, this equation provides a hook for future high-fidelity expansions (e.g., indicating peak heat release rates or combustion phasing faults) without rewriting the core architecture.

## Exhaust State
The exhaust manifold state is derived from conservation of mass (air + fuel) and conservation of energy. The exhaust temperature is explicitly calculated from the exhaust sensible power partition. The exhaust pressure uses a reduced-order parabolic restriction curve ($\Delta P \propto \dot{m}_{exh}^2$) ensuring physical consistency as it back-pressures the turbine in Phase 1B.
