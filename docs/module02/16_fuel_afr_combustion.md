# Module 02 — 16. Fuel Delivery, Air-Fuel Ratio, Combustion & Exhaust Energy Model (Phase 3.3.1 Hardened Physics)

## 1. Physical Equations & Subsystem Architecture

### Fuel Mass Flow & FADEC Air-Availability Smoke Limiter
$$\dot{m}_{\text{fuel,demand,kg/h}} = \dot{m}_{\text{fuel,idle}} + \left(\frac{\theta}{100.0}\right) \cdot (\dot{m}_{\text{fuel,max}} - \dot{m}_{\text{fuel,idle}})$$
$$\dot{m}_{\text{fuel,max\_air,kg/s}} = \frac{\dot{m}_{\text{air}} \cdot \phi_{\text{max}}}{\text{AFR}_{\text{stoich}}}$$
$$\dot{m}_{\text{fuel,actual}} = \min\left(\dot{m}_{\text{fuel,demand}}, \dot{m}_{\text{fuel,max\_air}}\right)$$
$$\dot{Q}_{\text{fuel}} = \dot{m}_{\text{fuel,actual,kg/s}} \cdot \text{LHV} \quad [\text{W}]$$
where $\text{LHV} = 43.0 \times 10^6\text{ J/kg}$ (Diesel Jet-A) and $\phi_{\text{max}} = 1.05$ (smoke limit equivalence ratio ceiling).

---

### Air-Fuel Ratio (AFR) & Equivalence Ratio ($\phi$)
$$\text{AFR} = \begin{cases} \text{None}, & \dot{m}_{\text{fuel}} \le 10^{-7}\text{ kg/s (Engine OFF / Zero Fuel)} \\ \frac{\dot{m}_{\text{air}}}{\dot{m}_{\text{fuel}}}, & \dot{m}_{\text{fuel}} > 10^{-7}\text{ kg/s} \end{cases}$$
$$\phi = \frac{\text{AFR}_{\text{stoich}}}{\text{AFR}} = \frac{\dot{m}_{\text{fuel}} \cdot \text{AFR}_{\text{stoich}}}{\dot{m}_{\text{air}}}$$
where $\text{AFR}_{\text{stoich}} = 14.5$ for diesel fuel. Zero fuel returns $\text{AFR} = \text{None}$ and $\phi = 0.0$ (eliminates fake arbitrary values).

---

### 4-Stroke Cycle Energy Formulation (Eliminates Low-RPM Torque Singularities)
For a 4-stroke engine, combustion work is generated per thermodynamic cycle (every 2 revolutions).
Cycle frequency:
$$f_{\text{cycle}} = \frac{N_{\text{RPM}}}{120.0} \quad [\text{cycles/sec}]$$
Indicated power:
$$P_{\text{ind}} = \eta_{\text{comb}} \cdot \eta_{\text{ind,peak}} \cdot \dot{m}_{\text{fuel}} \cdot \text{LHV} \quad [\text{W}]$$
Work per thermodynamic cycle:
$$W_{\text{cycle}} = \frac{P_{\text{ind}}}{f_{\text{cycle}}} \quad [\text{Joules/cycle}]$$
Indicated crankshaft torque:
$$T_{\text{ind}} = \frac{W_{\text{cycle}}}{4\pi} \quad [\text{N}\cdot\text{m}]$$

At any speed, $T_{\text{ind}}$ is strictly bounded by cycle work $W_{\text{cycle}} / (4\pi)$, cleanly preventing non-physical low-RPM torque singularities ($10,000\text{ N}\cdot\text{m}$).

---

### Engine Operating State Machine
- `OFF`: Engine stopped ($\text{RPM} < 50$, starter inactive). $\dot{m}_{\text{fuel}} = 0.0$, $P_{\text{ind}} = 0.0$, $T_{\text{ind}} = 0.0$, $\dot{m}_{\text{exh}} = 0.0$, $T_{\text{exh}} = T_{\text{amb}}$.
- `STARTING`: Starter motor active or cranking ($50 \le \text{RPM} < 600$). Bounded starting fuel schedule.
- `IDLE`: Engine at self-sustaining idle ($600 \le \text{RPM} < 1600$, throttle $\le 1\%$). Fuel delivery maintains idle speed ($2.2\text{ kg/h}$).
- `RUNNING`: Self-sustaining operating regime ($N_{\text{RPM}} \ge N_{\text{idle}}$). Fuel delivery responds to throttle demand constrained by FADEC smoke limiter.

---

### Rated Operating Point Consistency
- Rated power: $180\text{ HP} = 134,226\text{ W}$ at $4200\text{ RPM}$ ($\omega = 439.82\text{ rad/s}$).
- Friction torque at $4200\text{ RPM}$: $T_{\text{fric}} \approx 56.4\text{ N}\cdot\text{m}$.
- Indicated torque required: $T_{\text{ind}} \approx 361.6\text{ N}\cdot\text{m}$, Indicated power $P_{\text{ind}} \approx 159.0\text{ kW}$.
- Net shaft power: $P_{\text{brake}} = P_{\text{ind}} - P_{\text{fric}} = 134.2\text{ kW}$ ($180.0\text{ HP}$).

---

## 2. Exhaust Mass Flow, Temperature & Turbocharger Energy Output
$$\dot{m}_{\text{exh}} = \dot{m}_{\text{air}} + \dot{m}_{\text{fuel}} \quad [\text{kg/s}]$$
$$T_{\text{exh}} = T_{\text{intake}} + \frac{f_{\text{exh}} \cdot \eta_{\text{comb}} \cdot \dot{Q}_{\text{fuel}}}{\dot{m}_{\text{exh}} \cdot C_{p,\text{exh}}} \quad [\text{K}]$$
$$h_{\text{exh}} = C_{p,\text{exh}} \cdot (T_{\text{exh}} - T_{\text{amb}}) \quad [\text{J/kg}]$$
$$\dot{E}_{\text{exh}} = \dot{m}_{\text{exh}} \cdot h_{\text{exh}} \quad [\text{W}]$$
where $C_{p,\text{exh}} = 1150.0\text{ J/(kg K)}$. Zero exhaust energy when engine is `OFF`.

---

## 3. Interface Reserved for Phase 3.4 Turbo Turbine Integration

Phase 3.3.1 exposes clean thermodynamic outputs for Phase 3.4:
- `m_dot_exh` ($\text{kg/s}$): Total exhaust gas mass flow rate
- `T_exh` ($\text{K}$): Exhaust gas temperature entering turbine manifold
- `h_exh` ($\text{J/kg}$): Specific exhaust gas enthalpy
- `E_dot_exh` ($\text{W}$): Total thermal energy rate available for turbine expansion work
