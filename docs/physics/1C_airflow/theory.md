# Phase 1C: Airflow / Engine Breathing Model Theory

## Overview
Phase 1C represents the physical process by which the engine draws air from the intake manifold (airbox), past the throttle restriction (carburetor), and into the cylinders. It acts as the critical bridge connecting the turbocharger state (Phase 1B) to the combustion and torque generation layers (Phases 1D and 1E).

The core of Phase 1C relies on Mean Value Engine Modeling (MVEM). Instead of simulating high-frequency, crank-angle-resolved pressure waves (1-D gas dynamics), the model evaluates the flow in a time-averaged sense over complete engine cycles.

## 1. Engine Geometry
The Rotax 914 is a 4-cylinder, 4-stroke engine. The total swept volume (displacement) is a fundamental geometric property that governs its air-pumping capacity.
Using official EASA TCDS data:
- Bore = 79.5 mm
- Stroke = 61.0 mm

## 2. Speed-Density Cylinder Filling
The flow of air into the cylinders is calculated using the standard speed-density relationship. The mass flow depends on the density of the air in the intake port, the engine displacement, the engine speed, and the volumetric efficiency ($\eta_v$).
Because the engine is a 4-stroke, intake events happen every two revolutions. Thus, the intake frequency is $N / 2$, where $N$ is engine speed in revolutions per second.

## 3. Volumetric Efficiency Surrogate ($\eta_v$)
Volumetric efficiency describes how effectively the engine fills its cylinders compared to the theoretical maximum (swept volume $\times$ charge density). It is not a static constant. In reality, it varies with RPM due to tuning effects (intake runner resonance) and with charge pressure.
Because a complete empirical $\eta_v$ map for the Rotax 914 is proprietary, Phase 1C uses a smooth, bounded parabolic surrogate. It peaks near the optimal operating speed (5800 RPM) and scales gently with charge pressure to reflect improved filling at higher manifold pressures.

## 4. Throttle and Carburetor Restriction
The Rotax 914 uses carburetion. To prevent non-physical instantaneous pressure jumps and to model the throttling losses, Phase 1C treats the carburetor as a compressible flow restriction.
The flow capacity depends on the upstream pressure (from the turbocharger airbox), the effective throttle area, and the downstream pressure (charge pressure in the cylinder port).
An equilibrium state is calculated numerically (using a Bisection method) to find the exact downstream charge pressure where the mass flow crossing the throttle exactly equals the mass flow demanded by the cylinders. 

**Note on Temporal Dynamics:** The bisection method is strictly a *quasi-steady numerical solver* for this equilibrium state. It does NOT itself represent physical time delay or manifold filling dynamics. The major temporal dynamics (lag and spool-up) are already provided by the Phase 1B intake plenum and turbo shaft inertia. Airflow calculates the steady-state flow constraint for the current instant.
