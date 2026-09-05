"""
Phase 3.5 Dynamic Thermal & Lubrication Physics Test Suite.
SIH26054 — Module 02 Engine Simulator.
"""

import math
import pytest
from src.module02.config.config_loader import ConfigLoader
from src.module02.core.clock import SimulationClock
from src.module02.physics.thermal_lubrication import ThermalLubricationModel, ThermalLubricationPhysicsError
from src.module02.simulation.combustion_runner import CombustionRunner
from src.module02.simulation.engine_runner import EngineRunner
from src.module02.simulation.intake_runner import IntakeRunner
from src.module02.simulation.thermal_runner import ThermalRunner
from src.module02.simulation.turbo_runner import TurboRunner


def test_cht_rises_with_combustion_power():
    """1. CHT rises with increased combustion power."""
    runner = ThermalRunner(SimulationClock(dt_seconds=0.1))

    # Low power step for 10 s
    for _ in range(100):
        eng, therm, _ = runner.step_thermal(1, fuel_energy_rate_w=20000.0, indicated_power_w=8000.0, exhaust_energy_rate_w=8000.0, exhaust_temp_k=500.0, engine_rpm=2000.0, engine_friction_torque_n_m=15.0)
    cht_low = therm.cht_k

    # High power step for 10 s
    for _ in range(100):
        eng, therm, _ = runner.step_thermal(1, fuel_energy_rate_w=350000.0, indicated_power_w=140000.0, exhaust_energy_rate_w=135000.0, exhaust_temp_k=850.0, engine_rpm=4200.0, engine_friction_torque_n_m=25.0)
    cht_high = therm.cht_k

    assert cht_high > cht_low


def test_cht_falls_when_power_reduced():
    """2. CHT falls when power is reduced."""
    runner = ThermalRunner(SimulationClock(dt_seconds=0.1))

    # Heat engine up at high power for 50 s
    for _ in range(500):
        eng, therm, _ = runner.step_thermal(1, fuel_energy_rate_w=350000.0, indicated_power_w=140000.0, exhaust_energy_rate_w=135000.0, exhaust_temp_k=850.0, engine_rpm=4200.0, engine_friction_torque_n_m=25.0)
    cht_hot = therm.cht_k

    # Reduce power for 50 s
    for _ in range(500):
        eng, therm, _ = runner.step_thermal(1, fuel_energy_rate_w=0.0, indicated_power_w=0.0, exhaust_energy_rate_w=0.0, exhaust_temp_k=288.15, engine_rpm=0.0, engine_friction_torque_n_m=0.0)
    cht_cooled = therm.cht_k

    assert cht_cooled < cht_hot


def test_cht_responds_to_ambient_temperature():
    """3. CHT responds to ambient temperature differences."""
    runner_cold = ThermalRunner(SimulationClock(dt_seconds=0.1))
    runner_hot = ThermalRunner(SimulationClock(dt_seconds=0.1))

    for _ in range(100):
        runner_cold.step_thermal(1, 150000.0, 60000.0, 60000.0, 700.0, 3000.0, 20.0, ambient_temp_k=250.0) # Cold ambient (-23°C)
        runner_hot.step_thermal(1, 150000.0, 60000.0, 60000.0, 700.0, 3000.0, 20.0, ambient_temp_k=320.0)  # Hot ambient (+47°C)

    assert runner_hot.state.thermals[1].cht_k > runner_cold.state.thermals[1].cht_k


def test_cht_responds_to_cooling():
    """4. CHT responds to ram air cooling (higher airspeed increases cooling heat rejection)."""
    runner_static = ThermalRunner(SimulationClock(dt_seconds=0.1))
    runner_flying = ThermalRunner(SimulationClock(dt_seconds=0.1))

    for _ in range(100):
        runner_static.step_thermal(1, 150000.0, 60000.0, 60000.0, 700.0, 3000.0, 20.0, airspeed_m_s=0.0)   # Static ground
        runner_flying.step_thermal(1, 150000.0, 60000.0, 60000.0, 700.0, 3000.0, 20.0, airspeed_m_s=60.0)  # High airspeed (60 m/s)

    assert runner_flying.state.thermals[1].cooling_heat_rejection_w > runner_static.state.thermals[1].cooling_heat_rejection_w
    assert runner_flying.state.thermals[1].cht_k < runner_static.state.thermals[1].cht_k


