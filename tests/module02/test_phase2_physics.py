"""
Phase 2 Atmosphere & Flight Environment Physics Test Suite.
SIH26054 — Module 02 Engine Simulator.
"""

import math
import pytest
from src.module02.core.clock import SimulationClock
from src.module02.models.enums import FlightPhase, ParameterStatus
from src.module02.models.states import FlightState
from src.module02.physics.atmosphere import AtmosphereModel, AtmospherePhysicsError
from src.module02.physics.flight_environment import FlightEnvironmentModel, FlightEnvironmentError
from src.module02.simulation.environment_runner import EnvironmentRunner
from src.module02.simulation.flight_phase_machine import FlightPhaseMachine


# ==============================================================================
# TEST GROUP 1 — SEA LEVEL REFERENCE
# ==============================================================================
def test_group_1_sea_level_reference():
    """Verify standard sea level atmospheric values: T ~ 288.15 K, P ~ 101325 Pa, rho ~ 1.225 kg/m3."""
    t_std = AtmosphereModel.compute_standard_temperature(0.0)
    p_amb = AtmosphereModel.compute_ambient_pressure(0.0)
    rho_moist, _, _ = AtmosphereModel.compute_moist_air_density(p_amb, t_std, 0.0)

    assert t_std == pytest.approx(288.15, abs=0.01)
    assert p_amb == pytest.approx(101325.0, abs=1.0)
    assert rho_moist == pytest.approx(1.225, abs=0.005)


# ==============================================================================
# TEST GROUP 2 — ALTITUDE MONOTONICITY
# ==============================================================================
def test_group_2_altitude_monotonicity():
    """Verify that pressure, density, and temperature decrease monotonically with altitude in troposphere."""
    altitudes = [0.0, 1000.0, 3000.0, 6000.0, 9000.0, 11000.0]

    temps = [AtmosphereModel.compute_standard_temperature(h) for h in altitudes]
    pressures = [AtmosphereModel.compute_ambient_pressure(h) for h in altitudes]
    densities = [AtmosphereModel.compute_moist_air_density(p, t, 0.0)[0] for p, t in zip(pressures, temps)]

    # Check strict monotonic decreasing order
    for i in range(len(altitudes) - 1):
        assert temps[i] > temps[i + 1], f"Temperature not monotonic between {altitudes[i]}m and {altitudes[i+1]}m"
        assert pressures[i] > pressures[i + 1], f"Pressure not monotonic between {altitudes[i]}m and {altitudes[i+1]}m"
        assert densities[i] > densities[i + 1], f"Density not monotonic between {altitudes[i]}m and {altitudes[i+1]}m"


# ==============================================================================
# TEST GROUP 3 — TEMPERATURE OFFSET
# ==============================================================================
def test_group_3_temperature_offset():
    """Verify that a positive temperature offset at constant altitude results in lower air density."""
    h = 3000.0
    p_amb = AtmosphereModel.compute_ambient_pressure(h)

    t_std = AtmosphereModel.compute_actual_temperature(h, temp_offset_k=0.0)
    t_hot = AtmosphereModel.compute_actual_temperature(h, temp_offset_k=15.0) # ISA + 15 K hot day

    rho_std, _, _ = AtmosphereModel.compute_moist_air_density(p_amb, t_std, 0.0)
    rho_hot, _, _ = AtmosphereModel.compute_moist_air_density(p_amb, t_hot, 0.0)

    assert t_hot > t_std
    assert rho_hot < rho_std, "Higher temperature must causally produce lower air density."


# ==============================================================================
# TEST GROUP 4 — HUMIDITY VALIDATION
# ==============================================================================
def test_group_4_humidity_validation():
    """Verify 0% and 100% relative humidity are valid, while negative and >100% are rejected."""
    # Valid
    AtmosphereModel.validate_inputs(0.0, 0.0, 0.0)
    AtmosphereModel.validate_inputs(0.0, 0.0, 100.0)

    # Invalid
    with pytest.raises(AtmospherePhysicsError):
        AtmosphereModel.validate_inputs(0.0, 0.0, -5.0)

    with pytest.raises(AtmospherePhysicsError):
        AtmosphereModel.validate_inputs(0.0, 0.0, 105.0)


