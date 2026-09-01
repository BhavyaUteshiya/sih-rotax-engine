"""
Phase 1.1 Hardening Regression Test Suite.
SIH26054 — Module 02 Engine Simulator.
"""

import os
import pytest
import yaml
from src.module02.config.config_loader import ConfigLoader, ConfigurationError
from src.module02.core.parameter_registry import ParameterRegistry
from src.module02.models.enums import ParameterStatus, ProvenanceClassification
from src.module02.models.states import FlightState, GearboxState, TurbochargerState


def test_1_displacement_unit_correctness(tmp_path):
    """1. Verify displacement unit correctness (rejecting density units KG_PER_M3)."""
    bad_cfg = {
        "metadata": {"profile_id": "BAD_DISPLACEMENT_UNIT"},
        "general": {
            "cylinder_count": 4,
            "engine_type": {"value": "DIESEL", "classification": "REPORTED", "source": "DEFENSE_SPECS", "confidence": "HIGH", "calibration_required": False}
        },
        "geometry_and_inertia": {
            "displacement_m3": {
                "value": 0.0020,
                "unit": "KG_PER_M3",  # Invalid: Density unit instead of volume
                "classification": "ESTIMATED",
                "source": "ENGINEERING_ESTIMATE",
                "confidence": "LOW",
                "calibration_required": True
            }
        }
    }
    file_path = tmp_path / "bad_displacement_unit.yaml"
    with open(file_path, "w") as f:
        yaml.dump(bad_cfg, f)

    with pytest.raises(ConfigurationError):
        ConfigLoader.load_engine_config(str(file_path))


def test_2_no_official_parameter_without_valid_source(tmp_path):
    """2. Verify no OFFICIAL parameter without an authoritative public source."""
    bad_cfg = {
        "metadata": {"profile_id": "BAD_OFFICIAL_SOURCE"},
        "general": {
            "cylinder_count": 4,
            "fuel_type": {
                "value": "DIESEL",
                "classification": "OFFICIAL",
                "source": "ENGINEERING_ESTIMATE",  # Invalid: OFFICIAL cannot use ENGINEERING_ESTIMATE
                "confidence": "LOW",
                "calibration_required": True
            }
        }
    }
    file_path = tmp_path / "bad_official_source.yaml"
    with open(file_path, "w") as f:
        yaml.dump(bad_cfg, f)

    with pytest.raises(ConfigurationError):
        ConfigLoader.load_engine_config(str(file_path))


def test_3_manifold_absolute_pressure_vs_gauge_boost_naming():
    """3. Verify manifold absolute pressure (MAP) vs gauge boost pressure calculation."""
    turbo = TurbochargerState(max_manifold_absolute_pressure_pa=220000.0) # 2.2 bar MAP
    p_ambient = 101325.0                                                    # 1.013 bar ambient

    p_gauge = turbo.get_gauge_boost_pressure_pa(p_ambient)
    assert p_gauge == pytest.approx(118675.0)                               # ~1.18 bar gauge boost


def test_4_gearbox_speed_ratio_equation():
    """4. Verify gearbox speed-ratio equation N_prop = N_engine * speed_ratio and reduction ratio reciprocal."""
    gb = GearboxState(engine_to_propeller_speed_ratio=0.65)
    engine_rpm = 4200.0

    prop_rpm = gb.compute_propeller_rpm(engine_rpm)
    assert prop_rpm == pytest.approx(2730.0)                                 # 4200 * 0.65 = 2730 RPM
    assert gb.reduction_ratio == pytest.approx(1.5384615, rel=1e-5)          # 1 / 0.65


def test_5_tapas_selected_engine_profile_identity():
    """5. Verify TAPAS selected engine profile identity."""
    cfg = ConfigLoader.load_engine_config("configs/module02/engines/tapas_bh201_180hp_uav_diesel.yaml")
    assert cfg["metadata"]["profile_id"] == "TAPAS_BH201_INDIGENOUS_180HP_DIESEL"
    assert "indigenous propulsion reference" in cfg["metadata"]["identity_note"]


def test_6_target_vs_demonstrated_metrics_remain_separate():
    """6. Verify target and demonstrated performance metrics remain explicitly separate."""
    cfg = ConfigLoader.load_aircraft_config("configs/module02/aircraft/tapas_bh201.yaml")
    reqs = cfg["performance_requirements"]

    assert reqs["target_operating_altitude_m"]["value"] == 9144.0          # 30,000 ft
    assert reqs["demonstrated_altitude_m"]["value"] == 8534.4            # 28,000 ft
    assert reqs["target_operating_altitude_m"]["value"] != reqs["demonstrated_altitude_m"]["value"]

    assert reqs["target_endurance_hours"]["value"] == 24.0
    assert reqs["demonstrated_endurance_hours"]["value"] == 18.0
    assert reqs["target_endurance_hours"]["value"] != reqs["demonstrated_endurance_hours"]["value"]


def test_7_current_mass_derived_from_component_masses():
    """7. Verify current mass is derived dynamically from component masses m_dry + m_payload + m_fuel."""
    flight = FlightState(
        dry_mass_kg=1800.0,
        payload_mass_kg=350.0,
        fuel_mass_remaining_kg=650.0
    )
    assert flight.current_mass_kg == pytest.approx(2800.0)

    # Burn 100 kg fuel
    flight.fuel_mass_remaining_kg -= 100.0
    assert flight.current_mass_kg == pytest.approx(2700.0)


def test_8_every_registry_parameter_has_implementation_status():
    """8. Verify every parameter definition in ParameterRegistry declares an explicit ParameterStatus."""
    registry = ParameterRegistry()
    params = registry.list_all_parameters()

    valid_statuses = [s.value for s in ParameterStatus]

    for param in params:
        assert param.status is not None
        assert param.status.value in valid_statuses