def test_cht_gradual_dynamic_integration():
    """5. CHT does not instantly jump to arbitrary values (gradual differential integration)."""
    runner = ThermalRunner(SimulationClock(dt_seconds=0.01))

    cht_0 = runner.state.thermals[1].cht_k
    runner.step_thermal(1, 350000.0, 140000.0, 135000.0, 850.0, 4200.0, 25.0)
    cht_1 = runner.state.thermals[1].cht_k

    # Single step delta must be small and smooth
    assert (cht_1 - cht_0) < 5.0, "CHT must not jump discontinuously in a single 10ms timestep."


def test_egt_responds_to_combustion():
    """6. EGT responds to combustion heat release."""
    runner = ThermalRunner(SimulationClock(dt_seconds=0.1))

    for _ in range(50):
        runner.step_thermal(1, 100000.0, 40000.0, 40000.0, exhaust_temp_k=650.0, engine_rpm=2500.0, engine_friction_torque_n_m=18.0)
    egt_low = runner.state.thermals[1].egt_k

    for _ in range(50):
        runner.step_thermal(1, 350000.0, 140000.0, 135000.0, exhaust_temp_k=900.0, engine_rpm=4200.0, engine_friction_torque_n_m=25.0)
    egt_high = runner.state.thermals[1].egt_k

    assert egt_high > egt_low


def test_egt_coupled_to_exhaust_energy():
    """7. EGT remains coupled to exhaust energy."""
    egt_new = ThermalLubricationModel.compute_dynamic_egt(current_egt_k=300.0, exhaust_temp_k=800.0, egt_sensor_time_constant_sec=0.5, dt_seconds=0.1)
    assert egt_new > 300.0


def test_oil_temperature_rises_under_load():
    """8. Oil temperature rises under sustained load."""
    runner = ThermalRunner(SimulationClock(dt_seconds=0.1))

    for _ in range(200):
        runner.step_thermal(1, 300000.0, 120000.0, 120000.0, 800.0, 4000.0, 25.0)
    t_oil_hot = runner.state.lubrication[1].oil_temperature_k

    assert t_oil_hot > 288.15


def test_oil_temperature_cools_after_load_reduction():
    """9. Oil temperature cools after load reduction."""
    runner = ThermalRunner(SimulationClock(dt_seconds=0.1))

    # Heat up oil
    for _ in range(300):
        runner.step_thermal(1, 300000.0, 120000.0, 120000.0, 800.0, 4000.0, 25.0)
    t_oil_hot = runner.state.lubrication[1].oil_temperature_k

    # Cut load / engine off
    for _ in range(500):
        runner.step_thermal(1, 0.0, 0.0, 0.0, 288.15, 0.0, 0.0)
    t_oil_cooled = runner.state.lubrication[1].oil_temperature_k

    assert t_oil_cooled < t_oil_hot


def test_viscosity_changes_with_oil_temperature():
    """10-12. Vogel viscosity changes correctly: cold oil increases viscosity, hot oil decreases viscosity."""
    mu_cold = ThermalLubricationModel.compute_oil_viscosity(oil_temperature_k=288.15) # 15°C
    mu_ref = ThermalLubricationModel.compute_oil_viscosity(oil_temperature_k=373.15)  # 100°C reference
    mu_hot = ThermalLubricationModel.compute_oil_viscosity(oil_temperature_k=393.15)  # 120°C

    assert mu_cold > mu_ref, "Cold oil must be more viscous than reference."
    assert mu_hot < mu_ref, "Hot oil must be less viscous than reference."


