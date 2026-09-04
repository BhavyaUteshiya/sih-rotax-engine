# Phase 1A: Atmosphere Parameters

This document details the constants, physical parameters, and boundaries used within the `AtmosphereModel`.

| Parameter | Symbol | Value | Unit | Source | Classification | Purpose | Editable/Calibratable? | Notes |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Standard Gravity** | $g$ | `9.80665` | m/s² | ICAO Standard Atmosphere | VERIFIED | Hydrostatic pressure gradient | No | Universal physical constant |
| **Universal Gas Constant** | $R$ | `8.3144598` | J/(mol K) | CODATA | VERIFIED | Ideal gas law, pressure/density relation | No | Universal physical constant |
| **Dry Air Molar Mass** | $M_d$ | `0.0289644` | kg/mol | ICAO Standard Atmosphere | VERIFIED | Convert universal gas constant to specific | No | Standard physical constant |
| **Specific Gas Const. (Dry)** | $R_d$ | `287.0528` | J/(kg K) | Derived ($R/M_d$) | DERIVED | Dry air density | No | Calculated internally |
| **Specific Gas Const. (Vapor)** | $R_v$ | `461.495` | J/(kg K) | WMO | VERIFIED | Water vapor density | No | Standard physical constant |
| **Heat Capacity Ratio** | $\gamma$ | `1.4` | - | Standard Physics | VERIFIED | Speed of sound calculation | No | Valid for dry diatomic gases |
| **Sea Level Temp (ISA)** | $T_0$ | `288.15` | K | ICAO Standard Atmosphere | VERIFIED | ISA temperature baseline | No | Defines standard day |
| **Sea Level Press (ISA)** | $P_0$ | `101325.0` | Pa | ICAO Standard Atmosphere | VERIFIED | ISA pressure baseline | No | Defines standard day |
| **Temperature Lapse Rate** | $L$ | `0.0065` | K/m | ICAO Standard Atmosphere | VERIFIED | Troposphere temp gradient | No | Only valid in Troposphere |
| **Tropopause Limit** | $h_{max}$| `11000.0` | m | ICAO Standard Atmosphere | VERIFIED | Constrains model validity | No | Limits pressure equation range |

### Separation of Concerns
Note that these are entirely universal and standard atmospheric constants. There are **zero** Rotax 914 engine-specific parameters or arbitrary engineering estimates in this file. The environmental physics layer is entirely general.
