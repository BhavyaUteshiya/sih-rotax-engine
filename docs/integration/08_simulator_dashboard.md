# SIH26054 Simulator Control Dashboard

The pre-Digital-Twin control station is implemented in `app/` and runs on the existing physics simulator plus Simulator -> CAN -> Digital Twin integration path.

## Start

```bash
PYTHONPATH=. python scripts/run_dashboard.py
```

Open `http://127.0.0.1:8000`.

## Controls

Operator controls are intentionally limited to external/environmental inputs:
- Engine 1 / Engine 2 throttle
- Scenario altitude
- Ambient temperature offset
- Relative humidity
- Flight path angle
- Engine starter commands

The dashboard does **not** expose EGT, CHT, AFR, oil pressure, vibration, wear, MAP, or other internally generated engine states as manual controls.

## Data path

`Dashboard controls -> ThermodynamicEngineRunner -> 100 Hz physics -> 50 Hz telemetry -> CAN transport -> Digital Twin bridge -> normalized telemetry -> dataset export`.

The Digital Twin Physics remains authoritative. The dashboard is a frontend/control layer and does not bypass the ingestion contract.
