# Phase 1B: Turbo / Intake References

This document records the external authoritative sources used specifically for the Phase 1B Turbo/Intake model.

## [REF-TRB-01] Rotax 914 Turbocharger Modeling Research
- **Title:** Performance prediction of aircraft gasoline turbocharged engine at high-altitudes
- **Author/Organization:** Hossein Mansouri, Fatholah Ommi
- **Journal:** Applied Thermal Engineering
- **Year:** 2019
- **DOI:** 10.1016/j.applthermaleng.2019.04.116
- **URL:** [https://www.sciencedirect.com/science/article/pii/S1359431118380268](https://www.sciencedirect.com/science/article/pii/S1359431118380268)
- **Source Type:** Peer-reviewed Journal Article
- **Information Used:** Rotax 914 high-altitude engine modeling context, turbocharger performance / compressor behavior methodology, high-altitude pressure-ratio demand, compressor choking / high-altitude limitation behavior, and validation methodology using manufacturer turbocharger information.
- **Authority Level:** HIGH (Primary architecture justification)
- **Important Limitations:** This paper does NOT provide our current surrogate parameters. Our surrogate is NOT the exact published model. We do NOT claim exact Rotax turbo RPM values from our surrogate. Our surrogate parameters ($k_{pr}$, $k_{flow}$, efficiencies, inertia, etc.) are estimated/calibrated based on general methodology, not copied from the paper.
- **Date Accessed:** September 2026

## [REF-TRB-02] Rotax 914 EASA Type Certificate
- **Title:** EASA TCDS E.122
- **Author/Organization:** European Union Aviation Safety Agency / BRP-Rotax
- **URL:** [https://www.easa.europa.eu/en/document-library/type-certificates/engine-tcds/easae122](https://www.easa.europa.eu/en/document-library/type-certificates/engine-tcds/easae122)
- **Source Type:** Official Certification Document
- **Information Used:** Takeoff MAP limit (1320 hPa) and Continuous MAP limit (1180 hPa).
- **Authority Level:** HIGHEST (Certification Authority)
- **Date Accessed:** September 2026

## [REF-TRB-03] Thermodynamic Fundamentals of Turbomachinery
- **Title:** Fundamentals of Thermodynamics (Borgnakke & Sonntag)
- **Author/Organization:** Generic academic physics text
- **Source Type:** Textbook
- **Information Used:** Isentropic expansion/compression equations, Specific heats of air vs exhaust ($1005$ vs $1150$ J/kgK).
- **Authority Level:** HIGHEST (Fundamental Physics Standard)
- **Date Accessed:** September 2026
