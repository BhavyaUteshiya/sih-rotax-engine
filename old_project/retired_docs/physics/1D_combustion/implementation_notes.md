# Phase 1D: Implementation Notes and Limitations

## Limitations
1. **Not a 1-D Otto Cycle Solver:** This model computes mean cycle properties. Instantaneous cylinder pressure profiles ($P-V$ diagrams) and discrete valve gas exchange dynamics are omitted. The Wiebe burn equation is exposed as a placeholder and peak structural check, but does not drive a high-frequency cylinder volume integration.
2. **Proprietary Maps Unavailable:** The Rotax 914 AFR and precise thermal partition maps are not publicly verifiable. Thus, bounded surrogate functions (Equivalence Ratio, Heat Partition) are applied based on established generic internal combustion engine mechanics.
3. **No Dynamic Carburetor Flooding:** Fuel pressure constraints evaluate the nominal bounds for diagnostic flagging (Phase 5), but we do not model complex fluid-dynamic carburetor flooding/starvation transients.
4. **No Thermal Lag:** Energy partitioning to the exhaust is instantaneous. Detailed thermal inertia (wall heating, cylinder head temperatures) will be introduced in Phase 1G.

## Numerical Protections
- **Zero RPM / Zero Flow:** Explicit guards return zero indicated power and fuel flow when airflow or RPM drop below physical thresholds, preventing NaNs.
- **Exhaust Temperature Spikes:** The sensible temperature rise $P_{exhaust} / (\dot{m} \cdot C_{p})$ contains a mass-flow denominator limit. Below $1\mu\text{g/s}$, it falls back to the charge temperature to avoid an asymptote to infinity. 
- **Wiebe Non-Physical Roots:** Fractional powers of negative numbers can cause numerical crashes in Python (`math.pow`). The argument for the Wiebe shape factor $((\theta - \theta_0)/\Delta\theta)$ is rigorously clamped at $0.0$ to avoid imaginary numbers when evaluating pre-combustion states.
