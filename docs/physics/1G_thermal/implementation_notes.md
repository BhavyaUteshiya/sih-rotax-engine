# Phase 1G: Engine Thermal Physics - Implementation Notes

## Architecture Decisions
- **Two-Node Model:** We chose a two-node model (CHT and Oil) because it perfectly matches the available telemetry on typical Rotax 914 UAV installations. Adding a third node (e.g., coolant) was deemed unnecessary complexity for an engine where CHT and Oil Temp are the primary health indicators.
- **Energy Ownership:** The most critical architectural decision was ensuring Phase 1G does NOT calculate combustion energy. It natively accepts `heat_loss_power_w` from Phase 1D. This guarantees the first law of thermodynamics is strictly conserved across the digital twin.
- **Cooling Surrogate:** A full CFD simulation is impossible for real-time edge AI. Therefore, convective cooling is modeled as a surrogate dependent on $\rho$ and $V$. This ensures realistic behavior (hotter at altitude, hotter at low airspeeds) while remaining computationally trivial ($O(1)$).

## Limitations
- **No Spatial Resolution:** This model provides a single bulk CHT and a single bulk Oil temperature. It cannot predict localized hot-spots (e.g., exhaust valve seats or specific cylinder imbalances).
- **Static Thermal Capacities:** Specific heats of oil and metal change slightly with temperature. We assume them to be constant for this reduced-order model.
- **Simplified Heat Partition:** We assume a static fraction (`F_CHT = 0.35`) of the 1D heat loss enters the thermal network. In reality, this fraction varies slightly with engine load and RPM, but a static value provides a robust first-order approximation.

## Deferred Items
- **Diagnostic Residuals:** Generating health-monitoring residuals (comparing expected temperatures to actual noisy sensor telemetry) is deferred to a future phase.
- **Full Engine Integration:** The final orchestrator loop connecting Phase 1A-1G together in real-time is deferred to the Phase 1 System Integration phase.
