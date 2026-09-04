# Phase 1A: Atmosphere Formulas

This document records the exact physical equations implemented in the runtime atmosphere model (`src/digital_twin/physics/atmosphere.py`).

## 0. Geopotential Altitude Conversion (ATM-00)
- **Formula ID:** ATM-00
- **Equation:** $h_{gp} = \frac{r_0 \times h}{r_0 + h}$
- **Physical meaning:** Standard atmosphere equations integrate using constant gravity. Geopotential altitude mathematically accounts for the actual reduction in gravity with height, allowing the standard equations to treat gravity as a constant.
- **Variables:**
  - $h$: Geometric altitude (m)
- **Constants:**
  - $r_0$: 6,356,766 m (Nominal Earth radius, ICAO Doc 7488)
- **Source:** ICAO Standard Atmosphere (1993)
- **Classification:** VERIFIED
- **Location:** `src/digital_twin/physics/atmosphere.py:AtmosphereModel.calculate`

## 1. Standard Temperature Lapse (Troposphere)
- **Formula ID:** ATM-01
- **Equation:** $T_{ISA} = T_0 - L \times h_{gp}$
- **Physical meaning:** The linear decrease in baseline temperature with altitude in the lowest layer of the atmosphere.
- **Variables:**
  - $h_{gp}$: Geopotential altitude (m)
- **Constants:**
  - $T_0$: 288.15 K (Sea level standard temperature)
  - $L$: 0.0065 K/m (Temperature lapse rate)
- **Source:** ICAO Standard Atmosphere (1993)
- **Classification:** VERIFIED
- **Location:** `src/digital_twin/physics/atmosphere.py:AtmosphereModel.calculate`

## 2. Standard Pressure (Troposphere)
- **Formula ID:** ATM-02
- **Equation:** $P = P_0 \times \left(1 - \frac{L \times h_{gp}}{T_0}\right)^{\frac{g M}{R L}}$
- **Physical meaning:** The exponential decrease of static pressure due to the weight of the air column above, integrated over a linear temperature profile.
- **Variables:**
  - $h_{gp}$: Geopotential altitude (m)
- **Constants:**
  - $P_0$: 101325.0 Pa (Sea level standard pressure)
  - $g$: 9.80665 m/s² (Standard gravity)
  - $M$: 0.0289644 kg/mol (Molar mass of dry air)
  - $R$: 8.3144598 J/(mol K) (Universal gas constant)
- **Source:** ICAO Standard Atmosphere (1993)
- **Classification:** VERIFIED
- **Location:** `src/digital_twin/physics/atmosphere.py:AtmosphereModel.calculate`

## 3. Saturation Vapor Pressure (Alduchov & Eskridge)
- **Formula ID:** ATM-03
- **Equation:** $P_{sat,hPa} = 6.1094 \times \exp\left(\frac{17.625 \times T_c}{243.04 + T_c}\right)$
- **Physical meaning:** The maximum partial pressure of water vapor that air can hold at a given temperature before condensation occurs.
- **Variables:**
  - $T_c$: Actual ambient temperature (°C)
- **Assumptions:** Valid for temperatures between -40°C and +50°C (water over liquid).
- **Source:** Alduchov, O.A. and Eskridge, R.E., 1996. (Improved Magnus Form approximation)
- **Classification:** VERIFIED (Widely accepted empirical approximation)
- **Location:** `src/digital_twin/physics/atmosphere.py:AtmosphereModel.calculate`

## 4. Actual Vapor Partial Pressure
- **Formula ID:** ATM-04
- **Equation:** $P_v = (P_{sat,hPa} \times 100) \times \frac{RH}{100}$
- **Physical meaning:** The actual partial pressure of water vapor present in the air, based on the relative humidity.
- **Variables:**
  - $P_{sat,hPa}$: Saturation vapor pressure (hPa)
  - $RH$: Relative humidity (%)
- **Classification:** VERIFIED
- **Location:** `src/digital_twin/physics/atmosphere.py:AtmosphereModel.calculate`

## 5. Moist Air Density
- **Formula ID:** ATM-05
- **Equation:** $\rho = \frac{P - P_v}{R_d \times T} + \frac{P_v}{R_v \times T}$
- **Physical meaning:** Total density of a moist air parcel, derived by summing the densities of the dry air and water vapor fractions using the Ideal Gas Law for each.
- **Variables:**
  - $P$: Total pressure (Pa)
  - $P_v$: Vapor partial pressure (Pa)
  - $T$: Actual absolute temperature (K)
- **Constants:**
  - $R_d$: ~287.05 J/(kg K) (Specific gas constant for dry air)
  - $R_v$: 461.495 J/(kg K) (Specific gas constant for water vapor)
- **Classification:** VERIFIED
- **Location:** `src/digital_twin/physics/atmosphere.py:AtmosphereModel.calculate`

## 6. Speed of Sound (Dry Air Approximation)
- **Formula ID:** ATM-06
- **Equation:** $a = \sqrt{\gamma \times R_d \times T}$
- **Physical meaning:** The speed at which acoustic waves propagate through the medium.
- **Variables:**
  - $T$: Actual absolute temperature (K)
- **Constants:**
  - $\gamma$: 1.4 (Heat capacity ratio for dry air)
- **Assumptions:** This is a dry-air, fixed-gamma approximation. The error induced by moisture is negligible for this simulation, but it is explicitly NOT a full humid-air speed of sound calculation.
- **Classification:** APPROXIMATION
- **Location:** `src/digital_twin/physics/atmosphere.py:AtmosphereModel.calculate`
