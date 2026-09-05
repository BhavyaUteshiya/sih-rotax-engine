# SIH26054 Digital Twin — Master Reference Registry

This is the master reference list for the entire Rotax 914 Digital Twin project.

## A. Rotax 914 Authoritative Sources
- **ID:** REF-TRB-02
- **Title:** EASA TCDS E.122
- **Author/Organization:** European Union Aviation Safety Agency / BRP-Rotax
- **URL:** [https://www.easa.europa.eu/en/document-library/type-certificates/engine-tcds/easae122](https://www.easa.europa.eu/en/document-library/type-certificates/engine-tcds/easae122)
- **Category:** A
- **Information Used:** Takeoff MAP limit (1320 hPa) and Continuous MAP limit (1180 hPa).
- **Authority Level:** HIGHEST
- **Date Accessed:** September 2026

## B. EASA Certification Sources
*(Reserved for future use)*

## C. Rotax Operator / Maintenance Documentation
- **ID:** REF-OP-01
- **Title:** Operators Manual for Rotax Engine Type 914 Series
- **Author/Organization:** BRP-Rotax
- **URL:** [https://www.flyrotax.com/assets/filesDistributors/dis0002/n/om914-2-2.pdf](https://www.flyrotax.com/assets/filesDistributors/dis0002/n/om914-2-2.pdf)
- **Category:** C
- **Information Used:** Fuel consumption metrics (~33 L/h at takeoff load), engine operating limits.
- **Authority Level:** HIGHEST
- **Date Accessed:** September 2026

- **ID:** REF-OP-02
- **Title:** Illustrated Parts Catalog for Rotax Engine Type 912 and 914 Series
- **Author/Organization:** BRP-Rotax
- **URL:** [https://www.flyrotax.com/assets/filesDistributors/dis0002/IPC_912_914-Series_ED4_R3.pdf](https://www.flyrotax.com/assets/filesDistributors/dis0002/IPC_912_914-Series_ED4_R3.pdf)
- **Category:** C
- **Information Used:** Fuel system design parameters, fuel pressure nominal and limits.
- **Authority Level:** HIGHEST
- **Date Accessed:** September 2026

## D. Rotax-specific Research
- **ID:** REF-TRB-01
- **Title:** Performance prediction of aircraft gasoline turbocharged engine at high-altitudes
- **Author/Organization:** Hossein Mansouri, Fatholah Ommi
- **Journal:** Applied Thermal Engineering
- **Year:** 2019
- **DOI:** 10.1016/j.applthermaleng.2019.04.116
- **URL:** [https://www.sciencedirect.com/science/article/pii/S1359431118380268](https://www.sciencedirect.com/science/article/pii/S1359431118380268)
- **Category:** D
- **Information Used:** Rotax 914 high-altitude engine modeling context, turbocharger performance / compressor behavior methodology, high-altitude pressure-ratio demand, compressor choking / high-altitude limitation behavior, and validation methodology using manufacturer turbocharger information.
- **Important Limitations:** This paper does NOT provide our current surrogate parameters. Our surrogate is NOT the exact published model. We do NOT claim exact Rotax turbo RPM values from our surrogate. Our surrogate parameters ($k_{pr}$, $k_{flow}$, efficiencies, inertia, etc.) are estimated/calibrated based on general methodology, not copied from the paper.
- **Authority Level:** HIGH
- **Date Accessed:** September 2026

## E. Atmosphere / Thermodynamics
- **ID:** REF-ATM-01
- **Title:** Manual of the ICAO Standard Atmosphere (extended to 80 kilometres (262 500 feet))
- **Author/Organization:** International Civil Aviation Organization (ICAO)
- **URL:** N/A (Doc 7488/3)
- **Category:** E
- **Information Used:** Troposphere temperature lapse rate and hydrostatic pressure equation.
- **Authority Level:** HIGHEST
- **Date Accessed:** September 2026

- **ID:** REF-ATM-02
- **Title:** CODATA Recommended Values of the Fundamental Physical Constants
- **Author/Organization:** Committee on Data for Science and Technology (CODATA)
- **URL:** https://physics.nist.gov/cuu/Constants/
- **Category:** E
- **Information Used:** Universal Gas Constant ($R = 8.3144598$ J/(mol K)).
- **Authority Level:** HIGHEST
- **Date Accessed:** September 2026

- **ID:** REF-ATM-03
- **Title:** Improved Magnus Form Approximation of Saturation Vapor Pressure
- **Author/Organization:** Alduchov, O.A. and Eskridge, R.E.
- **URL:** https://doi.org/10.1175/1520-0450(1996)035%3C0601:IMFAOS%3E2.0.CO;2
- **Category:** E
- **Information Used:** Saturation vapor pressure coefficients: $e_s(T) = 6.1094 \times \exp\left(\frac{17.625 \times T}{243.04 + T}\right)$.
- **Authority Level:** HIGH
- **Date Accessed:** September 2026

## F. Turbocharger / Intake
- **ID:** REF-TRB-03
- **Title:** Fundamentals of Thermodynamics (Borgnakke & Sonntag)
- **Author/Organization:** Generic academic physics text
- **URL:** N/A
- **Category:** F
- **Information Used:** Isentropic expansion/compression equations, Specific heats.
- **Authority Level:** HIGHEST
- **Date Accessed:** September 2026

## G. Engine Physics
- **ID:** REF-ENG-01
- **Title:** The Analysis of Mean Value SI Engine Models
- **Author/Organization:** Hendricks & Vesterholm
- **Journal:** SAE 920682
- **URL:** [https://doi.org/10.4271/920682](https://doi.org/10.4271/920682)
- **Category:** G
- **Information Used:** Speed-density calculation methodology for Mean Value Engine Modeling (MVEM), generic physical flow restrictions.
- **Authority Level:** HIGH
- **Date Accessed:** September 2026

- **ID:** REF-ENG-02
- **Title:** Modelling of the Intake Manifold Filling Dynamics
- **Journal:** SAE 960037
- **Category:** G
- **Information Used:** Intake manifold charging and restriction flows methodology.
- **Authority Level:** HIGH
- **Date Accessed:** September 2026

- **ID:** REF-ENG-03
- **Title:** Internal Combustion Engine Fundamentals
- **Author/Organization:** Heywood, J. B. (McGraw-Hill Education)
- **Year:** 1988
- **Category:** G
- **Information Used:** General quadratic friction torque polynomial modeling ($\tau_f = C_0 + C_1\omega + C_2\omega^2$) and mechanical efficiency characteristics.
- **Authority Level:** HIGH
- **Date Accessed:** September 2026

## H. Propeller / UAV Propulsion
- **ID:** REF-PROP-01
- **Title:** Aerodynamics, Aeronautics, and Flight Mechanics (2nd ed.)
- **Author/Organization:** McCormick, B. W. (John Wiley & Sons)
- **Year:** 1995
- **Category:** H
- **Information Used:** Standard nondimensional propeller aerodynamic thrust and torque characteristics ($C_T = f(J)$, $C_Q = f(J)$, $T_{prop} = C_T \rho n^2 D^4$, and $\tau_{prop} = C_Q \rho n^2 D^5$).
- **Authority Level:** HIGH
- **Date Accessed:** September 2026

- **ID:** REF-PROP-02
- **Title:** Phase 1F Propeller Surrogate Model
- **Author/Organization:** Digital Twin Internal Calibration
- **URL:** N/A
- **Category:** H
- **Information Used:** Defines the specific $C_T$ and $C_Q$ polynomial parameters used in the absence of a specific UAV propeller map.
- **Authority Level:** CALIBRATION
- **Date Accessed:** September 2026

## I. Engine Thermal Physics
- **ID:** REF-THM-01
- **Title:** Fundamentals of Heat and Mass Transfer
- **Author/Organization:** Incropera, DeWitt
- **Category:** I
- **Information Used:** Lumped-capacitance method basis (THERM-02, THERM-05) and standard convective heat transfer scaling laws (THERM-07).
- **Authority Level:** HIGH
- **Date Accessed:** September 2026

- **ID:** REF-THM-02
- **Title:** Digital Twin Internal Calibration - Phase 1G
- **Author/Organization:** Digital Twin Calibration
- **Category:** I
- **Information Used:** Specific values for conductances, thermal mass, and heat fraction, calibrated internally to reproduce nominal Rotax limits at steady-state high-power settings.
- **Authority Level:** CALIBRATION
- **Date Accessed:** September 2026

## J. Digital Twin
*(Reserved for future use)*

## J. AI / ML
*(Reserved for future use)*

## K. Explainable AI
*(Reserved for future use)*

## L. Edge AI / deployment
*(Reserved for future use)*

## M. CAN / secure telemetry
*(Reserved for future use)*