# ==============================================================================
# TEST GROUP 5 — WIND VECTOR & AIRSPEED
# ==============================================================================
def test_group_5_wind_vector():
    """Verify zero wind produces V_air = V_ground, while headwind/crosswind modifies TAS appropriately."""
    v_ground_ned = (50.0, 0.0, 0.0) # 50 m/s North

    # Zero wind
    v_wind_zero = (0.0, 0.0, 0.0)
    v_rel_zero = FlightEnvironmentModel.compute_relative_air_velocity_ned(v_ground_ned, v_wind_zero)
    tas_zero = FlightEnvironmentModel.compute_true_airspeed_tas(v_rel_zero)
    assert tas_zero == pytest.approx(50.0)

    # Headwind (10 m/s North wind coming from North => air moving South (-10, 0, 0))
    v_wind_head = (-10.0, 0.0, 0.0)
    v_rel_head = FlightEnvironmentModel.compute_relative_air_velocity_ned(v_ground_ned, v_wind_head)
    tas_head = FlightEnvironmentModel.compute_true_airspeed_tas(v_rel_head)
    assert tas_head == pytest.approx(60.0) # 50 - (-10) = 60 m/s TAS


# ==============================================================================
# TEST GROUP 6 — DYNAMIC PRESSURE
# ==============================================================================
def test_group_6_dynamic_pressure():
    """Verify dynamic pressure equation q = 0.5 * rho * V^2 within numerical tolerance."""
    rho = 1.225
    v_tas = 60.0 # m/s
    q = AtmosphereModel.compute_dynamic_pressure(rho, v_tas)
    expected_q = 0.5 * 1.225 * (60.0 ** 2) # 2205.0 Pa

    assert q == pytest.approx(expected_q, abs=1e-3)


# ==============================================================================
# TEST GROUP 7 — SPEED OF SOUND
# ==============================================================================
def test_group_7_speed_of_sound():
    """Verify speed of sound a = sqrt(gamma * R * T) at sea level (T = 288.15 K)."""
    t_sea = 288.15
    a_sea = AtmosphereModel.compute_speed_of_sound(t_sea)
    expected_a = math.sqrt(1.4 * 287.058 * 288.15) # ~340.29 m/s

    assert a_sea == pytest.approx(expected_a, abs=0.1)


# ==============================================================================
# TEST GROUP 8 — AIRCRAFT MASS
# ==============================================================================
def test_group_8_aircraft_mass():
    """Verify m_current = m_dry + m_payload + m_fuel_remaining and m_current >= 0."""
    flight = FlightState(dry_mass_kg=1800.0, payload_mass_kg=350.0, fuel_mass_remaining_kg=650.0)
    assert flight.current_mass_kg == 2800.0
    assert flight.current_mass_kg >= 0.0


# ==============================================================================
# TEST GROUP 9 — FLIGHT PHASE CLASSIFICATION
# ==============================================================================
def test_group_9_flight_phase_classification():
    """Verify deterministic flight phase state transitions."""
    # GROUND
    p_ground = FlightPhaseMachine.determine_flight_phase(altitude_m=0.0, airspeed_m_s=0.0, vertical_speed_m_s=0.0)
    assert p_ground == FlightPhase.GROUND

    # TAXI
    p_taxi = FlightPhaseMachine.determine_flight_phase(altitude_m=0.0, airspeed_m_s=10.0, vertical_speed_m_s=0.0)
    assert p_taxi == FlightPhase.TAXI

    # TAKEOFF
    p_to = FlightPhaseMachine.determine_flight_phase(altitude_m=5.0, airspeed_m_s=30.0, vertical_speed_m_s=2.0)
    assert p_to == FlightPhase.TAKEOFF

    # CLIMB
    p_climb = FlightPhaseMachine.determine_flight_phase(altitude_m=1000.0, airspeed_m_s=60.0, vertical_speed_m_s=5.0)
    assert p_climb == FlightPhase.CLIMB

    # CRUISE
    p_cruise = FlightPhaseMachine.determine_flight_phase(altitude_m=5000.0, airspeed_m_s=75.0, vertical_speed_m_s=0.0)
    assert p_cruise == FlightPhase.CRUISE

    # DESCENT
    p_descent = FlightPhaseMachine.determine_flight_phase(altitude_m=3000.0, airspeed_m_s=60.0, vertical_speed_m_s=-4.0)
    assert p_descent == FlightPhase.DESCENT

    # LANDING
    p_landing = FlightPhaseMachine.determine_flight_phase(altitude_m=8.0, airspeed_m_s=35.0, vertical_speed_m_s=-2.0)
    assert p_landing == FlightPhase.LANDING


