# Rotax 914 UL/F Physics Foundation

This repository is the Phase 0/Phase 1 foundation for an SIH project: an AI-enabled digital-twin system intended to improve health monitoring, fault prediction, and mission reliability of aero piston engines in MALE UAVs.

The active work is deliberately narrower than the overall SIH vision. It is a deterministic, reduced-order, physics-based simulator for the **Rotax 914 UL/F** engine context. It models atmosphere, turbo/intake, airflow, fuel/combustion, rotational dynamics, propeller loading, and thermal response. It is not a telemetry system, dashboard, diagnostic system, ML model, RUL estimator, or maintenance tool.

## Status

Phase 0 is complete: one authoritative code path, a documented authority hierarchy, archived legacy material, and a focused test suite. Phase 1A–1G is implemented as a prototype physics foundation. Its calibration values must not be treated as certified Rotax limits.

## Layout

```
src/digital_twin/        authoritative Phase 1 simulator
configs/engine/          engine-facing parameter records
configs/simulation/      scenario/calibration settings
tests/unit/              model-level tests
tests/integration/       simulator integration test
docs/                    active engineering record
old_project/             reference-only retired material
```

## Run

Requires Python 3.11+ and `pytest`.

```powershell
python -m pytest tests
python -c "from src.digital_twin.simulation.simulator import DigitalTwinSimulator; from src.digital_twin.simulation.state import SimulationInput; print(DigitalTwinSimulator().step(SimulationInput(starter_engaged=True, throttle_position=0.4)))"
```

See [Phase 0 foundation](docs/phase_0/phase_0_foundation.md), [Phase 1 physics](docs/phase_1/phase_1_engine_physics.md), and [limitations](docs/validation/phase_1_validation.md).
