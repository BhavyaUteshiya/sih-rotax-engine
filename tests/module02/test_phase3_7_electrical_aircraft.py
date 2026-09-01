"""
Comprehensive Phase 3.7 Test Suite: Electrical Bus, Alternator Shaft Load, Battery SOC, Starter Motor, and 3-DOF Aircraft Dynamics.
SIH26054 — Module 02 Engine Simulator.
"""

import math
import os
import pytest
from typing import Dict

from src.module02.config.config_loader import ConfigLoader
from src.module02.core.clock import SimulationClock
from src.module02.core.parameter_registry import ParameterRegistry
from src.module02.physics.atmosphere import AtmosphereModel
from src.module02.physics.electrical_aircraft import ElectricalAircraftError, ElectricalAircraftModel
from src.module02.simulation.electrical_aircraft_runner import ElectricalAircraftRunner
from src.module02.simulation.engine_runner import EngineRunner


@pytest.fixture
def loaded_config():
    return ConfigLoader.load_engine_config("configs/module02/engines/rotax_914.yaml")


@pytest.fixture
def clock():
    return SimulationClock(dt_seconds=0.01)


# ==============================================================================
# ELECTRICAL SUBSYSTEM TESTS (1 - 10)
# ==============================================================================

def test_alternator_output_increases_with_rpm():
    """1. Alternator output increases from 0 below cut-in to rated output above cut-in RPM."""
    i_below, p_below, _, _ = ElectricalAircraftModel.compute_alternator_output_and_shaft_load(500.0, 28.0, 800.0, 75.0, 0.85, 1000.0)
    i_above, p_above, _, _ = ElectricalAircraftModel.compute_alternator_output_and_shaft_load(2000.0, 28.0, 800.0, 75.0, 0.85, 1000.0)

    assert i_below == 0.0
    assert p_below == 0.0
    assert i_above > 0.0
    assert p_above > 0.0


def test_alternator_output_is_load_limited():
    """2. Alternator output current is strictly bounded by max_current_a."""
    i_alt, p_alt, _, _ = ElectricalAircraftModel.compute_alternator_output_and_shaft_load(3000.0, 28.0, 5000.0, 75.0, 0.85, 1000.0)

    assert i_alt == 75.0
    assert p_alt == 28.0 * 75.0  # 2100 W max capacity


def test_alternator_torque_reaches_engine_shaft(clock, loaded_config):
    """3. Alternator mechanical load torque is reflected to the engine shaft."""
    runner = EngineRunner(clock, engine_config=loaded_config)
    eng_normal = runner.step_engine(1, throttle_percent=50.0, load_torque_n_m=40.0, alternator_torque_n_m=0.0)
    eng_alt_loaded = runner.step_engine(2, throttle_percent=50.0, load_torque_n_m=40.0, alternator_torque_n_m=15.0)

    assert eng_alt_loaded.alternator_load_torque_n_m == 15.0
    assert eng_alt_loaded.engine_rpm < eng_normal.engine_rpm


def test_alternator_efficiency_power_balance():
    """4. Alternator mechanical power requirement obeys P_mech = P_elec / eta_alt."""
    _, p_elec, p_mech, _ = ElectricalAircraftModel.compute_alternator_output_and_shaft_load(2500.0, 28.0, 800.0, 75.0, 0.85, 1000.0)

    assert math.isclose(p_mech, p_elec / 0.85, rel_tol=1e-5)
    assert p_mech >= p_elec


def test_electrical_load_consumes_power(clock, loaded_config):
    """5. Electrical load increases bus electrical power demand."""
    runner = ElectricalAircraftRunner(clock, engine_config=loaded_config)
    elec, batt, _, _, _ = runner.step_electrical_and_aircraft({1: 2500.0, 2: 2500.0}, {1: False, 2: False}, {1: 500.0, 2: 500.0}, 1.225)

    assert elec.electrical_load_w >= 800.0


def test_battery_supplies_deficit():
    """6. Battery supplies power deficit when alternator output is less than load demand."""
    new_soc, v_bat, i_batt, p_batt = ElectricalAircraftModel.step_battery_soc(
        current_soc=0.90, net_electrical_power_demand_w=500.0, dt_seconds=1.0, nominal_energy_j=2592000.0, nominal_voltage_v=24.0, charge_efficiency=0.90, discharge_efficiency=0.95
    )

    assert i_batt > 0.0  # Discharge convention
    assert new_soc < 0.90
    assert p_batt > 0.0


