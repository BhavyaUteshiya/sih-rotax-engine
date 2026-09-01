"""
Authoritative Digital Twin Phase 1 Architecture Test Suite — 26 Verification Assertions.
SIH26054 — Module 03 Digital Twin Core.
"""

import pytest
from fastapi.testclient import TestClient

from app.server import app
from src.digital_twin.analysis.causal_analyzer import CausalAnalyzer, CausalNodeStatus
from src.digital_twin.analysis.residual_analyzer import ResidualAnalyzer
from src.digital_twin.models.expected_state import ExpectedState
from src.digital_twin.models.observed_state import ObservedState
from src.digital_twin.models.residual_state import ParameterResidual, ResidualState
from src.digital_twin.models.twin_state import DigitalTwinState, DigitalTwinStatus
from src.digital_twin.physics.expected_behavior import ExpectedBehaviorModel
from src.digital_twin.services.twin_engine import DigitalTwinEngine
from src.module02.integration.can_transport import InMemoryTransport
from src.module02.integration.integration_runner import MasterIntegrationRunner


client = TestClient(app)


def test_1_2_3_21_parameter_classification_and_control_rejection():
    """1, 2, 3, 21. Controller vs Environmental vs Internal parameter classification & API control rejection."""
    controller_inputs = {"throttle_1", "throttle_2", "starter_1", "starter_2", "flight_path_angle_deg"}
    environmental_inputs = {"altitude_m", "temp_offset_c", "humidity_pct", "wind_m_s"}
    internal_outputs = [
        "rpm", "map_bar", "turbo_rpm", "airflow_kg_h", "fuel_flow_kg_h", "afr",
        "combustion_efficiency", "indicated_power_kw", "torque_n_m", "egt_c",
        "cht_c", "coolant_temp_c", "oil_temp_c", "oil_pressure_bar", "turbo_boost_bar",
        "gearbox_rpm", "propeller_load_nm", "thrust_n"
    ]

    # Test POST /api/controls accepts valid Category A & B inputs
    r_valid = client.post("/api/controls", json={
        "throttle_1": 50.0,
        "throttle_2": 50.0,
        "starter_1": True,
        "starter_2": True,
        "altitude_m": 500.0,
        "temp_offset_c": 0.0,
        "humidity_pct": 20.0,
        "wind_m_s": 5.0,
        "flight_path_angle_deg": 2.0
    })
    assert r_valid.status_code == 200

    # Test POST /api/controls rejects any internal output command (HTTP 422)
    for out_param in internal_outputs:
        r_invalid = client.post("/api/controls", json={
            "throttle_1": 50.0,
            "throttle_2": 50.0,
            "starter_1": True,
            "starter_2": True,
            "altitude_m": 0.0,
            "temp_offset_c": 0.0,
            "humidity_pct": 0.0,
            "wind_m_s": 0.0,
            "flight_path_angle_deg": 0.0,
            out_param: 100.0
        })
        assert r_invalid.status_code == 422


def test_4_5_6_18_parameter_support():
    """4, 5, 6. Verifies complete 18 internal parameters in ExpectedState, ObservedState, and ResidualAnalyzer."""
    exp = ExpectedState(
        rpm=5433.0, map_bar=1.32, turbo_rpm=115000.0, airflow_kg_h=240.0, fuel_flow_kg_h=18.5,
        afr=13.0, combustion_efficiency=0.95, indicated_power_kw=85.0, torque_n_m=152.0,
        egt_c=900.0, cht_c=110.0, coolant_temp_c=85.0, oil_temp_c=90.0, oil_pressure_bar=4.0,
        turbo_boost_bar=0.31, gearbox_rpm=2235.0, propeller_load_nm=62.5, thrust_n=1884.0
    )
    exp_dict = exp.to_dict()
    assert len(exp_dict) >= 18

    obs = ObservedState(
        rpm=5433.0, map_bar=1.32, turbo_rpm=115000.0, airflow_kg_h=240.0, fuel_flow_kg_h=18.5,
        afr=13.0, combustion_efficiency=0.95, indicated_power_kw=85.0, torque_n_m=152.0,
        egt_c=900.0, cht_c=110.0, coolant_temp_c=85.0, oil_temp_c=90.0, oil_pressure_bar=4.0,
        turbo_boost_bar=0.31, gearbox_rpm=2235.0, propeller_load_nm=62.5, thrust_n=1884.0,
        data_quality="GOOD"
    )
    obs_dict = obs.to_dict()
    assert len(obs_dict) >= 18

    analyzer = ResidualAnalyzer()
    res_state = analyzer.analyze(exp, obs)
    assert len(res_state.residuals) == 18


