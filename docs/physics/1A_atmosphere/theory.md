# Phase 1A: Atmosphere Theory

## Introduction
The atmosphere model serves as the environmental foundation for the SIH26054 Digital Twin. The Rotax 914 is an internal combustion engine that relies on ingesting ambient air; therefore, its performance, thermal behavior, and power output are intrinsically linked to the physical state of the atmosphere. 

This document explains the physical theory behind the selected atmospheric model, how it varies with altitude, and how environmental parameters such as humidity and temperature affect the air density.

## The Standard Atmosphere
The **International Standard Atmosphere (ISA)** is an atmospheric model of how pressure, temperature, density, and viscosity of the Earth's atmosphere change over a wide range of altitudes. For our prototype simulation envelope (up to approximately 30,000 ft or 9,144 m), we only need to model the lowest layer of the atmosphere: the **Troposphere** (which extends up to 11,000 m).

1. **Geopotential Altitude Conversion**: As Earth's gravity decreases with altitude, the standard atmosphere model uses *geopotential altitude* ($h_{gp}$) instead of pure geometric altitude to maintain simplified hydrostatic integration.
2. **Tropospheric Lapse Rate**: The temperature drops linearly with geopotential altitude up to 11,000 meters.
3. **Hydrostatic Equilibrium**: The pressure drops exponentially as a function of temperature and geopotential altitude.

### Temperature Variation with Altitude
In the Troposphere, temperature decreases linearly with altitude. This rate of decrease is called the **Temperature Lapse Rate ($L$)**. In the ISA model, this lapse rate is defined as exactly 0.0065 K/m.
Therefore, the standard temperature at any altitude $h$ is:
$$ T_{ISA} = T_0 - (L \times h) $$
Where $T_0$ is the standard sea-level temperature (288.15 K or 15 °C).

### Hydrostatic Equilibrium and Pressure
The atmosphere is held to the Earth by gravity. The pressure at any given altitude is the weight of the air column above it. Because air is compressible, its density decreases as pressure decreases, leading to an exponential decay of pressure with altitude. 
By combining the ideal gas law ($P = \rho R T$) with the hydrostatic equation ($dP = -\rho g dh$) and integrating over the linear temperature profile of the troposphere, we obtain the standard pressure equation:
$$ P = P_0 \times \left(1 - \frac{L \times h}{T_0}\right)^{\frac{g M}{R L}} $$

## Standard Atmosphere vs. Real Weather
The ISA is merely a standard baseline. Real weather introduces deviations:
- **Temperature Deviations:** Real days can be hotter or colder than standard. This is modeled by adding a $\Delta T$ to the standard temperature ($T_{actual} = T_{ISA} + \Delta T$). 
- **Humidity:** The ISA assumes dry air. Real air contains water vapor, which significantly alters density.

Our model supports real weather by allowing the user (or scenario) to specify the actual ambient temperature and relative humidity, while still relying on the ISA pressure gradient as the baseline constraint.

## The Effect of Humidity on Air Density
Air density is one of the most critical atmospheric outputs because the mass flow of air through the engine's intake determines how much fuel can be burned, and the density of air determines the aerodynamic load on the propeller.

A common misconception is that humid air is denser than dry air. **Humid air is actually less dense than dry air at the same temperature and pressure.** This is because water molecules ($H_2O$) have a molar mass of ~18 g/mol, which is lighter than the average molar mass of dry air (mostly $N_2$ and $O_2$, ~29 g/mol). When water vapor displaces dry air molecules, the overall gas mixture becomes lighter.

To model this, we calculate the saturation vapor pressure of water at the given temperature using the **Magnus Formula**, and then scale it by the Relative Humidity to find the actual vapor partial pressure ($P_v$).
We then split the total pressure into dry air partial pressure ($P_d$) and water vapor partial pressure ($P_v$). The total moist air density is the sum of the densities of these two ideal gases.

## Why the Atmosphere Matters to the Rotax 914
The output of this atmosphere model ($P, T, \rho$) will later feed directly into the engine's physics:
1. **Turbocharger Performance:** The turbocharger compresses the ambient air. Its pressure ratio depends on the ambient pressure ($P$).
2. **Air Mass Flow:** The volumetric efficiency of the engine determines a volume of air ingested per revolution. The *mass* of that air depends entirely on the air density ($\rho$).
3. **Thermal Behavior:** The ambient temperature ($T$) affects the cooling efficiency of the cylinder heads and oil cooler.
4. **Propeller Loading:** The torque required to spin the propeller at a given RPM scales directly with the air density ($\rho$).

## Assumptions and Limitations
- The model assumes the aircraft operates strictly within the Troposphere (below 11,000 meters). Above this altitude, the temperature lapse rate becomes zero (the Tropopause), and the pressure equation changes. This limitation is acceptable for MALE UAVs operating below 30,000 ft.
- We assume standard sea-level pressure ($P_0$) is fixed at 101325 Pa. True barometric weather systems (e.g., high/low pressure fronts) are not modeled as independent pressure offsets, though they could theoretically be added in the future.
- The model treats the air as an ideal gas.
