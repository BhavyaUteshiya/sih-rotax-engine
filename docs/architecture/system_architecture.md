# Active system architecture

`src/digital_twin` is the only runtime implementation. The `DigitalTwinSimulator` executes a single-engine, explicit-time-step causal chain:

`atmosphere → turbo/intake → airflow → combustion → propeller load → engine dynamics → thermal`.

The turbo uses exhaust state from the prior combustion step, avoiding an algebraic loop. Each model has typed input/output dataclasses and owns its output state. Simulation inputs provide operating conditions and prototype calibration boundaries. No active package imports `old_project`.

The active package deliberately excludes acquisition, CAN transport, persistence, dashboards, expected-vs-observed comparison, residual analysis, diagnosis, and ML. Those are future architecture concepts, not implemented capabilities.
