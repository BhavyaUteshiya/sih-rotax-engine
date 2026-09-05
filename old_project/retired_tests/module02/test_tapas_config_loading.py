"""
TAPAS-BH-201 Configuration Loading & Provenance Validation Tests.
SIH26054 — Module 02 Engine Simulator.
"""

import pytest
from src.module02.config.config_loader import ConfigLoader, ConfigurationError
from src.module02.models.enums import ProvenanceClassification


def test_load_tapas_engine_config():
    """Verify loading TAPAS-BH-201 engine configuration with valid provenance metadata."""
    cfg = ConfigLoader.load_engine_config("configs/module02/engines/tapas_bh201_180hp_uav_diesel.yaml")
    assert isinstance(cfg, dict)
    assert cfg["metadata"]["profile_id"] == "TAPAS_BH201_INDIGENOUS_180HP_DIESEL"

    # Official parameters
    power_entry = cfg["power_and_performance"]["takeoff_rated_power_hp"]
    assert power_entry["value"] == 180.0
    assert power_entry["classification"] == "OFFICIAL"
    assert power_entry["source"] == "DRDO_PUBLIC_RELEASE"
    assert power_entry["confidence"] == "HIGH"
    assert power_entry["calibration_required"] is False

    # Estimated parameter
    disp_entry = cfg["geometry_and_inertia"]["displacement_m3"]
    assert disp_entry["value"] == 0.0020
    assert disp_entry["unit"] == "METER3"
    assert disp_entry["classification"] == "ESTIMATED"
    assert disp_entry["calibration_required"] is True


def test_load_tapas_aircraft_config():
    """Verify loading TAPAS-BH-201 aircraft configuration with twin-engine architecture."""
    cfg = ConfigLoader.load_aircraft_config("configs/module02/aircraft/tapas_bh201.yaml")
    assert isinstance(cfg, dict)
    assert cfg["architecture"]["engine_count"]["value"] == 2

    # Separate target vs demonstrated performance
    reqs = cfg["performance_requirements"]
    assert reqs["target_operating_altitude_m"]["value"] == 9144.0          # 30,000 ft
    assert reqs["demonstrated_altitude_m"]["value"] == 8534.4            # 28,000 ft
    assert reqs["target_endurance_hours"]["value"] == 24.0
    assert reqs["demonstrated_endurance_hours"]["value"] == 18.0


def test_load_tapas_propeller_config():
    """Verify loading TAPAS-BH-201 gearbox & propeller configuration."""
    cfg = ConfigLoader.load_propeller_config("configs/module02/propellers/tapas_bh201_reference_propeller.yaml")
    assert isinstance(cfg, dict)
    assert cfg["gearbox"]["engine_to_propeller_speed_ratio"]["value"] == 0.65
    assert cfg["gearbox"]["gearbox_efficiency"]["value"] == 0.97
    assert cfg["propeller"]["num_blades"]["value"] == 3


def test_reject_official_classification_without_source(tmp_path):
    """Verify rejection if a parameter is marked OFFICIAL without an authoritative source."""
    bad_engine = {
        "metadata": {"profile_id": "BAD_PROVENANCE"},
        "general": {
            "cylinder_count": 4,
            "engine_type": {
                "value": "DIESEL",
                "classification": "OFFICIAL",
                "source": "ASSUMPTION"  # Contradiction: OFFICIAL cannot have source ASSUMPTION
            }
        }
    }
    file_path = tmp_path / "bad_provenance_engine.yaml"
    import yaml
    with open(file_path, "w") as f:
        yaml.dump(bad_engine, f)

    with pytest.raises(ConfigurationError):
        ConfigLoader.load_engine_config(str(file_path))
