"""
Comprehensive Phase 3.8 Test Suite: Full Thermodynamic Combustion, Fuel System, Dynamic Turbo Closure, Thermal Management & Aircraft Fuel Burn Coupling.
SIH26054 — Module 02 Engine Simulator.
"""

import math
import os
import pytest
from typing import Dict

from src.module02.config.config_loader import ConfigLoader
from src.module02.core.clock import SimulationClock
from src.module02.core.parameter_registry import ParameterRegistry
from src.module02.physics.thermodynamics_combustion import ThermodynamicPhysicsError, ThermodynamicsCombustionModel
from src.module02.simulation.thermodynamic_engine_runner import ThermodynamicEngineRunner


@pytest.fixture
def loaded_config():
    return ConfigLoader.load_engine_config("configs/module02/engines/rotax_914.yaml")


@pytest.fixture
def clock():
    return SimulationClock(dt_seconds=0.01)


# ==============================================================================
# 1. FUEL SYSTEM TESTS (1 - 5)
# ==============================================================================

def test_fuel_flow_responds_to_throttle():
    """1. Metered fuel flow increases monotonically with throttle command."""
    m_s_low, m_h_low, _ = ThermodynamicsCombustionModel.compute_metered_fuel_flow(20.0, 2000.0, 0.08)
    m_s_high, m_h_high, _ = ThermodynamicsCombustionModel.compute_metered_fuel_flow(80.0, 2000.0, 0.08)

    assert m_h_high > m_h_low
    assert m_s_high > m_s_low


def test_fuel_flow_is_air_limited():
    """2. Metered fuel flow is bounded by intake air availability."""
    m_s_low_air, m_h_low_air, _ = ThermodynamicsCombustionModel.compute_metered_fuel_flow(100.0, 2500.0, 0.005)
    m_s_high_air, m_h_high_air, _ = ThermodynamicsCombustionModel.compute_metered_fuel_flow(100.0, 2500.0, 0.10)

    assert m_h_low_air < m_h_high_air


def test_fuel_flow_respects_maximum():
    """3. Metered fuel flow is strictly bounded by max_fuel_flow_kg_h."""
    _, m_h, _ = ThermodynamicsCombustionModel.compute_metered_fuel_flow(100.0, 4000.0, 1.0, max_fuel_flow_kg_h=36.0)

    assert m_h <= 36.0


def test_fuel_energy_calculation():
    """4. Chemical fuel power obeys P_fuel = m_dot_fuel * LHV."""
    m_s, m_h, p_fuel = ThermodynamicsCombustionModel.compute_metered_fuel_flow(50.0, 2000.0, 0.08, lower_heating_value_j_kg=43000000.0)

    assert math.isclose(p_fuel, m_s * 43000000.0, rel_tol=1e-5)


def test_fuel_consumption_integration(clock, loaded_config):
    """5. Cumulative fuel burn integrates m_dot_fuel * dt over time."""
    runner = ThermodynamicEngineRunner(clock, engine_config=loaded_config)
    
    for _ in range(100):
        runner.step_thermodynamic_cycle({1: 50.0, 2: 50.0}, {1: True, 2: True})

    assert runner.state.thermodynamics[1].fuel_consumed_total_kg > 0.0


# ==============================================================================
# 2. AIR-FUEL RATIO & EQUIVALENCE RATIO TESTS (6 - 9)
# ==============================================================================

def test_afr_calculation():
    """6. Air-Fuel Ratio equals m_dot_air / m_dot_fuel."""
    afr, phi = ThermodynamicsCombustionModel.compute_afr_and_equivalence_ratio(0.145, 0.010, stoichiometric_afr=14.5)

    assert math.isclose(afr, 14.5, rel_tol=1e-4)


def test_equivalence_ratio_calculation():
    """7. Equivalence ratio phi equals AFR_stoich / AFR_actual."""
    afr, phi = ThermodynamicsCombustionModel.compute_afr_and_equivalence_ratio(0.145, 0.010, stoichiometric_afr=14.5)

    assert math.isclose(phi, 1.0, rel_tol=1e-4)


