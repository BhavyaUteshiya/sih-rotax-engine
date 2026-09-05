from src.module02.config.config_loader import ConfigLoader
from src.module02.core.clock import SimulationClock
from src.module02.simulation.thermodynamic_engine_runner import ThermodynamicEngineRunner


def test_default_engine_profile_is_rotax_914():
    cfg = ConfigLoader.load_engine_config()
    assert cfg["metadata"]["profile_id"] == "ROTAX_914_UL_115HP"
    assert cfg["general"]["cylinder_count"]["value"] == 4
    assert cfg["geometry_and_inertia"]["displacement_m3"]["value"] == 0.0012112
    assert cfg["power_and_performance"]["takeoff_rated_power_w"]["value"] == 84500.0
    assert cfg["power_and_performance"]["rated_rpm"]["value"] == 5800.0
    assert abs(cfg["gearbox"]["engine_to_propeller_speed_ratio"]["value"] - 0.41175986) < 1e-6


def test_rotax_requires_starter_for_start():
    r = ThermodynamicEngineRunner(SimulationClock(dt_seconds=0.01))
    for _ in range(50):
        r.step_thermodynamic_cycle({1: 40.0, 2: 0.0}, {1: False, 2: False})
    assert r.state.engines[1].engine_rpm == 0.0
    assert r.state.thermodynamics[1].fuel_mass_flow_kg_h == 0.0


def test_rotax_starter_then_self_sustaining():
    r = ThermodynamicEngineRunner(SimulationClock(dt_seconds=0.01))
    for _ in range(120):
        r.step_thermodynamic_cycle({1: 20.0, 2: 0.0}, {1: True, 2: False})
    rpm_cranked = r.state.engines[1].engine_rpm
    assert rpm_cranked > 0.0
    for _ in range(300):
        r.step_thermodynamic_cycle({1: 50.0, 2: 0.0}, {1: False, 2: False})
    e = r.state.engines[1]
    assert e.engine_rpm > rpm_cranked
    assert e.operating_state.value in {"IDLE", "RUNNING"}
    assert r.state.thermodynamics[1].fuel_mass_flow_kg_h > 0.0


def test_rotax_gearbox_and_environment_coupling():
    r = ThermodynamicEngineRunner(SimulationClock(dt_seconds=0.01))
    for _ in range(100):
        r.step_thermodynamic_cycle({1: 40.0, 2: 0.0}, {1: True, 2: False})
    for _ in range(200):
        r.step_thermodynamic_cycle({1: 70.0, 2: 0.0}, {1: False, 2: False})
    e = r.state.engines[1]
    p = r.propulsion_runner.state.propellers[1]
    assert p.propeller_rpm > 0.0
    assert abs(p.propeller_rpm / e.engine_rpm - 1.0 / 2.43) < 1e-3
    rho_sea = r.state.environment.air_density_kg_m3
    r.set_environment_inputs(altitude_m=3000.0, temp_offset_k=0.0, relative_humidity_percent=0.0, wind_speed_m_s=0.0)
    r.step_thermodynamic_cycle({1: 70.0, 2: 0.0}, {1: False, 2: False})
    assert r.state.environment.air_density_kg_m3 < rho_sea
