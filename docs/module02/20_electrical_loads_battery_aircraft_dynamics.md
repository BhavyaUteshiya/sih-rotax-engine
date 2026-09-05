# Module 02 Phase 3.7: Electrical Subsystem, Battery SOC, Starter Motor & 3-DOF Aircraft Dynamics

## Executive Summary

Phase 3.7 completes the physical integration of the electrical power generation architecture, battery state-of-charge (SOC) dynamics, starter motor cranking, and 3-DOF longitudinal aircraft flight dynamics into the **SIH26054 Aero Piston Engine Simulator**.

This physical coupling closes the full causal loop:
$$\text{ENGINE RPM} \longrightarrow \text{ALTERNATOR} \longrightarrow \text{ELECTRICAL BUS} \longrightarrow \text{BATTERY CHARGE/DISCHARGE} \longrightarrow \text{STARTER} \longrightarrow \text{PROPELLER THRUST} \longrightarrow \text{3-DOF AIRCRAFT FLIGHT DYNAMICS} \longrightarrow \text{ATMOSPHERE COUPLING} \longrightarrow \text{INTAKE AIRFLOW}$$

---

## 1. Physical Architecture & System Equations

### 1.1 Electrical Power Balance & Bus Voltage
The aircraft electrical bus operates at a nominal voltage $V_{\text{bus}}$ (28.0 V DC for TAPAS-BH-201).
Total electrical power demand $P_{\text{demand}}$ consists of baseline avionics/payload demand $P_{\text{avionics}}$ and starter motor power draw $P_{\text{starter}}$:
$$P_{\text{demand}} = P_{\text{avionics}} + \sum_{i=1}^{N_{\text{eng}}} P_{\text{starter}, i}$$

The net electrical demand $P_{\text{net}}$ evaluated against total alternator output $P_{\text{alt,total}} = \sum_{i=1}^{N_{\text{eng}}} P_{\text{alt,elec}, i}$ determines battery charge or discharge state:
$$P_{\text{net}} = P_{\text{demand}} - P_{\text{alt,total}}$$

### 1.2 Alternator Electromechanical Coupling
For each engine operating above alternator cut-in speed ($N_{\text{eng}} \ge N_{\text{cutin}}$), current generation $I_{\text{alt}}$ is bounded by maximum rated current $I_{\text{alt,max}}$:
$$I_{\text{alt}} = \min\left(I_{\text{alt,max}}, \frac{P_{\text{demand}}}{V_{\text{bus}}}\right)$$
$$P_{\text{alt,elec}} = V_{\text{bus}} \cdot I_{\text{alt}} \quad [\text{W}]$$
$$P_{\text{alt,mech}} = \frac{P_{\text{alt,elec}}}{\eta_{\text{alt}}} \quad [\text{W}]$$

The mechanical load torque $T_{\text{alt}}$ reflected to the engine crankshaft is:
$$T_{\text{alt}} = \frac{P_{\text{alt,mech}}}{\max(\omega_{\text{min}}, \omega_{\text{eng}})} \quad [\text{N}\cdot\text{m}]$$

This shaft torque enters the crankshaft rotational equation:
$$J_{\text{eng}} \frac{d\omega_{\text{eng}}}{dt} = (T_{\text{ind}} + T_{\text{starter}}) - (T_{\text{prop\_load}} + T_{\text{alt}}) - T_{\text{fric}}$$

### 1.3 Battery State-of-Charge (SOC) Differential Model
> [!IMPORTANT]
> **Single Sign Convention**:
> - **Positive Battery Current ($I_{\text{batt}} > 0$)**: DISCHARGE (Supplying electrical deficit).
> - **Negative Battery Current ($I_{\text{batt}} < 0$)**: CHARGE (Absorbing electrical surplus).

- **Discharging ($P_{\text{net}} > 0$)**:
  $$P_{\text{batt\_dis}} = \frac{P_{\text{net}}}{\eta_{\text{discharge}}} \implies I_{\text{batt}} = \frac{P_{\text{batt\_dis}}}{V_{\text{bus}}}$$
  $$\frac{d\text{SOC}}{dt} = -\frac{P_{\text{batt\_dis}}}{E_{\text{nominal}}}$$

- **Charging ($P_{\text{net}} < 0$ and $\text{SOC} < 1.0$)**:
  $$P_{\text{batt\_chg}} = -P_{\text{net}} \cdot \eta_{\text{charge}} \implies I_{\text{batt}} = -\frac{P_{\text{batt\_chg}}}{V_{\text{bus}}}$$
  $$\frac{d\text{SOC}}{dt} = +\frac{P_{\text{batt\_chg}}}{E_{\text{nominal}}}$$

Terminal battery voltage $V_{\text{batt\_terminal}}$ responds dynamically to state of charge:
$$V_{\text{batt\_terminal}} = V_{\text{nominal}} \cdot (0.85 + 0.15 \cdot \text{SOC})$$

### 1.4 Starter Motor Dynamics & Starting Sequence
Starter engagement requires $\text{SOC} \ge \text{SOC}_{\text{min\_starting}}$ (0.20) and engine speed $N_{\text{eng}} < N_{\text{idle}}$ (1400 RPM).
$$P_{\text{starter\_mech}} = P_{\text{starter\_rating}} \cdot \eta_{\text{starter}} \quad [\text{W}]$$
$$T_{\text{starter}} = \frac{P_{\text{starter\_mech}}}{\max(\omega_{\text{crank\_min}}, \omega_{\text{eng}})} \quad [\text{N}\cdot\text{m}]$$

