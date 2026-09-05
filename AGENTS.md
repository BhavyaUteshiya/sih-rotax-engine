# Project rules

- `src/digital_twin` is the sole authoritative implementation.
- Current scope is only Phase 0 and Phase 1A–1G physics. Do not add telemetry, diagnostics, ML, RUL, dashboards, or maintenance features.
- Use SI units in code and state units in names/docstrings.
- Preserve the provenance of every engineering value. Never label an estimate or calibration value as an official specification.
- Keep `old_project/` reference-only; active code must never import it.
- Read `docs/phase_0/phase_0_foundation.md` and `docs/decisions/engineering_decisions.md` before changing model boundaries.
