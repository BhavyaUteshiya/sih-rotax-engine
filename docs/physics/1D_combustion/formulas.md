# Phase 1D: Fuel Flow & Combustion Formulas

This document outlines the core mathematical relations implemented in `src/digital_twin/physics/combustion.py`.

## FUEL-01: Equivalence Ratio Surrogate
$$ \phi_{target} = \phi_{base} + \text{LoadEnrichment}(P_{map}) + \text{SpeedEnrichment}(N) $$
$$ \phi = \max(\phi_{min}, \min(\phi_{max}, \phi_{target})) $$

## FUEL-02: Fuel Pressure Constraints
$$ \Delta P_{fuel} = P_{fuel} - P_{airbox} $$
The nominal value is 25 kPa. The model reports `LOW` if $< 15$ kPa and `HIGH` if $> 35$ kPa.

## FUEL-03: Fuel Mass Flow
$$ AFR = \frac{AFR_{stoich}}{\phi} $$
$$ \dot{m}_{fuel} = \frac{\dot{m}_{air}}{AFR} $$

## FUEL-04: Fuel Volume Flow
$$ \dot{V}_{fuel (L/h)} = \frac{\dot{m}_{fuel}}{\rho_{fuel}} \times 3600 \times 1000 $$

## ENE-01: Chemical Power Release
$$ P_{fuel} = \dot{m}_{fuel} \cdot LHV $$
$$ P_{release} = P_{fuel} \cdot \eta_{comb} $$
$$ P_{unreleased} = P_{fuel} - P_{release} $$

## ENE-02: Energy Partition
$$ P_{indicated} = P_{release} \cdot \eta_{indicated} $$
$$ P_{remaining} = \max(0, P_{release} - P_{indicated}) $$
$$ P_{exhaust} = P_{remaining} \cdot \eta_{exhaust\_partition} $$
$$ P_{heat\_loss} = P_{remaining} - P_{exhaust} $$

## ENE-03: Energy Closure
Strict closure is enforced:
$$ P_{fuel} = P_{unreleased} + P_{indicated} + P_{exhaust} + P_{heat\_loss} $$

## COMB-01: Wiebe Burn Fraction
$$ x_b(\theta) = 1 - \exp \left[ -a \left( \frac{\theta - \theta_0}{\Delta \theta} \right)^{m+1} \right] $$
Evaluated strictly for $\theta \ge \theta_0$, else $x_b = 0$.

## EXH-01: Exhaust Mass Flow (Conservation)
$$ \dot{m}_{exhaust} = \dot{m}_{air} + \dot{m}_{fuel} $$

## EXH-02: Exhaust Temperature (Sensible Energy)
$$ T_{exhaust} = T_{charge} + \frac{P_{exhaust}}{\dot{m}_{exhaust} \cdot C_{P,exh}} $$

## EXH-03: Exhaust Pressure (Restriction)
$$ \Delta P_{exhaust} = K_{exhaust} \cdot \dot{m}_{exhaust}^2 $$
$$ P_{exhaust} = P_{ambient} + \Delta P_{exhaust} $$
