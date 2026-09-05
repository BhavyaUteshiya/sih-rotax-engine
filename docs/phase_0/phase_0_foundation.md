# Phase 0: project foundation

## Purpose and scope

This SIH project establishes a trustworthy physics foundation for a future MALE-UAV aero-engine digital twin, using the Rotax 914 UL/F context. Active scope is Phase 0 governance and Phase 1A–1G reduced-order physics only.

## Authority and provenance

Authority is ranked: (1) official Rotax/EASA material, (2) established engineering physics, (3) published engineering research, (4) validated engineering assumptions, then (5) calibration, estimated, or synthetic values. Values carry their classification in code comments, configuration records, and the reference registry. A plausible value is never silently promoted to an official specification.

## Engineering rules

- SI units and physically meaningful names are mandatory.
- A model has one owner for each output quantity.
- Keep interfaces minimal; no unused environmental inputs in rotational dynamics.
- Use explicit reduced-order assumptions rather than unverified fidelity claims.
- Tests check numerical safety, causal integration, and model-level behaviour; validation is model sanity, not certification.

## Documentation and archive

The active record is the architecture, Phase 1, theory, validation, references, and decisions documents. `old_project/` is a non-importable historical archive. It retains selected legacy evidence but cannot define active behaviour.

## Completion criteria

Phase 0 is complete when the repository has one active physics stack, no active future-phase runtime, traceable core formulas, declared limitations, a focused test suite, and passing relevant tests.