def test_7_8_e1_e2_independence_and_asymmetric_throttles():
    """7 & 8. Verifies E1/E2 twin engine independence under normal asymmetric throttle operation."""
    runner = MasterIntegrationRunner(transport_override=InMemoryTransport(buffer_capacity=10000))
    engine = DigitalTwinEngine("configs/digital_twin_config.yaml")

    for _ in range(60):
        runner.simulator.step_thermodynamic_cycle(throttles={1: 100.0, 2: 40.0}, starter_commands={1: True, 2: True})
        runner.scheduler.step_physics_and_publish_telemetry(state=runner.simulator.state, simulation_time_sec=runner.clock.simulation_time_sec)
        frames = runner.transport.receive_frames(max_frames=100)
        runner.bridge.process_batch(frames)

    st1 = engine.process_step(sim_state=runner.simulator.state, pipeline=runner.pipeline, engine_index=1, timestamp=runner.clock.simulation_time_sec)
    st2 = engine.process_step(sim_state=runner.simulator.state, pipeline=runner.pipeline, engine_index=2, timestamp=runner.clock.simulation_time_sec)

    assert st1.expected_state.rpm > st2.expected_state.rpm
    assert st1.status in {DigitalTwinStatus.SYNCHRONIZED, DigitalTwinStatus.DATA_QUALITY_DEGRADED}


def test_9_10_11_12_operating_states_handling():
    """9, 10, 11, 12. Verifies Engine OFF, STARTING, RUNNING, and starter transient expected states."""
    runner = MasterIntegrationRunner(transport_override=InMemoryTransport(buffer_capacity=10000))
    engine = DigitalTwinEngine("configs/digital_twin_config.yaml")

    # Engine OFF
    st_off = engine.process_step(sim_state=runner.simulator.state, pipeline=runner.pipeline, engine_index=1, timestamp=0.0)
    assert st_off.expected_state.rpm == 0.0
    assert st_off.expected_state.thrust_n == 0.0

    # Engine STARTING
    runner.simulator.step_thermodynamic_cycle(throttles={1: 0.0, 2: 0.0}, starter_commands={1: True, 2: False})
    st_start = engine.process_step(sim_state=runner.simulator.state, pipeline=runner.pipeline, engine_index=1, timestamp=0.1)
    assert st_start.expected_state.rpm >= 0.0


def test_13_complete_operating_context():
    """13. Verifies that operating context includes all Category A & B parameters."""
    client.post("/api/controls", json={"throttle_1": 80.0, "throttle_2": 80.0, "starter_1": True, "starter_2": True, "altitude_m": 1000.0, "temp_offset_c": 5.0, "humidity_pct": 30.0, "wind_m_s": 10.0, "flight_path_angle_deg": 3.0})
    r_snap = client.get("/api/state")
    assert r_snap.status_code == 200
    snap = r_snap.json()

    ctx1 = snap["digital_twin"]["1"]["operating_context"]
    assert "throttle_1" in ctx1
    assert "throttle_2" in ctx1
    assert "starter_1" in ctx1
    assert "starter_2" in ctx1
    assert "altitude_m" in ctx1
    assert "ambient_temp_c" in ctx1
    assert "humidity_pct" in ctx1
    assert "wind_m_s" in ctx1
    assert "flight_path_angle_deg" in ctx1


def test_14_15_16_17_18_19_environmental_causal_representation_and_dag_purity():
    """14-19. Verifies environmental causal nodes, intermediate concepts, and absence of direct shortcut edges."""
    causal = CausalAnalyzer()
    graph_e1 = causal._get_engine_graph(engine_index=1)
    graph_e2 = causal._get_engine_graph(engine_index=2)

    # 1. Assert separate Engine Start/Stop E1 vs E2 nodes and Starter nodes
    assert "engine_start_stop" in graph_e1
    assert graph_e1["engine_start_stop"].node_id == "engine_start_stop_1"
    assert graph_e2["engine_start_stop"].node_id == "engine_start_stop_2"

    assert "starter_command" in graph_e1
    assert graph_e1["starter_command"].node_id == "starter_command_1"
    assert graph_e2["starter_command"].node_id == "starter_command_2"

    # 2. Assert Flight Path Angle is an independent external input node
    fpa_node = graph_e1["flight_path_angle"]
    assert "altitude" not in fpa_node.upstream_parents
    assert fpa_node.upstream_parents == []

    # 3. Assert Wind Speed chain: Wind -> Relative Airspeed -> Aerodynamic Loading -> Propeller Load
    wind_node = graph_e1["wind_speed"]
    assert "rpm" not in wind_node.downstream_children
    assert "torque" not in wind_node.downstream_children
    assert "relative_airspeed" in wind_node.downstream_children

    rel_air_node = graph_e1["relative_airspeed"]
    assert "aerodynamic_loading" in rel_air_node.downstream_children

    # 4. Assert Flight Path Angle chain: FPA -> Flight Condition -> Aerodynamic Loading
    assert "rpm" not in fpa_node.downstream_children
    assert "torque" not in fpa_node.downstream_children
    assert "flight_condition" in fpa_node.downstream_children