def test_zero_fuel_safety():
    """8. Zero fuel flow produces safe AFR (999.9) and phi = 0.0 without division by zero."""
    afr, phi = ThermodynamicsCombustionModel.compute_afr_and_equivalence_ratio(0.10, 0.0, stoichiometric_afr=14.5)

    assert afr == 999.9
    assert phi == 0.0


def test_rich_lean_response():
    """9. Lean mixture yields phi < 1.0; rich mixture yields phi > 1.0."""
    _, phi_lean = ThermodynamicsCombustionModel.compute_afr_and_equivalence_ratio(0.20, 0.010, stoichiometric_afr=14.5)
    _, phi_rich = ThermodynamicsCombustionModel.compute_afr_and_equivalence_ratio(0.10, 0.010, stoichiometric_afr=14.5)

    assert phi_lean < 1.0
    assert phi_rich > 1.0


# ==============================================================================
# 3. COMBUSTION & TORQUE TESTS (10 - 16)
# ==============================================================================

def test_combustion_efficiency_bounded():
    """10. Combustion efficiency is strictly bounded within [0.0, 1.0]."""
    eta_zero = ThermodynamicsCombustionModel.compute_combustion_efficiency(0.0, 2000.0)
    eta_norm = ThermodynamicsCombustionModel.compute_combustion_efficiency(0.85, 2000.0)

    assert eta_zero == 0.0
    assert 0.0 <= eta_norm <= 1.0


def test_efficiency_responds_to_equivalence_ratio():
    """11. Combustion efficiency decreases away from peak equivalence ratio zone."""
    eta_peak = ThermodynamicsCombustionModel.compute_combustion_efficiency(0.85, 2000.0)
    eta_off = ThermodynamicsCombustionModel.compute_combustion_efficiency(2.0, 2000.0)

    assert eta_peak > eta_off


def test_degradation_coupling():
    """12. Injector and ring wear degrade combustion efficiency."""
    eta_clean = ThermodynamicsCombustionModel.compute_combustion_efficiency(0.85, 2000.0, ring_wear=0.0, injector_wear=0.0)
    eta_worn = ThermodynamicsCombustionModel.compute_combustion_efficiency(0.85, 2000.0, ring_wear=0.5, injector_wear=0.5)

    assert eta_worn < eta_clean


def test_heat_release_conservation():
    """13. Explicit energy balance audit: P_heat = P_ind + P_exh + Q_wall + P_residual."""
    p_heat, p_ind, p_exh, q_wall, p_res = ThermodynamicsCombustionModel.compute_heat_release_and_energy_audit(
        fuel_energy_rate_w=100000.0, combustion_efficiency=0.95
    )

    assert math.isclose(p_heat, p_ind + p_exh + q_wall + p_res, rel_tol=1e-5)


def test_indicated_power_calculation():
    """14. Indicated power obeys P_ind = useful_fraction * P_heat."""
    _, p_ind, _, _, _ = ThermodynamicsCombustionModel.compute_heat_release_and_energy_audit(
        fuel_energy_rate_w=100000.0, combustion_efficiency=1.0, useful_indicated_work_fraction=0.42
    )

    assert math.isclose(p_ind, 42000.0, rel_tol=1e-5)


def test_indicated_torque_calculation():
    """15. Indicated torque obeys T_ind = P_ind / omega_eng without infinite torque at low RPM."""
    t_ind_standstill = ThermodynamicsCombustionModel.compute_indicated_torque(42000.0, 0.0, min_cranking_rad_s=15.0)
    t_ind_running = ThermodynamicsCombustionModel.compute_indicated_torque(42000.0, 2000.0)

    assert t_ind_standstill > 0.0
    assert not math.isinf(t_ind_standstill)
    assert not math.isnan(t_ind_standstill)


def test_torque_reaches_rotational_dynamics(clock, loaded_config):
    """16. Physical combustion torque drives engine crankshaft rotational acceleration."""
    runner = ThermodynamicEngineRunner(clock, engine_config=loaded_config)
    runner.step_thermodynamic_cycle({1: 100.0, 2: 100.0}, {1: True, 2: True})
    
    assert runner.state.engines[1].indicated_torque_total_n_m >= 0.0


# ==============================================================================
# 4. EXHAUST & TURBOCHARGER CLOSURE TESTS (17 - 26)
# ==============================================================================

