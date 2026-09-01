# Module 02 — 06. Causal Dependency Contract

## Upstream and Downstream Causal Graph
Every physical parameter registered in `ParameterRegistry` documents its direct `upstream_cause_ids` and `downstream_effect_ids`.

```
Throttle (theta) -> Manifold Pressure (p_m) -> Air Mass Flow (m_air) -> Fuel Mass Flow (m_fuel)
-> Combustion Heat (Q_comb) -> Cylinder Torque (T_ind,i) -> Total Torque (T_ind,total)
-> Rotational Acceleration (d_omega/dt) -> Engine Speed (RPM) -> Propeller Thrust & Load
-> Airspeed (V_inf) & Cooling Airflow (h_cool) -> CHT & Oil Temperature
```
Zero orphan parameters exist in the registry.
