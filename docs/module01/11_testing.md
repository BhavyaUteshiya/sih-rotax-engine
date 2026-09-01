# Module 01 — Testing Strategy & Test Suite

## Test Hierarchy
- **Architecture Invariant Tests** (`tests/architecture/test_invariants.py`): Verifies raw payload immutability, SHA-256 content hashing vs `packet_id`, synthetic provenance, simulation injection rejection, CSV/JSON file sources, clock mapping drift formulas, synchronizer `is_sync_eligible` filtering, out-of-order `SOURCE_EVENT_ORDER` sorting, duplicate/retransmission/conflict detection, lineage resolution, and non-UTC `TimeRange` domain rejection.
- **Integration Tests** (`tests/integration/test_pipeline.py`): End-to-end pipeline execution from mock CAN and ECU stream ingestion through frame publication.
- **Unit Tests** (`tests/unit/`): Target tests for models, protocol decoders, and unit normalizers.

## Executing Test Suite
```bash
$ PYTHONPATH=. ./venv/bin/pytest -v
```
