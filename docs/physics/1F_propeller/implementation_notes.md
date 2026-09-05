# Phase 1F: Implementation Notes

## Architecture
Phase 1F completes the physical foundation stack (Phases 1A through 1F). 
It owns all aerodynamic propeller physics. 
It does **not** own the engine torque balance, the gearbox, or the aircraft mission state.

## Equivalent Inertia and Drivetrain Coupling
During Phase 1F implementation, the issue of "Equivalent Inertia" from Phase 1E was clarified.
The full inertia of the rotating system must account for both the engine and the propeller, connected via the gearbox ratio ($r_g$).

The effective equivalent inertia ($J_{eq}$) seen at the engine shaft is theoretically:
$$J_{eq} = J_{engine} + \frac{J_{prop}}{r_g^2}$$

In Phase 1E, a generic $J_{engine} = 0.05$ kg m² was used to guarantee stability. 
This document explicitly records that the true coupled inertia should be applied during the final **Phase 1 System Integration**, replacing the standalone $J_{engine}$ parameter in the `EngineDynamicsModel`.

Phase 1F intentionally does not inject this into Phase 1E right now, strictly adhering to the architectural separation rule.

## Deferred Items Carried Forward

1. **1D Carburetor Terminology Cleanup Status:** Fixed (Handled organically during Phase 1E).
2. **1D Registry/Reference Consistency Status:** Fixed in Phase 1F.
3. **1D Stronger Rated-Condition Fuel Validation Status:** Fixed in Phase 1F (Tightened bounds in `test_combustion.py`).
4. **1E Placeholder Regression Test Status:** Fixed in Phase 1F (Formalized the placeholders to defer exactly to Phase 1 System Integration).
5. **1E Equivalent-Inertia Documentation/Implementation Reconciliation Status:** Fixed in Phase 1F (Documented the exact $J_{eq}$ coupling formula in this document, explicitly deferring the injection into 1E until System Integration).
