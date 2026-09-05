"""
Phase 1 Telemetry Parameter Registry & Causal Metadata Validation Tests.
SIH26054 — Module 02 Engine Simulator.
"""

import pytest
from src.module02.core.parameter_registry import ParameterRegistry, RegistryError


def test_parameter_registry_completeness():
    """Verify that ParameterRegistry contains all required parameters with zero orphans."""
    registry = ParameterRegistry()
    params = registry.list_all_parameters()

    # Minimum 42 required parameters
    assert len(params) >= 42

    # Verify key required parameters exist
    required_ids = [
        "altitude", "ambient_temperature", "ambient_pressure", "air_density",
        "relative_humidity", "wind_speed", "airspeed", "vertical_speed",
        "aircraft_mass", "throttle", "manifold_pressure", "engine_rpm",
        "injection_timing", "air_mass_flow", "fuel_flow", "air_fuel_ratio",
        "combustion_efficiency", "indicated_torque", "propeller_load_torque",
        "friction_torque", "cht_cyl1", "cht_cyl2", "cht_cyl3", "cht_cyl4",
        "egt_cyl1", "egt_cyl2", "egt_cyl3", "egt_cyl4", "cooling_airflow",
        "oil_temperature", "oil_viscosity", "oil_pressure", "vibration_rms",
        "alternator_current", "alternator_load_torque", "battery_soc",
        "battery_voltage", "brake_thermal_efficiency", "bearing_wear",
        "injector_wear", "ring_wear"
    ]

    for req_id in required_ids:
        param_def = registry.get_parameter(req_id)
        assert param_def is not None
        assert param_def.parameter_id == req_id
        assert param_def.canonical_unit is not None
        assert param_def.display_unit is not None


def test_parameter_registry_integrity():
    """Verify registry integrity validation (canonical units, zero orphans, valid causal metadata)."""
    registry = ParameterRegistry()
    assert registry.validate_registry_integrity() is True


def test_parameter_registry_reject_duplicate():
    """Verify rejection of duplicate parameter registration."""
    registry = ParameterRegistry()
    first_param = registry.get_parameter("altitude")

    with pytest.raises(RegistryError):
        registry.register(first_param)
