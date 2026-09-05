# Phase 1 engine physics

## Scope

Phase 1 is a reduced-order, deterministic prototype—not a certified engine performance model. The implementation is `src/digital_twin/physics` and `src/digital_twin/simulation`.

## Models 1A–1G

1. **1A Atmosphere:** ISA troposphere with optional temperature offset and humid-air density.
2. **1B Turbo/intake:** exhaust-driven turbine/compressor surrogate, PI wastegate, and manifold filling state.
3. **1C Airflow:** speed-density, throttle-area, and volumetric-efficiency surrogate.
4. **1D Fuel/combustion:** mixture surrogate and 0-D Wiebe-shaped combustion accounting.
5. **1E Engine dynamics:** indicated, starter, friction, and reflected propeller torques drive the lumped shaft inertia.
6. **1F Propeller:** advance-ratio surrogate produces thrust and aerodynamic torque.
7. **1G Thermal:** lumped CHT/oil capacities with heat transfer and cooling surrogates.

## Integration, assumptions, and provenance

The simulator uses the causal order documented in the architecture. The full-throttle MAP target (default 110000 Pa) and 1.7 m propeller diameter are configurable prototype calibration boundaries, not official Rotax claims. The gearbox convention is `r = omega_prop / omega_engine`; therefore `J_eq = J_engine + J_prop × r²`. The engine and propeller inertia, friction, turbo map, thermal, and combustion partition coefficients are estimates unless separately sourced.

Combustion partitions released fuel energy among indicated work, exhaust sensible energy, and residual heat loss. This is a calibrated accounting model and does **not** demonstrate strict whole-system energy conservation.

## Limitations and validation

The model omits cylinder-resolved phenomena, turbo maps, ECU controls, actual propeller data, heat exchangers, altitude beyond the configured ISA troposphere range, measurement uncertainty, and fault physics. Unit and integration tests demonstrate numerical/causal behaviour only. See [validation](../validation/phase_1_validation.md) and [references](../references/reference_registry.md).
