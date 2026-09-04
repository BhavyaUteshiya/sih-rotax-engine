# SIH26054 Digital Twin — Master Physics Formula Registry

This is the master index of all physics and empirical formulas implemented in the codebase.

## Atmosphere (Phase 1A)

| ID | Subsystem | Equation | Meaning | Variables (Units) | Source | Class | Code Location | Status |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| ATM-01 | Atmosphere | $T = T_0 - L \times h$ | ISA Troposphere Temperature Lapse | $h$ (m) | ICAO Standard Atmosphere | VERIFIED | `atmosphere.py:calculate` | Implemented |
| ATM-02 | Atmosphere | $P = P_0 \times (1 - \frac{L \times h}{T_0})^{\frac{g M}{R L}}$ | ISA Troposphere Hydrostatic Pressure | $h$ (m) | ICAO Standard Atmosphere | VERIFIED | `atmosphere.py:calculate` | Implemented |
| ATM-03 | Atmosphere | $P_{sat} = 6.1078 \times 10^{\frac{7.5 \times T_c}{T_c + 237.3}}$ | Saturation Vapor Pressure (Magnus) | $T_c$ (°C) | Alduchov and Eskridge (1996) | VERIFIED | `atmosphere.py:calculate` | Implemented |
| ATM-04 | Atmosphere | $P_v = P_{sat} \times (RH / 100)$ | Actual Vapor Partial Pressure | $RH$ (%) | Standard Thermodynamics | VERIFIED | `atmosphere.py:calculate` | Implemented |
| ATM-05 | Atmosphere | $\rho = \frac{P - P_v}{R_d T} + \frac{P_v}{R_v T}$ | Moist Air Density | $P, P_v$ (Pa), $T$ (K) | Standard Thermodynamics | VERIFIED | `atmosphere.py:calculate` | Implemented |
| ATM-06 | Atmosphere | $a = \sqrt{\gamma \times R_d \times T}$ | Speed of Sound | $T$ (K) | Standard Physics | VERIFIED | `atmosphere.py:calculate` | Implemented |

*(Downstream modules like 1B-Intake and 1C-Combustion will be registered here once implemented.)*