# ==============================================================================
# TEST GROUP 10 — DETERMINISM
# ==============================================================================
def test_group_10_determinism():
    """Verify identical inputs, dt, and initial conditions produce 100% identical trajectory outputs."""
    runner1 = EnvironmentRunner(SimulationClock(dt_seconds=0.01))
    runner2 = EnvironmentRunner(SimulationClock(dt_seconds=0.01))

    runner1.initialize_environment(initial_altitude_m=100.0)
    runner2.initialize_environment(initial_altitude_m=100.0)

    trajectory1 = []
    trajectory2 = []

    v_g = (40.0, 0.0, -2.0) # Climbing in NED
    v_w = (-5.0, 0.0, 0.0)

    for _ in range(50):
        st1 = runner1.step(v_ground_ned_m_s=v_g, wind_ned_m_s=v_w)
        st2 = runner2.step(v_ground_ned_m_s=v_g, wind_ned_m_s=v_w)

        trajectory1.append((st1.environment.air_density_kg_m3, st1.flight.altitude_m, st1.flight.airspeed_m_s))
        trajectory2.append((st2.environment.air_density_kg_m3, st2.flight.altitude_m, st2.flight.airspeed_m_s))

    assert trajectory1 == trajectory2, "Phase 2 trajectories must be 100% deterministic."


# ==============================================================================
# TEST GROUP 11 — TIMESTEP SIMULATION INTEGRATION
# ==============================================================================
def test_group_11_timestep_integration():
    """Verify 10 x 0.01s steps advance simulation time by exactly 0.10s independent of wall-clock time."""
    runner = EnvironmentRunner(SimulationClock(dt_seconds=0.01))
    runner.initialize_environment()

    for _ in range(10):
        runner.step(v_ground_ned_m_s=(0.0, 0.0, 0.0))

    assert runner.clock.simulation_time_sec == pytest.approx(0.10, abs=1e-6)


# ==============================================================================
# TEST GROUP 12 — BOUNDARY CONDITIONS & NUMERICAL SAFETY
# ==============================================================================
def test_group_12_boundary_conditions_and_safety():
    """Verify handling of NaN, Inf, and boundary altitude limits."""
    with pytest.raises(AtmospherePhysicsError):
        AtmosphereModel.compute_environment_snapshot(altitude_m=float("nan"))

    with pytest.raises(AtmospherePhysicsError):
        AtmosphereModel.compute_environment_snapshot(altitude_m=float("inf"))

    with pytest.raises(AtmospherePhysicsError):
        AtmosphereModel.compute_environment_snapshot(altitude_m=25000.0) # Exceeds 20 km ceiling


# ==============================================================================
# PROPERTY / INVARIANT TESTS
# ==============================================================================
def test_property_invariants():
    """Verify property invariants P > 0, rho > 0, T > 0, a > 0, q >= 0 across altitudes 0 to 18,000m."""
    for alt in [0.0, 500.0, 2000.0, 6000.0, 10000.0, 15000.0, 18000.0]:
        env = AtmosphereModel.compute_environment_snapshot(altitude_m=alt, relative_humidity_percent=50.0)
        a = AtmosphereModel.compute_speed_of_sound(env.ambient_temp_k)
        q = AtmosphereModel.compute_dynamic_pressure(env.air_density_kg_m3, 50.0)

        assert env.ambient_pressure_pa > 0, f"Pressure non-positive at {alt}m"
        assert env.air_density_kg_m3 > 0, f"Density non-positive at {alt}m"
        assert env.ambient_temp_k > 0, f"Temperature non-positive at {alt}m"
        assert a > 0, f"Speed of sound non-positive at {alt}m"
        assert q >= 0, f"Dynamic pressure negative at {alt}m"
