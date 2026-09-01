"""
Verification & Regression Test Suite for Active Engine Selection (Rotax 914).
SIH26054 — Module 02 Engine Simulator.
"""

import pytest
from src.module02.config.config_loader import ConfigLoader
from src.module02.simulation.thermodynamic_engine_runner import ThermodynamicEngineRunner
from src.module02.integration.integration_runner import MasterIntegrationRunner
from src.module02.integration.can_transport import InMemoryTransport


def test_default_config_loader_is_rotax_914():
    """Verify that ConfigLoader.load_engine_config() defaults to rotax_914.yaml."""
    cfg = ConfigLoader.load_engine_config()
    assert isinstance(cfg, dict)
    assert cfg["metadata"]["profile_id"] == "ROTAX_914_UL_115HP"
    assert "ROTAX" in cfg["metadata"]["engine_name"].upper()
    assert cfg["geometry_and_inertia"]["displacement_m3"]["value"] == 0.0012112
    assert cfg["power_and_performance"]["takeoff_rated_power_hp"]["value"] == 115.0


def test_thermodynamic_engine_runner_default_is_rotax_914():
    """Verify ThermodynamicEngineRunner uses Rotax 914 configuration."""
    runner = ThermodynamicEngineRunner()
    profile_id = runner.engine_config["metadata"]["profile_id"]
    assert profile_id == "ROTAX_914_UL_115HP"
    assert runner.max_indicated_torque == 165.0
    assert runner.takeoff_duration_s == 300.0


def test_master_integration_runner_default_is_rotax_914():
    """Verify MasterIntegrationRunner uses Rotax 914 configuration."""
    runner = MasterIntegrationRunner(transport_override=InMemoryTransport())
    profile_id = runner.simulator.engine_config["metadata"]["profile_id"]
    assert profile_id == "ROTAX_914_UL_115HP"


def test_aircraft_configuration_points_to_rotax_914():
    """Verify aircraft airframe configuration points to rotax_914.yaml as its engine."""
    ac_cfg = ConfigLoader.load_aircraft_config("configs/module02/aircraft/tapas_bh201.yaml")
    engine_cfg_path = ac_cfg["architecture"]["engine_configuration_file"]
    assert engine_cfg_path == "configs/module02/engines/rotax_914.yaml"

    # Ensure loading the referenced engine file yields Rotax 914
    ref_eng = ConfigLoader.load_engine_config(engine_cfg_path)
    assert ref_eng["metadata"]["profile_id"] == "ROTAX_914_UL_115HP"


def test_regression_active_engine_is_not_tapas_diesel():
    """Regression test: fail if active runtime engine is TAPAS diesel engine."""
    default_cfg = ConfigLoader.load_engine_config()
    active_profile_id = default_cfg["metadata"]["profile_id"]
    assert active_profile_id != "TAPAS_BH201_INDIGENOUS_180HP_DIESEL", "CRITICAL ERROR: Active engine defaulted to TAPAS diesel profile!"

    runner = ThermodynamicEngineRunner()
    runner_profile = runner.engine_config["metadata"]["profile_id"]
    assert runner_profile != "TAPAS_BH201_INDIGENOUS_180HP_DIESEL", "CRITICAL ERROR: ThermodynamicEngineRunner initialized with TAPAS diesel profile!"