The starting state transition follows the causal chain:
$$\text{OFF} \xrightarrow[\text{command}]{\text{starter}} \text{CRANKING} \xrightarrow[T_{\text{starter}}]{\text{spin up}} \text{LIGHT-OFF} \xrightarrow[N_{\text{eng}} \ge N_{\text{idle}}]{\text{disengage}} \text{IDLE} \xrightarrow[\text{demand}]{\text{throttle}} \text{RUNNING}$$

### 1.5 3-DOF Longitudinal Aircraft Dynamics & Drag Polar
The aircraft longitudinal force balance governs horizontal position $x$, geometric altitude $h$, forward true airspeed $V$, and flight path angle $\gamma$:

- **Total Propulsive Thrust**:
  $$F_{\text{thrust,total}} = F_{\text{thrust,eng1}} + F_{\text{thrust,eng2}} \quad [\text{N}]$$

- **Drag Polar**:
  $$C_D = C_{D0} + k \cdot C_L^2$$
  $$F_{\text{drag}} = 0.5 \cdot \rho_{\text{air}} \cdot V^2 \cdot S \cdot C_D \quad [\text{N}]$$

- **Gravitational Weight**:
  $$W = m_{\text{ac}} \cdot g \quad [\text{N}]$$

- **Longitudinal Acceleration**:
  $$\frac{dV}{dt} = \frac{F_{\text{thrust,total}} - F_{\text{drag}} - W \cdot \sin\gamma}{m_{\text{ac}}} \quad [\text{m/s}^2]$$

- **Kinematic State Integrations**:
  $$\frac{dh}{dt} = V \cdot \sin\gamma \implies h(t + dt) = \max(0.0, h + V \sin\gamma \cdot dt)$$
  $$\frac{dx}{dt} = V \cdot \cos\gamma \implies x(t + dt) = x + V \cos\gamma \cdot dt$$

---

## 2. Configuration & Parameter Registry Integration

Every electrical, battery, starter, aircraft, and aerodynamic parameter is loaded strictly via `ConfigLoader` from YAML files with full provenance metadata (`OFFICIAL`, `REPORTED`, `ESTIMATED`, `DERIVED`).

### Phase 3.7 Parameter Registry Matrix (20 Parameters)

| Parameter ID | Category | Canonical SI Unit | Provenance | Telemetry Field |
| :--- | :--- | :--- | :--- | :--- |
| `bus_voltage` | ELECTRICAL | `VOLT` | REPORTED | `bus_voltage_v` |
| `bus_current` | ELECTRICAL | `AMPERE` | DERIVED | `bus_current_a` |
| `alternator_rpm` | ELECTRICAL | `RAD_PER_SEC` | DERIVED | `alternator_rpm` |
| `alternator_power` | ELECTRICAL | `WATT` | DERIVED | `alternator_power_w` |
| `alternator_torque` | ELECTRICAL | `NEWTON_METER` | DERIVED | `alternator_torque_n_m` |
| `battery_soc` | ELECTRICAL | `PERCENT` | ESTIMATED | `battery_soc_percent` |
| `battery_voltage` | ELECTRICAL | `VOLT` | REPORTED | `battery_voltage_v` |
| `battery_current` | ELECTRICAL | `AMPERE` | DERIVED | `battery_current_a` |
| `battery_power` | ELECTRICAL | `WATT` | DERIVED | `battery_power_w` |
| `starter_torque` | ELECTRICAL | `NEWTON_METER` | DERIVED | `starter_torque_n_m` |
| `starter_power` | ELECTRICAL | `WATT` | REPORTED | `starter_power_w` |
| `electrical_load_power` | ELECTRICAL | `WATT` | ESTIMATED | `electrical_load_w` |
| `aircraft_velocity` | FLIGHT | `M_PER_SEC` | IMPLEMENTED | `aircraft_velocity_m_s` |
| `aircraft_altitude` | FLIGHT | `METER` | IMPLEMENTED | `aircraft_altitude_m` |
| `aircraft_x_position` | FLIGHT | `METER` | IMPLEMENTED | `aircraft_x_m` |
| `flight_path_angle` | FLIGHT | `RADIAN` | IMPLEMENTED | `flight_path_angle_rad` |
| `drag_force` | FLIGHT | `NEWTON` | DERIVED | `drag_force_n` |
| `weight_force` | FLIGHT | `NEWTON` | DERIVED | `weight_force_n` |
| `total_thrust` | FLIGHT | `NEWTON` | DERIVED | `total_thrust_n` |
| `longitudinal_acceleration` | FLIGHT | `M_PER_SEC2` | DERIVED | `longitudinal_acceleration_m_s2` |

---

## 3. Verification & Test Suite Coverage

The Phase 3.7 test suite (`tests/module02/test_phase3_7_electrical_aircraft.py`) validates 34 targeted test scenarios:
- **Electrical & Alternator (Tests 1–10)**: Alternator output scaling, max current bounding, shaft torque reflection, power conservation, battery charge/discharge balance, SOC bounds $[0.0, 1.0]$.
- **Starter Motor (Tests 11–16)**: Battery power draw, starter cranking torque reflection, dynamic RPM rise, causal starting state transitions, SOC minimum threshold checks.
- **3-DOF Aircraft Dynamics (Tests 17–26)**: Twin-engine thrust summation, quadratic velocity drag scaling, density altitude drag response, force balance acceleration, vertical/horizontal kinematic state integration, atmosphere coupling.
- **Configuration & Integrity (Tests 27–34)**: YAML flow verification, provenance taxonomy checks, parameter registry zero-orphan audit, Module 01 immutability check.

All **225 test cases** across Module 01 and Module 02 pass with 100% success rate.
