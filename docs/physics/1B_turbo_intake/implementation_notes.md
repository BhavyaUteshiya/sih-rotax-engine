# Phase 1B: Turbo / Intake Implementation Notes

## Limitations & Assumptions
The following are explicitly documented limitations of the current Phase 1B implementation:

1. **No Proprietary Compressor Map**: We do not possess the proprietary Rotax compressor and turbine maps.
2. **Reduced-Order Surrogate**: The compressor is mathematically modeled as a calibratable reduced-order surrogate, rather than a lookup table.
3. **No Explicit Surge/Stall Model**: There is no explicit dynamic compressor surge/stall oscillatory model. The surrogate acts as a simple flow-limit boundary.
4. **Static Efficiencies**: Compressor and turbine efficiencies ($\eta_c$, $\eta_t$) are currently simplified and static, not dynamic functions of flow or speed.
5. **No Heat Transfer Lag**: Manifold temperature currently follows the compressor outlet temperature directly without detailed wall or intercooler heat-transfer lag.
6. **Engine Mass Flow Interface**: Engine mass-flow demand ($\dot{m}_{engine}$) remains an interface input to be supplied later by Phase 1C: Airflow.
7. **TCU Surrogate**: The TCU is a PI control surrogate, not the proprietary Rotax logic algorithm.
8. **Unverified Absolute RPM**: Exact real-world Rotax turbo RPM is not being claimed or validated; $\omega$ is a physically consistent internal state variable.
9. **High-Altitude Outputs**: High-altitude numerical values (like required turbo RPM) derived from this surrogate are internal model outputs, not direct measured Rotax empirical values.

## Formula Documentation
All runtime equations (TRB-01 through TRB-06) are documented in `formulas.md` with their variables, units, sources, and classifications. They are physically located in `src/digital_twin/physics/turbo_intake.py` under `TurboIntakeModel.step()`, and validated extensively in `scratch/test_turbo_intake.py` ensuring thermodynamic temperature/work relationships, numerical stability, and logical physical boundaries.
