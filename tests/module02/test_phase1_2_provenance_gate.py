"""
Phase 1.2 Final Provenance Gate Audit Test Suite.
SIH26054 — Module 02 Engine Simulator.
"""

import os
import pytest
import yaml
from src.module02.config.config_loader import ConfigLoader
from src.module02.models.enums import ProvenanceClassification


def _recursive_provenance_audit(data: dict, current_path: str = "") -> None:
    """
    Recursively scans configuration dictionary and validates provenance rules:
    - Every parameter dictionary MUST have a classification.
    - OFFICIAL parameters MUST have authoritative source DRDO_PUBLIC_RELEASE.
    - ESTIMATED parameters MUST have calibration_required = True.
    - DERIVED parameters MUST have valid derivation source.
    """
    if isinstance(data, dict):
        if "value" in data:
            classification = data.get("classification")
            source = data.get("source")
            calib_req = data.get("calibration_required")

            assert classification is not None, f"Unclassified parameter found at {current_path}"
            assert classification in ProvenanceClassification.__members__, f"Invalid classification '{classification}' at {current_path}"

            if classification == "OFFICIAL":
                assert source == "DRDO_PUBLIC_RELEASE", (
                    f"Parameter at {current_path} classified OFFICIAL but source is '{source}' (must be DRDO_PUBLIC_RELEASE)."
                )

            elif classification == "ESTIMATED":
                assert calib_req is True, (
                    f"Parameter at {current_path} classified ESTIMATED but calibration_required is False."
                )

            elif classification == "DERIVED":
                assert source in ["UNIT_CONVERSION", "MATHEMATICAL_RECIPROCAL", "FORMULA_DERIVATION"], (
                    f"Parameter at {current_path} classified DERIVED but source is '{source}'."
                )

        for k, v in data.items():
            new_path = f"{current_path}.{k}" if current_path else k
            _recursive_provenance_audit(v, new_path)


def test_tapas_engine_provenance_gate():
    """Audit TAPAS engine configuration file for provenance compliance."""
    cfg = ConfigLoader.load_engine_config("configs/module02/engines/tapas_bh201_180hp_uav_diesel.yaml")
    _recursive_provenance_audit(cfg)


def test_tapas_aircraft_provenance_gate():
    """Audit TAPAS aircraft configuration file for provenance compliance."""
    cfg = ConfigLoader.load_aircraft_config("configs/module02/aircraft/tapas_bh201.yaml")
    _recursive_provenance_audit(cfg)


def test_tapas_propeller_provenance_gate():
    """Audit TAPAS propeller configuration file for provenance compliance."""
    cfg = ConfigLoader.load_propeller_config("configs/module02/propellers/tapas_bh201_reference_propeller.yaml")
    _recursive_provenance_audit(cfg)


def test_target_vs_demonstrated_altitude_and_endurance_separation():
    """Verify target and demonstrated performance metrics remain strictly separate."""
    cfg = ConfigLoader.load_aircraft_config("configs/module02/aircraft/tapas_bh201.yaml")
    reqs = cfg["performance_requirements"]

    target_alt = reqs["target_operating_altitude_m"]["value"]
    dem_alt = reqs["demonstrated_altitude_m"]["value"]
    target_end = reqs["target_endurance_hours"]["value"]
    dem_end = reqs["demonstrated_endurance_hours"]["value"]

    assert target_alt == 9144.0          # 30,000 ft
    assert dem_alt == 8534.4            # 28,000 ft
    assert target_alt > dem_alt

    assert target_end == 24.0           # 24 h
    assert dem_end == 18.0              # 18 h
    assert target_end > dem_end
