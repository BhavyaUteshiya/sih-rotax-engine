"""
Phase 1 Enums and Core State Dataclass Validation Tests.
SIH26054 — Module 02 Engine Simulator.
"""

import pytest
from src.module02.models.enums import (
    FaultScenario,
    FlightPhase,
    ParameterCategory,
    PhysicalOrigin,
    ProcessingContext,
    ProvenanceClassification,
    StateCategory,
)
from src.module02.models.states import (
    CylinderState,
    ElectricalState,
    EngineState,
    EnvironmentState,
    FlightState,
    LubricationState,
    SimulationState,
    TelemetryState,
)


def test_enum_completeness():
    """Verify presence of all required enum members."""
    # Flight Phases
    phases = [p.value for p in FlightPhase]
    expected_phases = ["GROUND", "START", "TAXI", "TAKEOFF", "CLIMB", "CRUISE", "DESCENT", "LANDING"]
    for ep in expected_phases:
        assert ep in phases

    # Fault Scenarios
    faults = [f.value for f in FaultScenario]
    expected_faults = [
        "NONE", "MISFIRE", "INJECTOR_ABNORMALITY", "LUBRICATION_ISSUE",
        "SENSOR_DRIFT", "SENSOR_FAILURE", "COMBUSTION_INSTABILITY",
        "OVERHEATING_TREND", "ABNORMAL_VIBRATION", "CODING_DEGRADATION"
    ]
    for ef in expected_faults:
        assert ef in faults

    # Integration Boundaries
    assert PhysicalOrigin.SIMULATOR.value == "SIMULATOR"
    assert StateCategory.SIMULATED.value == "SIMULATED"
    assert ProcessingContext.SYNTHETIC_GENERATION.value == "SYNTHETIC_GENERATION"

    # Provenance Classifications
    provs = [pr.value for pr in ProvenanceClassification]
    assert "OFFICIAL" in provs
    assert "ESTIMATED" in provs


def test_simulation_state_instantiation():
    """Verify state dataclass default instantiations for twin-engine support."""
    state = SimulationState()
    state.engines[1] = EngineState(engine_index=1, engine_id="engine_1")
    state.engines[2] = EngineState(engine_index=2, engine_id="engine_2")

    assert state.environment.altitude_m == 0.0
    assert state.environment.ambient_pressure_pa == 101325.0
    assert state.engines[1].engine_rpm == 0.0
    assert len(state.engines) == 2
    assert state.electrical.battery_voltage_v == 28.0


def test_telemetry_state_provenance_defaults():
    """Verify TelemetryState carries required synthetic provenance flags."""
    telem = TelemetryState(
        timestamp_utc=1787733200.0,
        simulation_time_sec=0.0,
        mission_elapsed_sec=0.0,
        mission_phase="GROUND",
        altitude_m=0.0,
        ambient_temp_k=288.15,
        ambient_pressure_pa=101325.0,
        air_density_kg_m3=1.225,
        relative_humidity_percent=0.0,
        wind_speed_m_s=0.0,
        airspeed_m_s=0.0,
        aircraft_mass_kg=2800.0,
        throttle_percent=0.0,
        engine_rpm=0.0,
        engine_rpm_rad_per_sec=0.0,
        manifold_pressure_pa=101325.0,
        cht_cyl1_degc=15.0,
        cht_cyl2_degc=15.0,
        cht_cyl3_degc=15.0,
        cht_cyl4_degc=15.0,
        egt_cyl1_degc=15.0,
        egt_cyl2_degc=15.0,
        egt_cyl3_degc=15.0,
        egt_cyl4_degc=15.0,
        oil_pressure_bar=0.0,
        oil_pressure_pa=0.0,
        oil_temperature_degc=15.0,
        oil_temperature_k=288.15,
        fuel_flow_kg_h=0.0,
        fuel_flow_kg_s=0.0,
        air_fuel_ratio=14.5,
        vibration_rms_m_s2=5.0,
        battery_voltage_v=28.0,
        alternator_current_a=0.0,
        injection_timing_deg_btdc=18.0,
        brake_thermal_efficiency_percent=0.0,
        degradation_bearing=0.0,
        degradation_injector=0.0,
        degradation_ring=0.0,
        simulation_id="sim_0001",
        scenario_id="NONE",
        random_seed=42,
        fault_scenario_id="NONE",
    )

    assert telem.physical_origin == "SIMULATOR"
    assert telem.state_category == "SIMULATED"
    assert telem.processing_context == "SYNTHETIC_GENERATION"
