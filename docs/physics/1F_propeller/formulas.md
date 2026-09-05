# Phase 1F: Propeller Formulas

This document registers the formulas used to calculate the physical state of the propeller.

## PROP-01: Advance Ratio
Calculates the advance ratio of the propeller, which is a key non-dimensional parameter that dictates its aerodynamic operating point.
- **Equation**: $J = \frac{V}{n \cdot D}$
- **Variables**: $V$ (airspeed, m/s), $n$ (propeller speed, rev/s), $D$ (diameter, m).
- **Assumptions**: Bypassed if $n$ is effectively 0.

## PROP-02: Thrust Coefficient Surrogate
Estimates the thrust coefficient using a linear decay model representing a generic fixed-pitch propeller.
- **Equation**: $C_T = \max(C_{T,min}, C_{T,static} + C_{T,slope} \cdot J)$
- **Assumptions**: Simple surrogate since a proprietary map is unavailable. Does not model reverse thrust.

## PROP-03: Torque Coefficient Surrogate
Estimates the torque coefficient using a linear decay model.
- **Equation**: $C_Q = \max(C_{Q,min}, C_{Q,static} + C_{Q,slope} \cdot J)$
- **Assumptions**: Consistent with the stand-in model used temporarily in Phase 1E. 

## PROP-04: Propeller Thrust
Calculates the aerodynamic thrust produced by the propeller.
- **Equation**: $T = C_T \cdot \rho \cdot n^2 \cdot D^4$
- **Variables**: $\rho$ (air density, kg/m³).

## PROP-05: Propeller Torque
Calculates the aerodynamic drag torque absorbed by the propeller.
- **Equation**: $Q = C_Q \cdot \rho \cdot n^2 \cdot D^5$
- **Variables**: This is the torque magnitude that opposes engine rotation.

## PROP-06: Absorbed Power
Calculates the power absorbed by the propeller (shaft power demanded).
- **Equation**: $P = 2\pi n Q$
- **Assumptions**: Strict physical consistency with aerodynamic torque.

## PROP-07: Propeller Efficiency
Calculates the propulsive efficiency.
- **Equation**: $\eta = \frac{T \cdot V}{P}$
- **Assumptions**: Capped between 0 and 1. Defined as 0 when $V=0$ or $P=0$.
