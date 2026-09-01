# Module 02 — 18. Dynamic CHT Thermal, EGT, Oil Sump & Temperature-Dependent Viscosity Subsystem

## 1. Physical Heat Partitioning & Energy Accounting

The total chemical heat release rate of fuel delivery $\dot{Q}_{\text{fuel}} = \dot{m}_{\text{fuel}} \cdot \text{LHV} \quad [\text{W}]$ is partitioned between useful work and thermal losses:

$$\dot{Q}_{\text{fuel}} \ge P_{\text{indicated}} + \dot{Q}_{\text{exhaust}} + \dot{Q}_{\text{wall}} + \dot{Q}_{\text{loss}}$$

where:
- $P_{\text{indicated}} = \eta_{\text{comb}} \cdot \eta_{\text{ind,peak}} \cdot \dot{Q}_{\text{fuel}}$ ($\text{W}$): Useful indicated combustion power
- $\dot{Q}_{\text{exhaust}} = f_{\text{exh}} \cdot \eta_{\text{comb}} \cdot \dot{Q}_{\text{fuel}}$ ($\text{W}$): Exhaust gas thermal energy rate
- $\dot{Q}_{\text{wall}} = \min(\dot{Q}_{\text{fuel}} - P_{\text{ind}} - \dot{Q}_{\text{exh}}, f_{\text{wall}} \cdot \dot{Q}_{\text{fuel}})$ ($\text{W}$): Cylinder wall heat transfer rate
- $\dot{Q}_{\text{loss}}$ ($\text{W}$): Remaining radiation/unburned hydrocarbon energy losses

---

## 2. Dynamic Lumped Cylinder Head Temperature (CHT) Model

$$m_{\text{cyl}} \cdot C_{p,\text{cyl}} \cdot \frac{dT_{\text{CHT}}}{dt} = \dot{Q}_{\text{wall}} - \dot{Q}_{\text{cooling}}$$

where:
- $m_{\text{cyl}}$ ($\text{kg}$): Cylinder head metal mass (YAML: `18.0 kg` for TAPAS)
- $C_{p,\text{cyl}}$ ($\text{J/(kg K)}$): Cylinder specific heat capacity (YAML: `480.0 J/(kg K)`)
- $\dot{Q}_{\text{cooling}} = h_{\text{cool}} \cdot A_{\text{cyl}} \cdot \max(0.0, T_{\text{CHT}} - T_{\text{ambient}})$ ($\text{W}$)
- Convective cooling heat transfer coefficient $h_{\text{cool}} = h_{\text{base}} \cdot \left[1 + 0.05 \cdot \left(\frac{V_{\text{inf}}}{10}\right) + 0.02 \cdot \left(\frac{N_{\text{engine}}}{1000}\right)\right]$ ($\text{W/(m}^2\text{ K)}$)

---

## 3. Dynamic Exhaust Gas Temperature (EGT) Model

$$T_{\text{EGT}} = T_{\text{intake}} + \frac{\dot{Q}_{\text{exhaust}}}{\dot{m}_{\text{exhaust}} \cdot C_{p,\text{exhaust}}}$$
Thermocouple sensor first-order response lag:
$$\frac{dT_{\text{EGT}}}{dt} = \frac{T_{\text{exhaust}} - T_{\text{EGT}}}{\tau_{\text{EGT}}}$$
where $\tau_{\text{EGT}} = 0.5\text{ s}$ thermocouple time constant.

---

## 4. Dynamic Oil Sump Thermal Model

$$m_{\text{oil}} \cdot C_{p,\text{oil}} \cdot \frac{dT_{\text{oil}}}{dt} = \dot{Q}_{\text{oil\_gen}} - \dot{Q}_{\text{oil\_cool}}$$

where:
- $m_{\text{oil}}$ ($\text{kg}$): Oil sump fluid mass (YAML: `4.5 kg`)
- $C_{p,\text{oil}}$ ($\text{J/(kg K)}$): Oil heat capacity (YAML: `2100.0 J/(kg K)`)
- $\dot{Q}_{\text{oil\_gen}} = (0.75 \cdot P_{\text{friction}}) + 0.02 \cdot \max(0.0, T_{\text{CHT}} - T_{\text{oil}})$ ($\text{W}$)
- $\dot{Q}_{\text{oil\_cool}} = h_{\text{oil\_cooler}} \cdot \max(0.0, T_{\text{oil}} - T_{\text{ambient}})$ ($\text{W}$)

