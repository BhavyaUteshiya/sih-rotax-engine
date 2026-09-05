# Formula and model provenance

| Model | Formula / meaning | Variables and SI units | Code location | Source/classification | Status |
|---|---|---|---|---|---|
| Atmosphere | ISA pressure and temperature; moist density `rho = p_d/(R_d T) + p_v/(R_v T)` | `p` Pa, `T` K, `rho` kg/m³, altitude m | `physics/atmosphere.py` | ICAO standard atmosphere; Magnus correlation | Unit tested; prototype envelope limited to troposphere |
| Airflow | speed-density charge and volumetric-efficiency surrogate | mass flow kg/s, pressure Pa, temperature K, speed rpm | `physics/airflow.py` | engineering reduced-order model / calibration | Unit tested |
| Turbo | turbine/compressor work, manifold state, PI wastegate | power W, speed rad/s, pressure Pa, flow kg/s | `physics/turbo_intake.py` | engineering equations plus calibration | Unit tested; no certified map |
| Combustion | `P_fuel = m_dot_fuel × LHV`, released-energy partition, Wiebe burn fraction | W, kg/s, J/kg, crank angle deg | `physics/combustion.py` | established equations plus calibration | Unit tested; not whole-system conservation |
| Dynamics | `alpha = T_net/J_eq`; `J_eq = J_engine + J_prop × r²` | rad/s², N·m, kg·m², `r = omega_prop/omega_engine` | `physics/engine_dynamics.py` | mechanics; inertia/friction calibrated | Unit/validation tested |
| Propeller | advance-ratio thrust and torque coefficients | thrust N, torque N·m, density kg/m³, speed m/s | `physics/propeller.py` | propeller theory / calibration | Unit tested |
| Thermal | lumped heat-capacity and convective heat-transfer balances | temperature K, power W, heat capacity J/K | `physics/thermal.py` | heat-transfer equations / calibration | Unit tested |

“Unit tested” means implementation behaviour has automated coverage; it does not claim physical validation against a particular Rotax engine dataset.