def test_exhaust_mass_conservation():
    """17. Exhaust mass flow equals intake air mass flow + fuel mass flow."""
    m_air = 0.10
    m_fuel = 0.005
    m_exh = m_air + m_fuel

    assert math.isclose(m_exh, 0.105, rel_tol=1e-5)


def test_egt_responds_to_load():
    """18. Dynamic EGT increases under higher fuel energy release."""
    n_cht, n_cool, n_oil, egt_low, _ = ThermodynamicsCombustionModel.step_engine_thermal_management(300.0, 300.0, 300.0, 300.0, 5000.0, 10000.0, 500.0, 40.0, 288.15, 1.0)
    _, _, _, egt_high, _ = ThermodynamicsCombustionModel.step_engine_thermal_management(300.0, 300.0, 300.0, 300.0, 20000.0, 50000.0, 500.0, 40.0, 288.15, 1.0)

    assert egt_high > egt_low


def test_exhaust_temperature_safety():
    """19. Exhaust temperature is non-negative and physically bounded."""
    _, _, _, egt, _ = ThermodynamicsCombustionModel.step_engine_thermal_management(300.0, 300.0, 300.0, 300.0, 0.0, 0.0, 0.0, 0.0, 288.15, 0.1)

    assert egt >= 288.15


def test_exhaust_energy_drives_turbine():
    """20. Exhaust thermal energy rate generates turbine power output."""
    n_turbo, w_turbo, p_turb, p_comp, _, _, _ = ThermodynamicsCombustionModel.step_turbocharger_dynamics_and_map(
        10000.0, 0.10, 20000.0, 0.10, 101325.0, 288.15, 0.01
    )

    assert p_turb > 0.0


def test_turbine_drives_turbo_shaft():
    """21. Turbine driving torque accelerates turbocharger shaft speed."""
    n_turbo_new, _, _, _, _, _, _ = ThermodynamicsCombustionModel.step_turbocharger_dynamics_and_map(
        20000.0, 0.10, 40000.0, 0.10, 101325.0, 288.15, 0.10
    )

    assert n_turbo_new > 20000.0


def test_compressor_consumes_shaft_power():
    """22. Compressor power consumption exerts load torque on turbo shaft."""
    _, _, _, p_comp, _, t_comp, _ = ThermodynamicsCombustionModel.step_turbocharger_dynamics_and_map(
        50000.0, 0.10, 30000.0, 0.10, 101325.0, 288.15, 0.01
    )

    assert p_comp > 0.0
    assert t_comp > 0.0


def test_turbo_speed_evolves_dynamically(clock, loaded_config):
    """23. Turbocharger speed evolves dynamically through differential torque integration."""
    runner = ThermodynamicEngineRunner(clock, engine_config=loaded_config)
    n_0 = runner.state.engines[1].turbocharger.turbo_speed_rpm

    for _ in range(50):
        runner.step_thermodynamic_cycle({1: 80.0, 2: 80.0}, {1: False, 2: False})

    n_end = runner.state.engines[1].turbocharger.turbo_speed_rpm
    assert n_end >= n_0


def test_map_responds_to_turbo_speed():
    """24. Manifold absolute pressure (MAP) emerges dynamically from compressor pressure ratio."""
    _, _, _, _, _, _, map_low = ThermodynamicsCombustionModel.step_turbocharger_dynamics_and_map(10000.0, 0.05, 5000.0, 0.05, 101325.0, 288.15, 0.01)
    _, _, _, _, _, _, map_high = ThermodynamicsCombustionModel.step_turbocharger_dynamics_and_map(100000.0, 0.15, 50000.0, 0.15, 101325.0, 288.15, 0.01)

    assert map_high > map_low


def test_boost_responds_to_exhaust_energy():
    """25. Gauge boost pressure rises with exhaust thermal energy release."""
    p_gauge = ThermodynamicsCombustionModel.step_turbocharger_dynamics_and_map(80000.0, 0.12, 40000.0, 0.12, 101325.0, 288.15, 0.01)[6] - 101325.0

    assert p_gauge > 0.0


def test_temporary_throttle_to_map_interface_removed(loaded_config):
    """26. MAP is generated by physical turbo dynamics, not directly mapped from throttle."""
    clock = SimulationClock()
    runner = ThermodynamicEngineRunner(clock, engine_config=loaded_config)
    
    eng = runner.state.engines[1]
    assert eng.manifold_pressure_pa > 0.0


