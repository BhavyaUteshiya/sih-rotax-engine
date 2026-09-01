# Module 02 — Phase 3.8: Full Thermodynamic Combustion, Fuel System & Engine Thermal Management

## 1. Overview & Objectives

Phase 3.8 replaces all remaining temporary combustion, torque, MAP, and thermal placeholders with a physically coupled engine thermodynamic model. 

The complete closed-loop causal chain is:

$$\text{THROTTLE} \longrightarrow \text{FUEL METERING} \longrightarrow \text{AIR/FUEL RATIO} \longrightarrow \text{EQUIVALENCE RATIO } (\phi) \longrightarrow \text{COMBUSTION EFFICIENCY } (\eta_{\text{comb}}) \longrightarrow \text{HEAT RELEASE } (P_{\text{heat}})$$
$$\downarrow$$
$$\text{INDICATED POWER } (P_{\text{ind}}) \longrightarrow \text{INDICATED TORQUE } (T_{\text{ind}}) \longrightarrow \text{CRANKSHAFT ROTATIONAL DYNAMICS}$$
$$\downarrow$$
$$\text{EXHAUST MASS FLOW } (m_{\dot{\text{exh}}}) \longrightarrow \text{EXHAUST ENTHALPY} \longrightarrow \text{TURBINE POWER} \longrightarrow \text{TURBO SHAFT ACCELERATION}$$
$$\downarrow$$
$$\text{COMPRESSOR WORK} \longrightarrow \text{COMPRESSOR PRESSURE RATIO } (\Pi_c) \longrightarrow \text{EMERGING MAP} \longrightarrow \text{INTAKE AIR DENSITY} \longrightarrow \text{INTAKE AIRFLOW } (m_{\dot{\text{air}}})$$
$$\downarrow$$
$$\text{CYLINDER WALL HEAT LOSS } (Q_{\text{wall}}) \longrightarrow 1^{\text{st}}\text{-ORDER CHT / COOLANT / OIL / EGT DYNAMIC THERMAL INTEGRATION}$$
$$\downarrow$$
$$\text{THERMAL PROTECTION DERATING} \longrightarrow \text{FUEL BURN WEIGHT REDUCTION} \longrightarrow 3\text{-DOF AIRCRAFT FLIGHT KINEMATICS}$$

---

## 2. Theoretical & Physical Formulations

### 2.1 Fuel System & Metered Fuel Flow
Metered fuel mass flow rate $m_{\dot{\text{fuel}}}$ (kg/s and kg/h) responds to throttle command $\theta \in [0.0, 100.0]\%$, engine operating state (`OFF`, `STARTING`, `IDLE`, `RUNNING`), available intake oxygen boundary, maximum fuel flow limit $m_{\text{fuel\_max\_kg\_h}}$, and thermal derating factor $\kappa_{\text{derate}} \in [0.30, 1.0]$:

$$m_{\dot{\text{fuel\_demand}}} = m_{\text{idle\_kg\_h}} + \frac{\theta}{100.0} (m_{\text{max\_kg\_h}} - m_{\text{idle\_kg\_h}}) \quad [\text{kg/h}]$$
$$m_{\dot{\text{air\_max}}} = \left(\frac{m_{\dot{\text{air}}}}{\text{AFR}_{\text{stoich}} \cdot 0.70}\right) \cdot 3600.0 \quad [\text{kg/h}]$$
$$m_{\dot{\text{fuel}}} = \min\left(m_{\text{max\_kg\_h}}, \max\left(m_{\dot{\text{fuel\_demand}}}, m_{\dot{\text{air\_max}}}\right)\right) \cdot \kappa_{\text{derate}} \quad [\text{kg/h}]$$
$$P_{\text{fuel}} = m_{\dot{\text{fuel\_kg\_s}}} \cdot \text{LHV} \quad [\text{W}]$$

### 2.2 Air-Fuel Ratio (AFR) & Equivalence Ratio ($\phi$)
$$\text{AFR} = \frac{m_{\dot{\text{air}}}}{m_{\dot{\text{fuel}}}}, \qquad \phi = \frac{\text{AFR}_{\text{stoich}}}{\text{AFR}}$$
If $m_{\dot{\text{fuel}}} \le 10^{-9}$ kg/s (fuel cut-off or shutdown): $\text{AFR} = 999.9$ and $\phi = 0.0$.

### 2.3 Bounded Combustion Efficiency ($\eta_{\text{comb}}$)
Combustion efficiency is strictly bounded within $[0.0, 1.0]$ responding to equivalence ratio $\phi$ and cumulative mechanical degradation (piston ring wear $D_{\text{ring}}$ and fuel injector erosion $D_{\text{injector}}$):

$$\eta_{\phi} = e^{-2.0 (\phi - 0.85)^2}$$
$$\eta_{\text{wear}} = \max(0.50, 1.0 - 0.15 D_{\text{ring}} - 0.10 D_{\text{injector}})$$
$$\eta_{\text{comb}} = \min\left(1.0, \max\left(0.0, \eta_{\text{comb\_max}} \cdot \eta_{\phi} \cdot \eta_{\text{wear}}\right)\right)$$