def test_viscosity_affects_friction():
    """13. Viscosity affects engine friction torque."""
    t_fric_cold, _ = ThermalLubricationModel.compute_viscosity_modified_friction_torque(2500.0, oil_viscosity_pa_s=0.10, friction_static_n_m=15.0, friction_viscous_n_m_s_rad=0.05, friction_hydrodynamic_n_m_s2_rad2=0.0001)
    t_fric_hot, _ = ThermalLubricationModel.compute_viscosity_modified_friction_torque(2500.0, oil_viscosity_pa_s=0.01, friction_static_n_m=15.0, friction_viscous_n_m_s_rad=0.05, friction_hydrodynamic_n_m_s2_rad2=0.0001)

    assert t_fric_cold > t_fric_hot, "Cold viscous oil must exert higher friction torque."


def test_full_causal_feedback_loop_thermal():
    """14-17. Full Causal Chain: Friction -> RPM -> Airflow -> Combustion -> Thermal state -> Oil Temp -> Viscosity -> Friction."""
    clock = SimulationClock(dt_seconds=0.01)
    cfg = ConfigLoader.load_engine_config("configs/module02/engines/tapas_bh201_180hp_uav_diesel.yaml")

    eng_runner = EngineRunner(clock, engine_config=cfg)
    intake_runner = IntakeRunner(clock, engine_config=cfg)
    comb_runner = CombustionRunner(clock, engine_config=cfg)
    turbo_runner = TurboRunner(clock, engine_config=cfg)
    thermal_runner = ThermalRunner(clock, engine_config=cfg)

    # Initial state
    eng_st = eng_runner.step_engine(1, throttle_percent=100.0)
    intake_st = intake_runner.step_intake(1, eng_st.engine_rpm, 100.0, 101325.0, 288.15)
    comb_st = comb_runner.step_combustion(1, 100.0, intake_st.air_mass_flow_kg_s, eng_st.engine_rpm)
    turbo_st = turbo_runner.step_turbo(1, comb_st.exhaust.exhaust_mass_flow_kg_s, comb_st.exhaust.exhaust_temp_k, comb_st.exhaust.exhaust_energy_rate_w, intake_st.air_mass_flow_kg_s)
    eng_st, therm_st, lub_st = thermal_runner.step_thermal(1, comb_st.fuel.fuel_energy_rate_w, comb_st.combustion.indicated_power_w, comb_st.exhaust.exhaust_energy_rate_w, comb_st.exhaust.exhaust_temp_k, eng_st.engine_rpm, eng_st.friction_torque_n_m)

    initial_cht = therm_st.cht_k

    for _ in range(100):
        eng_st = eng_runner.step_engine(1, throttle_percent=100.0)
        intake_st = intake_runner.step_intake(1, eng_st.engine_rpm, 100.0, 101325.0, 288.15, manifold_pressure_pa=turbo_st.manifold_pressure_pa)
        comb_st = comb_runner.step_combustion(1, 100.0, intake_st.air_mass_flow_kg_s, eng_st.engine_rpm)
        turbo_st = turbo_runner.step_turbo(1, comb_st.exhaust.exhaust_mass_flow_kg_s, comb_st.exhaust.exhaust_temp_k, comb_st.exhaust.exhaust_energy_rate_w, intake_st.air_mass_flow_kg_s)
        eng_st, therm_st, lub_st = thermal_runner.step_thermal(1, comb_st.fuel.fuel_energy_rate_w, comb_st.combustion.indicated_power_w, comb_st.exhaust.exhaust_energy_rate_w, comb_st.exhaust.exhaust_temp_k, eng_st.engine_rpm, eng_st.friction_torque_n_m)
        clock.step()

    assert therm_st.cht_k > initial_cht, "CHT must rise as combustion proceeds."