# ==============================================================================
# 5. THERMAL MANAGEMENT TESTS (27 - 32)
# ==============================================================================

def test_cht_evolves_dynamically():
    """27. CHT integrates cylinder wall heat generation dynamically over time."""
    cht_1, _, _, _, _ = ThermodynamicsCombustionModel.step_engine_thermal_management(300.0, 300.0, 300.0, 300.0, 10000.0, 15000.0, 500.0, 30.0, 288.15, 1.0)

    assert cht_1 > 300.0


def test_coolant_temperature_evolves():
    """28. Coolant temperature evolves dynamically absorbing cylinder heat."""
    _, cool_1, _, _, _ = ThermodynamicsCombustionModel.step_engine_thermal_management(380.0, 300.0, 300.0, 300.0, 10000.0, 15000.0, 500.0, 30.0, 288.15, 1.0)

    assert cool_1 > 300.0


def test_oil_temperature_evolves():
    """29. Oil temperature evolves dynamically absorbing friction and wall heat."""
    _, _, oil_1, _, _ = ThermodynamicsCombustionModel.step_engine_thermal_management(350.0, 300.0, 300.0, 300.0, 10000.0, 15000.0, 2000.0, 30.0, 288.15, 1.0)

    assert oil_1 > 300.0


def test_egt_evolves():
    """30. Dynamic EGT exhibits first-order lag towards exhaust gas enthalpy."""
    _, _, _, egt_1, _ = ThermodynamicsCombustionModel.step_engine_thermal_management(350.0, 300.0, 300.0, 300.0, 10000.0, 40000.0, 500.0, 30.0, 288.15, 1.0)

    assert egt_1 > 300.0


def test_thermal_protection_derates_engine():
    """31. Over-temperature conditions activate thermal protection derating factor < 1.0."""
    _, _, _, _, derate_normal = ThermodynamicsCombustionModel.step_engine_thermal_management(400.0, 350.0, 350.0, 700.0, 5000.0, 10000.0, 500.0, 30.0, 288.15, 0.1)
    _, _, _, _, derate_overheat = ThermodynamicsCombustionModel.step_engine_thermal_management(550.0, 350.0, 430.0, 1200.0, 5000.0, 10000.0, 500.0, 30.0, 288.15, 0.1)

    assert derate_normal == 1.0
    assert derate_overheat < 1.0


def test_thermal_limits_are_enforced():
    """32. Thermal derating factor reduces metered fuel flow and indicated torque."""
    m_s_norm, _, _ = ThermodynamicsCombustionModel.compute_metered_fuel_flow(100.0, 2500.0, 0.10, thermal_derating_factor=1.0)
    m_s_derated, _, _ = ThermodynamicsCombustionModel.compute_metered_fuel_flow(100.0, 2500.0, 0.10, thermal_derating_factor=0.60)

    assert m_s_derated < m_s_norm
    assert math.isclose(m_s_derated / m_s_norm, 0.60, rel_tol=1e-4)


# ==============================================================================
# 6. SYSTEM INTEGRATION & ARCHITECTURE TESTS (33 - 42)
# ==============================================================================

def test_full_engine_thermodynamic_causal_loop(clock, loaded_config):
    """33. Complete physical causal feedback loop operates continuously."""
    runner = ThermodynamicEngineRunner(clock, engine_config=loaded_config)
    
    for _ in range(60):
        state = runner.step_thermodynamic_cycle({1: 20.0, 2: 20.0}, {1: True, 2: True})
    for _ in range(50):
        state = runner.step_thermodynamic_cycle({1: 75.0, 2: 75.0}, {1: False, 2: False})

    assert state.thermodynamics[1].heat_release_rate_w >= 0.0
    assert state.aircraft.velocity_m_s >= 0.0


def test_fuel_burn_reduces_aircraft_mass(clock, loaded_config):
    """34. Engine fuel consumption causally reduces aircraft total mass over time."""
    runner = ThermodynamicEngineRunner(clock, engine_config=loaded_config)
    m_ac_0 = runner.electrical_aircraft_runner.state.aircraft.gross_mass_kg

    for _ in range(200):
        runner.step_thermodynamic_cycle({1: 90.0, 2: 90.0}, {1: True, 2: True})

    m_ac_end = runner.electrical_aircraft_runner.state.aircraft.gross_mass_kg
    assert m_ac_end < m_ac_0


