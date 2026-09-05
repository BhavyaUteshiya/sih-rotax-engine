# Phase 1E: Engine Dynamics & Torque Balance — Validation

## Overview
The Phase 1E Engine Dynamics module replaces static RPM prescribing with emergent rotational dynamics. The validation suite ensures that the numerical integration is stable, robust against edge cases (like zero RPM), and physically consistent with the rated output of the Rotax 914 engine.

## Test Suite
The automated test suite (`scratch/test_engine_dynamics.py`) contains 30 discrete tests verifying isolated behavior and integration across Phases 1A–1E.

### Key Validation Criteria

1.  **Zero-RPM Stability (Tests 08-11):** 
    Numerical models often crash when angular velocity is exactly zero due to the $\tau = P / \omega$ singularity. The tests verify that:
    *   Friction clamps properly without driving the engine in reverse.
    *   Starting torque safely initiates rotation without mathematical infinities (NaN/Inf).
    *   Indicated torque defaults to zero below a safe threshold until the starter spins the engine up.

2.  **Rated Power Consistency (Test 25):** 
    At 5800 RPM (607.37 rad/s), the nominal Rotax 914 produces 115 HP (85.8 kW). The validation checks that if $85.8 \text{ kW}$ of *indicated power* is produced, the resultant *shaft power* (indicated minus friction) aligns physically with a reasonable mechanical loss profile (e.g., ~$10\text{-}20 \text{ kW}$ of friction).

3.  **Dynamic Balance (Tests 03-05):** 
    *   Positive Net Torque → RPM increases.
    *   Negative Net Torque → RPM decreases.
    *   Zero Net Torque → RPM holds steady.

4.  **Gearbox & Propeller Coupling (Tests 17-24):** 
    The module verifies correct power transmission across the reduction gearbox (Ratio = 2.4286). It checks that the aero-dynamic load imposed by the propeller increases appropriately with air density (Phase 1A link) and engine speed.

5.  **Full Chain Integration (Test 30):** 
    A unified smoke test initializing Phases 1A, 1B, 1C, 1D, and 1E sequentially. It confirms that atmospheric state maps successfully to manifold pressure, which dictates airflow, which dictates combustion power, which finally produces positive angular acceleration on the shaft.
