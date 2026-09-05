# Module 02 — 15. Intake Manifold & Turbocharger Compressor Model

## 1. Mathematical Equations & Physical Models

### Ambient Atmosphere Input Coupling
$$\text{Altitude } h \implies p_{\text{amb}}(h), T_{\text{amb}}(h), \rho_{\text{amb}}(h)$$

### Manifold Absolute Pressure (MAP) & Compressor Pressure Ratio ($\pi_c$)
$$p_{\text{boost\_max}} = \min\left(p_{\text{max\_map}} - p_{\text{amb}}, p_{\text{amb}} \cdot (\pi_{c,\text{max}} - 1.0)\right)$$
$$p_m = P_{\text{manifold\_absolute}} = p_{\text{amb}} + \left(\frac{\theta}{100.0}\right) \cdot p_{\text{boost\_max}}$$
$$\pi_c = \frac{P_{\text{manifold\_absolute}}}{p_{\text{amb}}}$$

### Gauge Boost Pressure
$$P_{\text{boost\_gauge}} = \max\left(0.0, P_{\text{manifold\_absolute}} - p_{\text{amb}}\right)$$

### Compressor Discharge Outlet Temperature ($T_{\text{comp\_out}}$)
Isentropic compression temperature rise with compressor efficiency $\eta_c$:
$$T_{\text{comp\_out}} = T_{\text{amb}} \cdot \left[ 1 + \frac{1}{\eta_c} \left( \pi_c^{\frac{\gamma - 1}{\gamma}} - 1 \right) \right]$$
where $\gamma = 1.4 \implies \frac{\gamma - 1}{\gamma} \approx 0.285714$.

### Intake Air Mass Density ($\rho_{\text{intake}}$)
$$\rho_{\text{intake}} = \frac{P_{\text{manifold\_absolute}}}{R_d \cdot T_{\text{comp\_out}}} \quad [\text{kg/m}^3]$$
where $R_d = 287.058\text{ J/(kg K)}$.

### Engine Volumetric Efficiency ($\eta_v$)
$$\eta_v(N_{\text{RPM}}) = 0.82 + 0.10 \left(\frac{N_{\text{RPM}}}{N_{\text{rated}}}\right) - 0.08 \left(\frac{N_{\text{RPM}}}{N_{\text{rated}}}\right)^2$$
bounded $0.65 \le \eta_v \le 0.95$.

### Engine Air Mass Flow Rate ($\dot{m}_{\text{air}}$)
For a 4-stroke engine ($V_d$ total volume in $\text{m}^3$):
$$\dot{m}_{\text{air,kg/s}} = \eta_v \cdot \rho_{\text{intake}} \cdot V_d \cdot \left(\frac{N_{\text{RPM}}}{120.0}\right) \quad [\text{kg/s}]$$
$$\dot{m}_{\text{air,kg/h}} = \dot{m}_{\text{air,kg/s}} \times 3600.0 \quad [\text{kg/h}]$$

---

## 2. Parameter Implementation Status Summary

| Parameter ID | Canonical Unit | Category | Status | Upstream Causes | Downstream Effects |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `manifold_pressure` | `PASCAL` | `ENGINE_DYNAMICS` | `IMPLEMENTED` | `throttle`, `ambient_pressure`, `boost_pressure` | `air_mass_flow` |
| `boost_pressure` | `PASCAL` | `TURBOCHARGER` | `DERIVED` | `turbo_speed`, `ambient_pressure` | `manifold_pressure` |
| `turbo_speed` | `RAD_PER_SEC` | `TURBOCHARGER` | `IMPLEMENTED` | `engine_rpm`, `throttle` | `boost_pressure` |
| `air_mass_flow` | `KG_PER_SEC` | `ENGINE_DYNAMICS` | `DERIVED` | `manifold_pressure`, `air_density`, `engine_rpm` | `fuel_flow`, `air_fuel_ratio` |