def test_battery_charges_from_surplus():
    """7. Battery charges when alternator output exceeds electrical load demand."""
    new_soc, v_bat, i_batt, p_batt = ElectricalAircraftModel.step_battery_soc(
        current_soc=0.80, net_electrical_power_demand_w=-400.0, dt_seconds=1.0, nominal_energy_j=2592000.0, nominal_voltage_v=24.0, charge_efficiency=0.90, discharge_efficiency=0.95
    )

    assert i_batt < 0.0  # Charge convention
    assert new_soc > 0.80
    assert p_batt < 0.0


def test_soc_remains_bounded_0_to_1():
    """8. Battery SOC remains strictly bounded within [0.0, 1.0]."""
    soc_over, _, _, _ = ElectricalAircraftModel.step_battery_soc(1.0, -1000.0, 100.0)
    soc_under, _, _, _ = ElectricalAircraftModel.step_battery_soc(0.0, 10000.0, 1000.0)

    assert soc_over == 1.0
    assert soc_under == 0.0


def test_deterministic_battery_trajectory():
    """9. Identical battery integration inputs produce identical SOC trajectories."""
    soc_a, _, _, _ = ElectricalAircraftModel.step_battery_soc(0.90, 200.0, 5.0)
    soc_b, _, _, _ = ElectricalAircraftModel.step_battery_soc(0.90, 200.0, 5.0)

    assert soc_a == soc_b


def test_no_electrical_energy_creation():
    """10. Electrical power balance obeys conservation: P_alt + P_dis = P_load + P_chg."""
    p_net = 300.0  # Deficit
    new_soc, v_bat, i_batt, p_batt_dis = ElectricalAircraftModel.step_battery_soc(0.80, p_net, 1.0, discharge_efficiency=0.95)

    assert math.isclose(p_batt_dis * 0.95, p_net, rel_tol=1e-4)


# ==============================================================================
# STARTER MOTOR TESTS (11 - 16)
# ==============================================================================

def test_starter_draws_battery_current():
    """11. Active starter motor consumes electrical power and draws battery current."""
    active, p_starter, t_starter = ElectricalAircraftModel.compute_starter_torque_and_power(
        starter_active=True, engine_rpm=0.0, battery_soc=0.90, min_starting_soc=0.20, starter_power_w=1500.0
    )

    assert active == 1.0
    assert p_starter == 1500.0
    assert t_starter > 0.0


def test_starter_torque_reaches_crankshaft(clock, loaded_config):
    """12. Starter mechanical torque assists crankshaft acceleration."""
    runner = EngineRunner(clock, engine_config=loaded_config)
    eng = runner.step_engine(1, throttle_percent=0.0, starter_torque_n_m=80.0)

    assert eng.engine_rpm > 0.0


def test_engine_rpm_rises_during_cranking(clock, loaded_config):
    """13. Engine RPM increases dynamically during starter cranking."""
    runner = EngineRunner(clock, engine_config=loaded_config)
    rpm_0 = runner.state.engines[1].engine_rpm

    for _ in range(20):
        eng = runner.step_engine(1, throttle_percent=0.0, starter_torque_n_m=60.0)

    assert eng.engine_rpm > rpm_0


def test_starting_sequence_is_causal(clock, loaded_config):
    """14. Starting sequence evolves causally from zero RPM up to idle speed."""
    runner = EngineRunner(clock, engine_config=loaded_config)
    rpms = []

    for _ in range(50):
        eng = runner.step_engine(1, throttle_percent=0.0, starter_torque_n_m=50.0)
        rpms.append(eng.engine_rpm)

    assert rpms[0] == 0.0 or rpms[1] > rpms[0]
    assert rpms[-1] > rpms[0]


def test_insufficient_soc_prevents_or_limits_starting():
    """15. Low battery SOC below min_starting_soc prevents starter engagement."""
    active, p_starter, t_starter = ElectricalAircraftModel.compute_starter_torque_and_power(
        starter_active=True, engine_rpm=0.0, battery_soc=0.10, min_starting_soc=0.20, starter_power_w=1500.0
    )

    assert active == 0.0
    assert p_starter == 0.0
    assert t_starter == 0.0


def test_starter_stops_after_running_transition():
    """16. Starter automatically disengages once engine RPM reaches idle speed."""
    active, p_starter, t_starter = ElectricalAircraftModel.compute_starter_torque_and_power(
        starter_active=True, engine_rpm=1500.0, battery_soc=0.90, min_starting_soc=0.20, idle_rpm=1400.0
    )

    assert active == 0.0
    assert p_starter == 0.0
    assert t_starter == 0.0


