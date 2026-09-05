# Phase 1B: Turbo / Intake Formulas

This document catalogues the mathematical formulas implemented in the Turbo / Intake subsystem.

## [TRB-01] Turbine Isentropic Power
* **Equation**: $P_t = \dot{m}_t c_{p,exh} \eta_t T_{exh} \left(1 - \left(\frac{P_{amb}}{P_{exh}}\right)^{\frac{\gamma_{exh}-1}{\gamma_{exh}}}\right)$
* **Meaning**: Calculates the mechanical power extracted from the exhaust gas by the turbine.
* **SI Units**: $P_t$ in Watts.
* **Assumptions**: Assumes expansion from $P_{exh}$ down to $P_{amb}$ (no post-turbine restriction). Constant specific heats.
* **Classification**: STANDARD THERMODYNAMICS

## [TRB-02] Compressor Surrogate Maximum Pressure Ratio
* **Equation**: $PR_{max}(\omega) = 1 + k_{pr} \omega^2$
* **Meaning**: Predicts the maximum pressure ratio a centrifugal compressor can sustain at a given angular velocity.
* **SI Units**: Dimensionless. $\omega$ in rad/s.
* **Classification**: CALIBRATABLE SURROGATE

## [TRB-03] Compressor Surrogate Mass Flow
* **Equation**: $\dot{m}_c = k_{flow} \cdot \omega \cdot \max(0, PR_{max} - PR_{actual})$
* **Meaning**: Determines the air mass flow rate delivered by the compressor based on head difference.
* **SI Units**: kg/s.
* **Classification**: CALIBRATABLE SURROGATE

## [TRB-04] Compressor Isentropic Temperature Rise
* **Equation**: $T_{comp\_out} = T_{amb} \left(1 + \frac{PR^{\frac{\gamma-1}{\gamma}} - 1}{\eta_c}\right)$
* **Meaning**: Calculates the temperature of the air leaving the compressor, factoring in the inefficiency ($\eta_c$) that generates excess heat.
* **SI Units**: Kelvin.
* **Classification**: STANDARD THERMODYNAMICS

## [TRB-05] Turbocharger Shaft Dynamics
* **Equation**: $\frac{d\omega}{dt} = \frac{P_t - P_c - P_{loss}}{J_{turbo} \cdot \omega}$
* **Meaning**: Conservation of angular momentum. Net power accelerates or decelerates the shaft.
* **SI Units**: rad/s²
* **Classification**: STANDARD KINETICS

## [TRB-06] Intake Manifold (Plenum) Pressure State
* **Equation**: $\frac{dP_{map}}{dt} = \frac{R_{air} \cdot T_{map}}{V_{map}} (\dot{m}_c - \dot{m}_{engine})$
* **Meaning**: Ideal gas law applied to a control volume. Pressure rises if compressor inflow exceeds engine consumption.
* **SI Units**: Pa/s
* **Classification**: STANDARD FLUID DYNAMICS
