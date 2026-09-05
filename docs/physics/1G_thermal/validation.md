# Phase 1G: Engine Thermal Physics - Validation

The Phase 1G thermal model is validated against an extensive suite of expected physical behaviors and boundary conditions, implemented in `scratch/test_thermal.py`.

## Tested Scenarios

1. **Cold Start:** Confirms temperatures naturally rise from ambient when heat is applied.
2. **Thermal Lag:** Confirms that direct heat enters the CHT first, and the oil temperature follows with a realistic thermal lag due to the `R_CHT_OIL` resistance and thermal capacities.
3. **Engine Shutdown (Heat removed):** Confirms temperatures naturally converge back to ambient due to residual cooling (`G_MIN`).
4. **Airspeed and Density Sensitivity:** Confirms that higher airspeeds and higher air densities increase convective cooling, lowering steady-state temperatures.
5. **Altitude Sensitivity:** Confirms that lower atmospheric density (e.g., at altitude) reduces the effectiveness of forced convective cooling.
6. **Hot/Cold Ambient Conditions:** Confirms that steady-state engine temperatures scale appropriately with ISA deviations (e.g., ISA+20).
7. **High Power Steady-State (Test 27):** Confirms that under 76.9 kW of residual combustion heat loss (from Phase 1D) at a 40 m/s cruise, the temperatures stabilize within realistic engine limits:
   - CHT stabilizes between 80 °C and 140 °C.
   - Oil stabilizes between 60 °C and 130 °C.

## Numerical Stability
- Explicit Euler integration steps are protected against zero or negative timesteps.
- Hard limits prevent non-physical negative Kelvin temperatures.
- Division by zero is protected against in the convective cooling term.
- `NaN` and `Infinity` outputs are strictly tested against.

## Cross-Phase Integration
- Validated to natively accept the `heat_loss_power_w` output from the Phase 1D combustion model without re-evaluating or double-counting chemical energy.