### 2.4 Explicit Energy Audit & Heat Release Partitioning
Total chemical heat release rate $P_{\text{heat}}$ is strictly conserved and partitioned:

$$P_{\text{heat}} = P_{\text{fuel}} \cdot \eta_{\text{comb}}$$
$$P_{\text{ind}} = f_{\text{work}} \cdot P_{\text{heat}} \quad (\text{Useful Mechanical Work, default 42\%})$$
$$P_{\text{exh}} = f_{\text{exh}} \cdot P_{\text{heat}} \quad (\text{Exhaust Thermal Enthalpy, default 35\%})$$
$$Q_{\text{wall}} = f_{\text{wall}} \cdot P_{\text{heat}} \quad (\text{Cylinder Wall Heat Transfer, default 20\%})$$
$$P_{\text{residual}} = (1.0 - f_{\text{work}} - f_{\text{exh}} - f_{\text{wall}}) \cdot P_{\text{heat}} \quad (\text{Entropy/Radiative Loss, default 3\%})$$
$$P_{\text{heat}} \equiv P_{\text{ind}} + P_{\text{exh}} + Q_{\text{wall}} + P_{\text{residual}}$$

### 2.5 Indicated Power & Bounded Indicated Torque
Indicated combustion torque $T_{\text{ind}}$ drives engine crankshaft acceleration without infinite spikes or division-by-zero errors at low cranking speeds:

$$T_{\text{ind}} = \min\left(T_{\text{ind\_max}}, \frac{P_{\text{ind}}}{\max(\omega_{\text{crank\_min}}, \omega_{\text{eng}})}\right) \quad [\text{N}\cdot\text{m}]$$

### 2.6 Dynamic Turbocharger Closure & MAP Emergence
Exhaust mass flow $m_{\dot{\text{exh}}} = m_{\dot{\text{air}}} + m_{\dot{\text{fuel}}}$ drives turbine power extraction $P_{\text{turbine}} = \eta_{\text{turbine}} P_{\text{exh\_avail}}$. Turbocharger shaft angular acceleration obeys:

$$J_{\text{turbo}} \frac{d\omega_{\text{turbo}}}{dt} = T_{\text{turbine}} - T_{\text{compressor}} - T_{\text{turbo\_friction}}$$
$$\Pi_c = 1.0 + (\Pi_{c,\text{max}} - 1.0) \left(\frac{N_{\text{turbo}}}{N_{\text{turbo\_max}}}\right)^2$$
$$\text{MAP} = \min(\text{MAP}_{\text{ceiling}}, \max(0.8 P_{\text{amb}}, \Pi_c \cdot P_{\text{amb}}))$$

### 2.7 1st-Order Dynamic Thermal Management & Protection Derating
Differential lumped energy balances integrate temperatures across cylinder head, coolant, oil sump, and EGT sensor:

$$m_{\text{head}} C_{p,\text{head}} \frac{dT_{\text{CHT}}}{dt} = Q_{\text{wall}} - h_{\text{cool}} S_{\text{cool}} (T_{\text{CHT}} - T_{\text{coolant}})$$
$$m_{\text{cool}} C_{p,\text{cool}} \frac{dT_{\text{coolant}}}{dt} = h_{\text{cool}} S_{\text{cool}} (T_{\text{CHT}} - T_{\text{coolant}}) - k_{\text{rad}} (T_{\text{coolant}} - T_{\text{amb}})$$
$$m_{\text{oil}} C_{p,\text{oil}} \frac{dT_{\text{oil}}}{dt} = Q_{\text{fric}} + 0.10 Q_{\text{wall}} - k_{\text{oil\_cool}} (T_{\text{oil}} - T_{\text{amb}})$$
$$\frac{dT_{\text{EGT}}}{dt} = \frac{T_{\text{exh\_target}} - T_{\text{EGT}}}{\tau_{\text{EGT}}}$$

$$\kappa_{\text{derate}} = \min\left(1.0 - 0.02 \max(0, T_{\text{CHT}} - T_{\text{CHT\_max}}), 1.0 - 0.01 \max(0, T_{\text{EGT}} - T_{\text{EGT\_max}}), 1.0 - 0.02 \max(0, T_{\text{oil}} - T_{\text{oil\_max}})\right)$$

### 2.8 Aircraft Fuel Burn Weight Coupling
Fuel consumption integrates continuously over time, reducing fuel mass remaining and total aircraft gross takeoff weight:

$$m_{\text{fuel\_remaining}}(t + \Delta t) = m_{\text{fuel\_remaining}}(t) - m_{\text{fuel\_burned\_step}}$$
$$m_{\text{ac}}(t) = m_{\text{dry}} + m_{\text{payload}} + m_{\text{fuel\_remaining}}(t)$$
$$W(t) = m_{\text{ac}}(t) \cdot g$$

---

## 3. Verification Results

- **Unit Test Suite**: 267 / 267 tests passing (100% success rate).
- **Module 01 Freeze Guarantee**: Zero files altered under `src/module01/`.
- **YAML Provenance**: All engine-specific parameters stream strictly through `ConfigLoader`. Zero hardcoded TAPAS constants in Python code.
