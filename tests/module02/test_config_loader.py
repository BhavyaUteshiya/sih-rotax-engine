"""
Phase 1 Configuration Loader Validation Tests.
SIH26054 — Module 02 Engine Simulator.
"""

import os
import pytest
import yaml
from src.module02.config.config_loader import ConfigLoader, ConfigurationError


def test_load_valid_simulation_config():
    """Verify loading valid simulation_config.yaml."""
    cfg = ConfigLoader.load_simulation_config("configs/module02/simulation_config.yaml")
    assert isinstance(cfg, dict)
    assert cfg["time"]["default_dt_seconds"] == 0.01
    assert cfg["randomness"]["default_seed"] == 42
    assert cfg["metadata"]["model_version"] == "1.3.0"


def test_load_valid_engine_config():
    """Verify loading valid engine configuration."""
    cfg = ConfigLoader.load_engine_config("configs/module02/engines/tapas_bh201_180hp_uav_diesel.yaml")
    assert isinstance(cfg, dict)
    assert cfg["general"]["cylinder_count"]["value"] == 4
    assert cfg["power_and_performance"]["takeoff_rated_power_hp"]["value"] == 180.0


def test_reject_non_existent_config_file():
    """Verify error when config file does not exist."""
    with pytest.raises(ConfigurationError):
        ConfigLoader.load_simulation_config("configs/module02/non_existent.yaml")


def test_reject_invalid_cylinder_count(tmp_path):
    """Verify rejection of non-4 cylinder engine parameters."""
    bad_cfg = {
        "metadata": {"profile_id": "BAD_CYLINDERS"},
        "general": {
            "cylinder_count": {
                "value": 6,  # Invalid: Module 02 requires 4
                "unit": "COUNT",
                "classification": "ESTIMATED",
                "source": "ENGINEERING_ESTIMATE",
                "confidence": "LOW",
                "calibration_required": True
            }
        }
    }
    file_path = os.path.join(tmp_path, "bad_engine.yaml")
    with open(file_path, "w") as f:
        yaml.dump(bad_cfg, f)

    with pytest.raises(ConfigurationError):
        ConfigLoader.load_engine_config(file_path)


def test_reject_negative_timestep(tmp_path):
    """Verify rejection of negative or zero timestep in simulation config."""
    bad_cfg = {
        "time": {
            "default_dt_seconds": -0.05,  # Invalid
        },
        "randomness": {
            "default_seed": 42,
        }
    }
    file_path = os.path.join(tmp_path, "bad_sim.yaml")
    with open(file_path, "w") as f:
        yaml.dump(bad_cfg, f)

    with pytest.raises(ConfigurationError):
        ConfigLoader.load_simulation_config(file_path)