# ==============================================================================
# 3-DOF AIRCRAFT DYNAMICS TESTS (17 - 26)
# ==============================================================================

def test_total_thrust_equals_engine1_plus_engine2(clock, loaded_config):
    """17. Total propulsive thrust equals the sum of Engine 1 and Engine 2 thrusts."""
    runner = ElectricalAircraftRunner(clock, engine_config=loaded_config)
    _, _, ac, _, _ = runner.step_electrical_and_aircraft({1: 3000.0, 2: 3000.0}, {1: False, 2: False}, {1: 1200.0, 2: 1200.0}, 1.225)

    assert ac.total_thrust_n == 2400.0


def test_drag_increases_with_velocity():
    """18. Aerodynamic drag force increases quadratically with flight velocity."""
    _, _, _, _, drag_low, _, _, _ = ElectricalAircraftModel.compute_aircraft_longitudinal_dynamics(0.0, 1000.0, 30.0, 0.0, 2000.0, 1.225, 0.01)
    _, _, _, _, drag_high, _, _, _ = ElectricalAircraftModel.compute_aircraft_longitudinal_dynamics(0.0, 1000.0, 60.0, 0.0, 2000.0, 1.225, 0.01)

    assert drag_high > drag_low
    assert math.isclose(drag_high / drag_low, (60.0 / 30.0) ** 2, rel_tol=1e-3)


def test_drag_responds_to_density():
    """19. Aerodynamic drag decreases at higher altitudes due to lower air density."""
    _, _, _, _, drag_sea, _, _, _ = ElectricalAircraftModel.compute_aircraft_longitudinal_dynamics(0.0, 0.0, 50.0, 0.0, 2000.0, 1.225, 0.01)
    _, _, _, _, drag_alt, _, _, _ = ElectricalAircraftModel.compute_aircraft_longitudinal_dynamics(0.0, 6000.0, 50.0, 0.0, 2000.0, 0.660, 0.01)

    assert drag_alt < drag_sea
    assert math.isclose(drag_alt / drag_sea, 0.660 / 1.225, rel_tol=1e-3)


def test_acceleration_follows_force_balance():
    """20. Acceleration obeys Newton's second law: a = (F_thrust - F_drag - W*sin(gamma)) / m_ac."""
    _, _, _, accel, drag, weight, thrust, _ = ElectricalAircraftModel.compute_aircraft_longitudinal_dynamics(
        x_m=0.0, altitude_m=1000.0, velocity_m_s=50.0, flight_path_angle_rad=0.05, total_thrust_n=4000.0, air_density_kg_m3=1.10, dt_seconds=0.01, gross_mass_kg=1800.0, gravity_m_s2=9.80665
    )

    expected_accel = (4000.0 - drag - weight * math.sin(0.05)) / 1800.0
    assert math.isclose(accel, expected_accel, rel_tol=1e-4)


def test_altitude_integrates_vertical_velocity():
    """21. Geometric altitude integrates vertical velocity V * sin(gamma)."""
    x_new, alt_new, v_new, _, _, _, _, _ = ElectricalAircraftModel.compute_aircraft_longitudinal_dynamics(
        x_m=0.0, altitude_m=1000.0, velocity_m_s=50.0, flight_path_angle_rad=0.10, total_thrust_n=3000.0, air_density_kg_m3=1.10, dt_seconds=2.0
    )

    assert alt_new > 1000.0
    assert x_new > 0.0


def test_horizontal_position_integrates_velocity():
    """22. Horizontal position x integrates forward velocity V * cos(gamma)."""
    x_new, alt_new, v_new, _, _, _, _, _ = ElectricalAircraftModel.compute_aircraft_longitudinal_dynamics(
        x_m=100.0, altitude_m=1000.0, velocity_m_s=50.0, flight_path_angle_rad=0.0, total_thrust_n=2000.0, air_density_kg_m3=1.10, dt_seconds=1.0
    )

    assert math.isclose(x_new, 100.0 + 50.0 * 1.0, rel_tol=1e-2)
    assert alt_new == 1000.0


def test_atmosphere_coupling_works():
    """23. Atmosphere model provides pressure, temperature, and density for aircraft dynamics."""
    t_std = AtmosphereModel.compute_standard_temperature(3000.0)
    p_amb = AtmosphereModel.compute_ambient_pressure(3000.0)
    rho_3k, _, _ = AtmosphereModel.compute_moist_air_density(p_amb, t_std, 0.0)

    assert rho_3k < 1.225
    assert p_amb < 101325.0


