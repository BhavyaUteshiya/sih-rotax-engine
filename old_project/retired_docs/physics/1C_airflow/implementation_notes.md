# Phase 1C: Implementation Notes and Limitations

## Limitations

1. **No Proprietary Rotax Maps**: A full proprietary map for volumetric efficiency ($\eta_v$) and carburetor geometry for the Rotax 914 is unavailable. Thus, a parabolic surrogate for $\eta_v$ and a quadratic surrogate for effective throttle area are used.
2. **Mean-Value Engine Modeling (MVEM)**: There is no 1D gas dynamics or CFD. Instantaneous crank-angle resolved pressures (wave action, individual valve openings) are not simulated.
3. **No Combustion/Fuel Flow**: This phase calculates airflow only. Fuel-air ratio, thermal output, and torque will be introduced in subsequent phases (1D and 1E).
4. **Input RPM**: RPM is currently an input variable. The actual closed-loop RPM dynamics based on load and torque generation are deferred to Phase 1E.
5. **No Diaphragm Dynamics**: Detailed dynamic response of the carburetor diaphragm or needle valves is ignored in favor of a macroscopic restriction model.
6. **No Thermal Transfer Model**: The intake manifold is treated as adiabatic during the throttle expansion. Thermal physics (CHT, EGT) are deferred to later stages.

## Numerical Considerations
- The model employs a Bisection method to find the equilibrium charge pressure (where throttle flow equals cylinder demand). This is a quasi-steady numerical solver; it does *not* simulate temporal dynamic delay or lag. The major temporal dynamics are owned by Phase 1B (the intake manifold plenum). This approach is more stable than introducing a new stiff ODE state for a small port volume downstream of the throttle.
- The iteration is capped at 50 loops with a 0.5 Pa tolerance to guarantee bounded execution time suitable for real-time Digital Twin constraints.
