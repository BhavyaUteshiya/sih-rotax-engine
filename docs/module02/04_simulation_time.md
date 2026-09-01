# Module 02 — 04. Deterministic Simulation Time & Clock

## 1. Simulation Clock Design
The simulation clock (`SimulationClock`) provides deterministic fixed-step ($dt=0.01\text{ s}$) or configurable-step time integration.

## 2. Wall-Clock Independence
Physics progression depends ONLY on the step count and integration timestep $dt$. Host CPU execution speed or system clock fluctuations have ZERO effect on physics state evolution.

```python
clock = SimulationClock(dt_seconds=0.01, start_time_utc=1787733200.0)
clock.step() # Advances simulation_time_sec by exactly 0.01s
```
