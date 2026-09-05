# Phase 1C: Airflow Formulas

This document catalogues the runtime equations implemented in `src/digital_twin/physics/airflow.py`.

### AIR-01: Cylinder Swept Volume
**Equation:** $V_{cyl} = \frac{\pi}{4} \cdot \text{bore}^2 \cdot \text{stroke}$
**Variables:** bore [m], stroke [m]
**Classification:** VERIFIED (EASA TCDS)
**Implementation:** `AirflowModel.V_D`

### AIR-02: Total Engine Displacement
**Equation:** $V_d = N_{cyl} \cdot V_{cyl}$
**Variables:** $N_{cyl}$ (4 for Rotax 914)
**Classification:** VERIFIED (EASA TCDS)
**Implementation:** `AirflowModel.V_D`

### AIR-03: Charge-Air Density
**Equation:** $\rho_{charge} = \frac{P_{charge}}{R_{air} \cdot T_{charge}}$
**Variables:** $P_{charge}$ [Pa], $T_{charge}$ [K], $R_{air}$ [287.05 J/(kg K)]
**Classification:** VERIFIED (Thermodynamics)
**Implementation:** `AirflowModel._cylinder_mass_flow`

### AIR-04: Speed-Density Cylinder Filling
**Equation:** $\dot{m}_{cyl} = \eta_v \cdot \rho_{charge} \cdot V_d \cdot \frac{N}{2}$
**Variables:** $\dot{m}_{cyl}$ [kg/s], $\eta_v$ [-], $N$ [rev/s]
**Classification:** VERIFIED (MVEM Literature)
**Implementation:** `AirflowModel._cylinder_mass_flow`

### AIR-05: RPM Conversion
**Equation:** $N = \frac{\text{RPM}}{60}$
**Variables:** RPM [rev/min]
**Classification:** VERIFIED (Unit Conversion)
**Implementation:** `AirflowModel._cylinder_mass_flow` (implemented as RPM/120 for N/2)

### AIR-06: Throttle Effective Area
**Equation:** $A_{eff} = A_{idle} + \text{throttle}^2 \cdot (A_{max} - A_{idle})$
**Variables:** throttle [0.0 to 1.0], $A_{max}$ [m$^2$], $A_{idle}$ [m$^2$]
**Classification:** CALIBRATABLE SURROGATE
**Implementation:** `AirflowModel._throttle_effective_area`

### AIR-07: Compressible Restriction Mass-Flow
**Equation (Unchoked):** $\dot{m}_{throttle} = C_d A_{eff} \frac{P_{up}}{\sqrt{R_{air} T_{up}}} \sqrt{\frac{2\gamma}{\gamma-1} \left( PR^{\frac{2}{\gamma}} - PR^{\frac{\gamma+1}{\gamma}} \right)}$
**Variables:** $P_{up}$ [Pa], $T_{up}$ [K], $PR = P_{down}/P_{up}$
**Classification:** VERIFIED (Fluid Dynamics)
**Implementation:** `AirflowModel._throttle_mass_flow`

### AIR-08: Choked-Flow Criterion
**Equation:** If $PR \le \left(\frac{2}{\gamma+1}\right)^{\frac{\gamma}{\gamma-1}}$, flow is choked.
**Variables:** $\gamma$ (1.4 for air)
**Classification:** VERIFIED (Fluid Dynamics)
**Implementation:** `AirflowModel._throttle_mass_flow`

### AIR-09: Volumetric Efficiency Surrogate
**Equation:** $\eta_v = \text{clip}\left(\eta_{v,base} + c_{rpm} \left[1 - \left(\frac{RPM - RPM_{opt}}{RPM_{opt}}\right)^2\right] + c_p \left(\frac{P_{charge}}{P_{ref}}\right), \eta_{v,min}, \eta_{v,max}\right)$
**Variables:** $\eta_{v,base}, c_{rpm}, c_p, RPM_{opt}$
**Classification:** ESTIMATED SURROGATE
**Implementation:** `AirflowModel._calculate_eta_v`

### AIR-10: Downstream Pressure Numerical Solver
**Equation:** Find $P_{charge}$ such that $\dot{m}_{throttle}(P_{charge}) - \dot{m}_{cyl}(P_{charge}) = 0$
**Classification:** VERIFIED (Numerical Method - Bisection)
**Implementation:** `AirflowModel.calculate`