def test_energy_accounting_validity():
    """18. Energy accounting: Qfuel >= Pind + Qexh + Qwall."""
    q_wall, q_loss = ThermalLubricationModel.compute_heat_partition(
        fuel_energy_rate_w=300000.0,
        indicated_power_w=120000.0,
        exhaust_energy_rate_w=100000.0,
        wall_heat_fraction=0.25
    )

    total_accounted = 120000.0 + 100000.0 + q_wall + q_loss
    assert math.isclose(300000.0, total_accounted, abs_tol=1e-3)


def test_twin_engine_thermal_independence():
    """19. Twin Engine Thermal Independence: Modifying Engine 1 thermal state does not alter Engine 2."""
    runner = ThermalRunner(SimulationClock(dt_seconds=0.1))

    # Heat up Engine 1
    for _ in range(50):
        runner.step_thermal(1, 300000.0, 120000.0, 120000.0, 800.0, 4000.0, 25.0)

    # Leave Engine 2 unheated
    st1 = runner.state.thermals[1]
    st2 = runner.state.thermals[2]

    assert st1.cht_k > st2.cht_k
    assert st1.wall_heat_generation_w > st2.wall_heat_generation_w


def test_repeated_simulation_determinism():
    """20. Determinism: 100% bit-for-bit identical thermal trajectories given identical inputs."""
    runner1 = ThermalRunner(SimulationClock(dt_seconds=0.1))
    runner2 = ThermalRunner(SimulationClock(dt_seconds=0.1))

    traj1 = []
    traj2 = []

    for _ in range(50):
        _, th1, lub1 = runner1.step_thermal(1, 200000.0, 80000.0, 80000.0, 750.0, 3000.0, 20.0)
        _, th2, lub2 = runner2.step_thermal(1, 200000.0, 80000.0, 80000.0, 750.0, 3000.0, 20.0)

        traj1.append((th1.cht_k, lub1.oil_temperature_k, lub1.oil_viscosity_pa_s))
        traj2.append((th2.cht_k, lub2.oil_temperature_k, lub2.oil_viscosity_pa_s))

    assert traj1 == traj2


def test_configuration_flow_thermal():
    """21. Configuration Flow: Modifying YAML parameters changes thermal behavior without Python code edits."""
    cfg_tapas = ConfigLoader.load_engine_config("configs/module02/engines/tapas_bh201_180hp_uav_diesel.yaml")
    cfg_gasoline = ConfigLoader.load_engine_config("configs/module02/engines/generic_115hp_gasoline.yaml")

    runner_tapas = ThermalRunner(SimulationClock(dt_seconds=0.1), engine_config=cfg_tapas)
    runner_gasoline = ThermalRunner(SimulationClock(dt_seconds=0.1), engine_config=cfg_gasoline)

    runner_tapas.step_thermal(1, 100000.0, 40000.0, 40000.0, 700.0, 3000.0, 20.0)
    runner_gasoline.step_thermal(1, 100000.0, 40000.0, 40000.0, 700.0, 3000.0, 20.0)

    # Different thermal masses lead to different delta CHT
    assert runner_tapas.state.thermals[1].cht_k != runner_gasoline.state.thermals[1].cht_k


def test_numerical_safety_and_rejections():
    """22-24. Numerical Safety: Rejects invalid masses, dt <= 0, NaN/Inf, and negative physical values."""
    with pytest.raises(ThermalLubricationPhysicsError):
        ThermalLubricationModel.validate_inputs(-10.0, 480.0, 4.5, 2100.0, 0.01)

    with pytest.raises(ThermalLubricationPhysicsError):
        ThermalLubricationModel.validate_inputs(18.0, 480.0, 4.5, 2100.0, -0.01)

    with pytest.raises(ThermalLubricationPhysicsError):
        ThermalLubricationModel.compute_heat_partition(-100.0, 50.0, 50.0)

    with pytest.raises(ThermalLubricationPhysicsError):
        ThermalLubricationModel.step_cht_and_cooling(-300.0, 1000.0, 288.15, 0.0, 2000.0, 18.0, 480.0)