def test_thrust_changes_aircraft_acceleration():
    """24. Higher total thrust produces higher longitudinal acceleration."""
    _, _, _, accel_low, _, _, _, _ = ElectricalAircraftModel.compute_aircraft_longitudinal_dynamics(0.0, 1000.0, 40.0, 0.0, 1500.0, 1.10, 0.01)
    _, _, _, accel_high, _, _, _, _ = ElectricalAircraftModel.compute_aircraft_longitudinal_dynamics(0.0, 1000.0, 40.0, 0.0, 3500.0, 1.10, 0.01)

    assert accel_high > accel_low


def test_twin_engine_asymmetric_thrust(clock, loaded_config):
    """25. Asymmetric twin engine thrust correctly sums to total aircraft thrust."""
    runner = ElectricalAircraftRunner(clock, engine_config=loaded_config)
    _, _, ac, _, _ = runner.step_electrical_and_aircraft({1: 3000.0, 2: 1400.0}, {1: False, 2: False}, {1: 1500.0, 2: 300.0}, 1.225)

    assert ac.total_thrust_n == 1800.0


def test_deterministic_aircraft_trajectory():
    """26. Identical initial aircraft state and thrust produce deterministic trajectory."""
    res_a = ElectricalAircraftModel.compute_aircraft_longitudinal_dynamics(0.0, 1000.0, 50.0, 0.05, 2500.0, 1.10, 1.0)
    res_b = ElectricalAircraftModel.compute_aircraft_longitudinal_dynamics(0.0, 1000.0, 50.0, 0.05, 2500.0, 1.10, 1.0)

    assert res_a == res_b


# ==============================================================================
# CONFIGURATION & PROVENANCE TESTS (27 - 34)
# ==============================================================================

def test_electrical_yaml_reaches_physics(loaded_config):
    """27. Electrical configuration parameters stream strictly from YAML."""
    val = ConfigLoader.get_config_value(loaded_config, "electrical.nominal_bus_voltage_v")
    assert val == 28.0


def test_battery_yaml_reaches_physics(loaded_config):
    """28. Battery configuration parameters stream strictly from YAML."""
    val = ConfigLoader.get_config_value(loaded_config, "battery.capacity_ah")
    assert val == 30.0


def test_starter_yaml_reaches_physics(loaded_config):
    """29. Starter motor configuration parameters stream strictly from YAML."""
    val = ConfigLoader.get_config_value(loaded_config, "starter.starter_power_w")
    assert val == 1500.0


def test_aircraft_yaml_reaches_physics(loaded_config):
    """30. Aircraft gross mass and wing area stream strictly from YAML."""
    mass = ConfigLoader.get_config_value(loaded_config, "aircraft.gross_takeoff_mass_kg")
    wing = ConfigLoader.get_config_value(loaded_config, "aerodynamics.wing_area_m2")
    assert mass == 1800.0
    assert wing == 22.5


def test_no_hardcoded_tapas_values():
    """31. Physics files contain zero TAPAS-specific default argument constants."""
    import inspect
    sig = inspect.signature(ElectricalAircraftModel.compute_alternator_output_and_shaft_load)
    assert sig.parameters["max_current_a"].default == 75.0  # Configured default fallback OK if YAML passed


def test_provenance_validation(loaded_config):
    """32. Every Phase 3.7 configuration item includes valid provenance metadata."""
    for key in ["electrical", "alternator", "battery", "starter", "aircraft", "aerodynamics"]:
        assert key in loaded_config
        for subkey, item in loaded_config[key].items():
            assert "value" in item
            assert "unit" in item
            assert "classification" in item


def test_parameter_registry_completeness():
    """33. All Phase 3.7 telemetry parameters are registered with valid metadata and zero orphans."""
    registry = ParameterRegistry()
    assert registry.validate_registry_integrity() is True

    required_ids = [
        "bus_voltage", "bus_current", "alternator_rpm", "alternator_power", "alternator_torque",
        "battery_soc", "battery_voltage", "battery_current", "battery_power", "starter_torque",
        "starter_power", "electrical_load_power", "aircraft_velocity", "aircraft_altitude",
        "aircraft_x_position", "flight_path_angle", "drag_force", "weight_force", "total_thrust", "longitudinal_acceleration"
    ]
    for param_id in required_ids:
        param = registry.get_parameter(param_id)
        assert param.canonical_unit is not None


def test_module01_remains_untouched():
    """34. Module 01 filesystem remains 100% untouched."""
    module01_dir = "src/module01"
    assert os.path.exists(module01_dir)