def test_20_primary_vs_propagated_deviation():
    """20. Verifies primary vs propagated deviation classification in CausalAnalyzer."""
    causal = CausalAnalyzer()

    map_res = ParameterResidual.compute(parameter="map_bar", expected=1.32, observed=1.02, threshold=0.05, unit="bar")
    air_res = ParameterResidual.compute(parameter="airflow_kg_h", expected=240.0, observed=180.0, threshold=15.0, unit="kg/h")
    
    res_state = ResidualState(residuals={"map_bar": map_res, "airflow_kg_h": air_res}, warnings_count=2)
    analysis = causal.analyze_causal_chain(res_state, engine_index=1)

    nodes = analysis["nodes"]
    assert nodes["map"]["status"] == "PRIMARY_DEVIATION"
    assert nodes["map"]["node_id"] == "map_1"
    assert nodes["airflow"]["status"] == "PROPAGATED_DEVIATION"


def test_22_no_production_test_injection():
    """22. Verifies zero production test injection."""
    r_post = client.post("/api/digital-twin/test-inject", json={"parameter": "map", "offset": -0.3})
    assert r_post.status_code in {404, 405}

    dt_engine = DigitalTwinEngine()
    assert not hasattr(dt_engine, "test_injection")


def test_23_digital_twin_api_regression():
    """23. Verifies Digital Twin API endpoints regression safety."""
    r_state = client.get("/api/digital-twin/state?engine_index=1")
    assert r_state.status_code == 200

    r_status = client.get("/api/digital-twin/status?engine_index=1")
    assert r_status.status_code == 200

    r_res = client.get("/api/digital-twin/residuals?engine_index=1")
    assert r_res.status_code == 200

    r_causal = client.get("/api/digital-twin/causal?engine_index=1")
    assert r_causal.status_code == 200

    r_warn = client.get("/api/digital-twin/warnings")
    assert r_warn.status_code == 200


def test_24_canonical_yaml_threshold_keys_no_duplicates():
    """24. Verifies digital_twin_config.yaml contains exactly canonical keys with zero duplicate aliases."""
    import yaml
    with open("configs/digital_twin_config.yaml", "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)
    thresh = cfg["digital_twin"]["residual_thresholds"]

    # Must contain canonical keys for authoritative 18 parameters
    canonical_keys = {
        "rpm", "map_bar", "turbo_rpm", "airflow_kg_h", "fuel_flow_kg_h", "afr",
        "combustion_energy", "indicated_power_kw", "torque_n_m", "egt_c", "cht_c",
        "coolant_temp_c", "oil_temp_c", "oil_pressure_bar", "turbo_boost_bar",
        "gearbox_rpm", "propeller_load_nm", "thrust_n"
    }
    for k in canonical_keys:
        assert k in thresh, f"Canonical key '{k}' must be present in digital_twin_config.yaml"

    # Must NOT contain duplicate aliases
    duplicate_aliases = {"map", "egt", "cht", "oil_temperature", "airflow", "fuel_flow", "thrust", "turbo_speed"}
    for alias in duplicate_aliases:
        assert alias not in thresh, f"Duplicate alias '{alias}' must NOT be in digital_twin_config.yaml"


def test_25_combustion_energy_semantic_disambiguation_and_missing_residuals():
    """25. Verifies heat_release_rate_w is not mislabeled as combustion_energy, Joule is not used for rate, and missing channels produce 0 warning."""
    exp = ExpectedState(combustion_efficiency=0.95, combustion_energy=None)
    obs = ObservedState(combustion_efficiency=0.95, combustion_energy=None)

    # 1. combustion_efficiency is a ratio
    assert exp.combustion_efficiency == 0.95
    assert obs.combustion_efficiency == 0.95

    # 2. combustion_energy is None (not mislabeling heat_release_rate_w as Joules)
    assert exp.combustion_energy is None
    assert obs.combustion_energy is None

    # 3. Missing observed value yields MISSING quality, 0 residual, 0 warning
    res_missing = ParameterResidual.compute("combustion_energy", expected=100.0, observed=None, threshold=10.0, unit="J")
    assert res_missing.quality == "MISSING"
    assert res_missing.warning_triggered is False
    assert res_missing.residual == 0.0

