# Module 02 — 19. Propeller Aerodynamics, Gearbox Reflection, Cumulative Wear & 1000 Hz Vibration

## 1. Propeller Aerodynamic Load & Thrust Equations

$$N_{\text{prop}} = N_{\text{engine}} \cdot \text{speed\_ratio} \quad [\text{RPM}]$$
$$n_{\text{prop}} = \frac{N_{\text{prop}}}{60.0} \quad [\text{rev/s}]$$
$$T_{\text{prop\_load}} = C_q \cdot \rho_{\text{air}} \cdot n_{\text{prop}}^2 \cdot D_{\text{prop}}^5 \quad [\text{N}\cdot\text{m}]$$
$$F_{\text{prop\_thrust}} = C_t \cdot \rho_{\text{air}} \cdot n_{\text{prop}}^2 \cdot D_{\text{prop}}^4 \quad [\text{N}]$$

where:
- $\text{speed\_ratio} = 0.65$ ($N_{\text{prop}} / N_{\text{engine}}$, reduction ratio = $1.5385$)
- $C_q = 0.014$ (propeller torque coefficient loaded from YAML)
- $C_t = 0.085$ (propeller thrust coefficient loaded from YAML)
- $D_{\text{prop}} = 1.90\text{ m}$ (propeller diameter loaded from YAML)

---

## 2. Reflected Gearbox Load & Power Balance

Propeller Shaft Power Demand:
$$P_{\text{prop}} = T_{\text{prop\_load}} \cdot \omega_{\text{prop}} \quad [\text{W}]$$

Power Reflection across Gearbox Transmission ($\eta_{\text{gearbox}} = 0.97$):
$$P_{\text{engine\_load}} = \frac{P_{\text{prop}}}{\eta_{\text{gearbox}}} \quad [\text{W}]$$
$$T_{\text{engine\_load}} = \frac{T_{\text{prop\_load}} \cdot \text{speed\_ratio}}{\eta_{\text{gearbox}}} \quad [\text{N}\cdot\text{m}]$$

Power Conservation Audit: $P_{\text{prop}} = \eta_{\text{gearbox}} \cdot P_{\text{engine\_load}} \le P_{\text{engine\_load}}$. Power is strictly conserved.

---

## 3. Closed Engine Rotational Dynamics Feedback Loop

$$J_{\text{engine}} \frac{d\omega_{\text{engine}}}{dt} = T_{\text{indicated}} - T_{\text{engine\_load}} - T_{\text{friction}}$$

```
COMBUSTION
    │
    ▼
INDICATED TORQUE (T_ind)
    │
    ▼
ENGINE SHAFT (J_eng * d(omega)/dt = T_ind - T_engine_load - T_fric)
    │
    ▼
GEARBOX (N_prop = N_engine * speed_ratio)
    │
    ▼
PROPELLER RPM (n_prop rev/s)
    │
    ▼
PROPELLER AERODYNAMIC LOAD (T_prop = Cq * rho * n_prop^2 * D^5)
    │
    ▼
REFLECTED ENGINE LOAD (T_engine_load = T_prop * speed_ratio / eta_gb)
    │
    ▼
ENGINE RPM (omega)
    │
    ▼
INTAKE AIRFLOW & COMBUSTION
```

---

## 4. Cumulative Wear Degradation Subsystem

- **Bearing Wear** ($D_{\text{bearing}} \in [0.0, 1.0]$):
  $$\frac{dD_{\text{bearing}}}{dt} = k_{\text{bearing}} \cdot \left(\frac{N_{\text{engine}}}{N_{\text{rated}}}\right) \cdot \left(\frac{T_{\text{indicated}}}{T_{\text{max}}}\right) \cdot \left(\frac{\mu_{\text{ref}}}{\mu(T_{\text{oil}})}\right)$$
  Bearing wear increases mechanical friction: $T_{\text{fric}} = T_{\text{fric,nominal}} \cdot (1 + 0.50 \cdot D_{\text{bearing}})$.
- **Piston Ring Wear** ($D_{\text{ring}} \in [0.0, 1.0]$):
  $$\frac{dD_{\text{ring}}}{dt} = k_{\text{ring}} \cdot \left(\frac{N_{\text{engine}}}{N_{\text{rated}}}\right) \cdot \left(\frac{T_{\text{CHT}}}{T_{\text{ref}}}\right)$$
- **Injector Wear** ($D_{\text{injector}} \in [0.0, 1.0]$):
  $$\frac{dD_{\text{injector}}}{dt} = k_{\text{injector}} \cdot \left(\frac{\dot{m}_{\text{fuel}}}{\dot{m}_{\text{fuel,max}}}\right) \cdot \left(\frac{T_{\text{CHT}}}{T_{\text{ref}}}\right)$$

---

## 5. 1000 Hz Structural Vibration Acceleration Synthesis

Instantaneous Acceleration ($a_{\text{vibration}}(t) \quad [\text{m/s}^2]$):
$$a(t) = A_{\text{rot}} \sin(2\pi f_{\text{rot}} t) + A_{\text{fire}} \sin(2\pi f_{\text{fire}} t) + A_{\text{prop}} \sin(2\pi f_{\text{prop}} t) + A_{\text{deg}} \sin(2\pi \cdot 4.5 f_{\text{rot}} t)$$

where:
- $f_{\text{rot}} = N_{\text{engine}} / 60\text{ Hz}$ (Rotational order 1x)
- $f_{\text{fire}} = 2 \cdot f_{\text{rot}}\text{ Hz}$ (4-cylinder 4-stroke firing order 2x)
- $f_{\text{prop}} = B \cdot \frac{N_{\text{prop}}}{60}\text{ Hz}$ (Propeller blade pass order 3x)
- $a_{\text{RMS}} = \sqrt{\frac{1}{N} \sum_{i=1}^N a(t_i)^2} \quad [\text{m/s}^2]$ (1000 Hz sample rate over 1-second window)

---

## 6. Twin-Engine Independence & Asymmetric Thrust

- Engine 1 and Engine 2 maintain completely independent propeller speeds ($N_{\text{prop,1}}, N_{\text{prop,2}}$), aerodynamic torques ($T_{\text{prop,1}}, T_{\text{prop,2}}$), thrust forces ($F_{\text{thrust,1}}, F_{\text{thrust,2}}$), wear states ($D_{\text{bearing,1}}, D_{\text{bearing,2}}$), and 1000 Hz vibration acceleration outputs.
- Modifying Engine 1 operating conditions never alters Engine 2.