---

## 5. Vogel Temperature-Dependent Dynamic Oil Viscosity Model

$$\mu(T_{\text{oil}}) = \mu_{\text{ref}} \cdot \exp\left( B_{\text{visc}} \cdot \left[ \frac{1}{T_{\text{oil}}} - \frac{1}{T_{\text{ref}}} \right] \right) \quad [\text{Pa}\cdot\text{s}]$$

where:
- $T_{\text{ref}} = 373.15\text{ K}$ ($100^\circ\text{C}$): SAE J300 reference temperature
- $\mu_{\text{ref}} = 0.012\text{ Pa}\cdot\text{s}$ ($12\text{ cSt}$): SAE 15W-40 oil viscosity at $100^\circ\text{C}$
- $B_{\text{visc}} = 3800.0\text{ K}$: Viscosity-temperature activation constant (`ESTIMATED`, `calibration_required: true`)

---

## 6. Viscosity-Modified Mechanical Friction Coupling

$$T_{\text{friction}} = T_{\text{static}} \cdot \tanh(10 \cdot \omega) + c_{\text{viscous}} \cdot \left(\frac{\mu(T_{\text{oil}})}{\mu_{\text{ref}}}\right) \cdot \omega + c_{\text{hydro}} \cdot \omega^2 \quad [\text{N}\cdot\text{m}]$$

- Cold oil ($\mu > \mu_{\text{ref}}$) increases viscous friction torque, resisting crankshaft acceleration.
- Warm oil ($\mu \approx \mu_{\text{ref}}$) reduces viscous friction torque, allowing higher net shaft torque.

---

## 7. Causal Dependency Loop & Environmental Coupling

```
USER CONTROLS (Throttle, Altitude, Ambient Temp/Pressure, Start/Stop)
       │
       ▼
[ENGINE OPERATING STATE MACHINE (OFF, STARTING, IDLE, RUNNING)]
       │
       ▼
[INTAKE AIRFLOW (m_dot_air) & CLOSED-LOOP MAP (p_map)]
       │
       ▼
[FUEL DELIVERY (m_dot_fuel) & FADEC SMOKE LIMITER]
       │
       ▼
[AIR-FUEL RATIO (AFR) & COMBUSTION EFFICIENCY (eta_comb)]
       │
       ▼
[HEAT PARTITION: P_ind, Q_exh, Q_wall, Q_oil]
       │                 │            │
       ▼                 ▼            ▼
[EXHAUST TURBINE]   [DYNAMIC EGT]  [CHT DYNAMICS (m_cyl * Cp * dT_cht/dt = Q_wall - Q_cool)]
  & TURBO MAP                         │
                                      ▼
                           [OIL TEMP DYNAMICS (m_oil * Cp * dT_oil/dt = Q_oil_gen - Q_oil_cool)]
                                      │
                                      ▼
                           [DYNAMIC OIL VISCOSITY mu(T_oil)]
                                      │
                                      ▼
                           [VISCOSITY-DEPENDENT FRICTION T_friction(mu)]
                                      │
                                      ▼
                           [CRANKSHAFT DYNAMICS J * d(omega)/dt = T_ind - T_load - T_friction]
                                      │
                                      ▼
                           [ENGINE RPM (omega)]
```

---

## 8. Twin-Engine Independence & Assumptions

- Engine 1 and Engine 2 maintain completely independent thermal masses ($m_{\text{cyl,1}}, m_{\text{cyl,2}}$), CHTs ($T_{\text{CHT,1}}, T_{\text{CHT,2}}$), EGTs ($T_{\text{EGT,1}}, T_{\text{EGT,2}}$), oil temperatures ($T_{\text{oil,1}}, T_{\text{oil,2}}$), and oil viscosities ($\mu_1, \mu_2$).
- Modifying Engine 1 operating conditions never alters Engine 2.