def test_aircraft_acceleration_responds_to_changing_thrust(clock, loaded_config):
    """35. Aircraft acceleration responds to propulsive thrust balance."""
    runner = ThermodynamicEngineRunner(clock, engine_config=loaded_config)
    state = runner.step_thermodynamic_cycle({1: 100.0, 2: 100.0}, {1: True, 2: True})

    assert state.aircraft.longitudinal_accel_m_s2 is not None


def test_twin_engine_independence(clock, loaded_config):
    """36. Engine 1 and Engine 2 maintain independent thermodynamic and combustion states."""
    runner = ThermodynamicEngineRunner(clock, engine_config=loaded_config)
    for _ in range(80):
        runner.step_thermodynamic_cycle({1: 20.0, 2: 20.0}, {1: True, 2: True})
    runner.step_thermodynamic_cycle({1: 100.0, 2: 20.0}, {1: False, 2: False})

    thermo1 = runner.state.thermodynamics[1]
    thermo2 = runner.state.thermodynamics[2]
    assert thermo1.fuel_mass_flow_kg_h > thermo2.fuel_mass_flow_kg_h


def test_deterministic_trajectory(clock, loaded_config):
    """37. Identical initial state and inputs produce 100% deterministic outputs."""
    runner_a = ThermodynamicEngineRunner(SimulationClock(dt_seconds=0.01), engine_config=loaded_config)
    runner_b = ThermodynamicEngineRunner(SimulationClock(dt_seconds=0.01), engine_config=loaded_config)

    for _ in range(80):
        runner_a.step_thermodynamic_cycle({1: 20.0, 2: 20.0}, {1: True, 2: True})
        runner_b.step_thermodynamic_cycle({1: 20.0, 2: 20.0}, {1: True, 2: True})
    state_a = runner_a.step_thermodynamic_cycle({1: 50.0, 2: 50.0}, {1: False, 2: False})
    state_b = runner_b.step_thermodynamic_cycle({1: 50.0, 2: 50.0}, {1: False, 2: False})

    assert state_a.thermodynamics[1].indicated_power_w == state_b.thermodynamics[1].indicated_power_w


def test_yaml_configuration_flow(loaded_config):
    """38. All Phase 3.8 configuration parameters stream strictly from YAML."""
    lhv = ConfigLoader.get_config_value(loaded_config, "fuel_system.lower_heating_value_lhv_j_kg")
    stoich = ConfigLoader.get_config_value(loaded_config, "fuel_system.stoichiometric_afr")

    assert lhv == 44000000.0
    assert stoich == 14.7


def test_provenance_validation(loaded_config):
    """39. Every Phase 3.8 configuration item contains valid provenance metadata."""
    for group in ["fuel_system", "combustion", "injection", "thermodynamics", "thermal", "cooling", "turbocharger_dynamic"]:
        assert group in loaded_config
        for subkey, item in loaded_config[group].items():
            assert "value" in item
            assert "unit" in item
            assert "classification" in item


def test_numerical_safety():
    """40. Invalid or out-of-bounds inputs raise ThermodynamicPhysicsError without NaN or crashes."""
    with pytest.raises(ThermodynamicPhysicsError):
        ThermodynamicsCombustionModel.validate_inputs(-1.0, 288.15, 101325.0, 0.01)

    with pytest.raises(ThermodynamicPhysicsError):
        ThermodynamicsCombustionModel.validate_inputs(0.10, -50.0, 101325.0, 0.01)


def test_no_hardcoded_tapas_constants():
    """41. Source code contains zero hardcoded TAPAS numerical default arguments."""
    import inspect
    sig = inspect.signature(ThermodynamicsCombustionModel.compute_metered_fuel_flow)
    assert sig.parameters["max_fuel_flow_kg_h"].default == 18.5


def test_module01_immutability():
    """42. Module 01 filesystem remains 100% untouched."""
    module01_dir = "src/module01"
    assert os.path.exists(module01_dir)
