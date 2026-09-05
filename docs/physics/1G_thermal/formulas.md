# Phase 1G: Engine Thermal Physics - Formulas

## 1. Thermal Capacity (THERM-01)
Calculates the lumped thermal capacities of the engine block and oil.
$$ C_{\text{CHT}} = M_{\text{CHT}} \cdot CP_{\text{CHT}} $$
$$ C_{\text{Oil}} = M_{\text{Oil}} \cdot CP_{\text{Oil}} $$
Where:
- $M$ = Mass of the component (kg)
- $CP$ = Specific heat capacity (J/(kg·K))
- $C$ = Thermal capacity (J/K)

## 2. CHT Energy Balance (THERM-02)
Governs the dynamic temperature evolution of the Cylinder Head Thermal node.
$$ \frac{dT_{\text{CHT}}}{dt} = \frac{Q_{\text{CHT\_in}} - Q_{\text{CHT}\to\text{Oil}} - Q_{\text{CHT\_cooling}}}{C_{\text{CHT}}} $$

## 3. CHT to Oil Heat Transfer (THERM-03)
Calculates the conductive/convective heat flow between the engine block and the oil.
$$ Q_{\text{CHT}\to\text{Oil}} = \frac{T_{\text{CHT}} - T_{\text{Oil}}}{R_{\text{CHT\_Oil}}} $$
Where:
- $R_{\text{CHT\_Oil}}$ = Thermal resistance (K/W)

## 4. CHT Environmental Cooling (THERM-04)
Calculates the convective heat rejected directly from the engine block/cylinders to the ambient air.
$$ Q_{\text{CHT\_cooling}} = G_{\text{CHT\_cool}} \cdot (T_{\text{CHT}} - T_{\text{amb}}) $$

## 5. Oil Energy Balance (THERM-05)
Governs the dynamic temperature evolution of the Engine Oil node.
$$ \frac{dT_{\text{Oil}}}{dt} = \frac{Q_{\text{CHT}\to\text{Oil}} - Q_{\text{Oil\_cooling}}}{C_{\text{Oil}}} $$

## 6. Oil Environmental Cooling (THERM-06)
Calculates the heat rejected by the oil cooler to the ambient air.
$$ Q_{\text{Oil\_cooling}} = G_{\text{Oil\_cool}} \cdot (T_{\text{Oil}} - T_{\text{amb}}) $$

## 7. Cooling Conductance Surrogate (THERM-07)
A reduced-order surrogate for modeling how convective cooling efficiency scales with airspeed and air density.
$$ G_{\text{cool}} = \max\left( G_{\text{min}}, G_{\text{base}} \cdot \left(\frac{\rho \cdot V}{\rho_{\text{ref}} \cdot V_{\text{ref}}}\right)^a \right) $$
Where:
- $G_{\text{base}}$ = Reference cooling conductance (W/K)
- $\rho$ = Ambient air density (kg/m³)
- $V$ = Airspeed (m/s)
- $a$ = Cooling exponent (empirical)

*Note: Oil cooling conductance ($G_{\text{Oil\_cool}}$) additionally includes an RPM-proportional term to account for the oil pump circulation rate.*

## 8. Explicit Euler Time Integration (THERM-08)
Advances the simulation thermal states to the next timestep.
$$ T_{\text{next}} = T_{\text{current}} + \frac{dT}{dt} \cdot dt $$
