"""
Digital Twin Phase 1 Comprehensive Test Suite.
SIH26054 — Module 03 Digital Twin Core.
"""

import math
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
from src.module02.config.config_loader import ConfigLoader
from src.module02.simulation.thermodynamic_engine_runner import ThermodynamicEngineRunner


client = TestClient(app)


def test_observed_state_creation():
    """1. Test ObservedState instantiation and serialization."""
    obs = ObservedState(timestamp=10.0, sequence_number=100, engine_id="engine_1", rpm=5200.0, data_quality="GOOD")
    assert obs.rpm == 5200.0
    d = obs.to_dict()
    assert d["rpm"] == 5200.0
    assert d["data_quality"] == "GOOD"


def test_expected_state_creation():
    """2. Test ExpectedState instantiation and serialization."""
    exp = ExpectedState(timestamp=10.0, sequence_number=100, engine_id="engine_1", rpm=5200.0)
    assert exp.rpm == 5200.0
    d = exp.to_dict()
    assert d["rpm"] == 5200.0
    assert d["model_confidence"] == 1.0


def test_residual_calculation_zero_positive_negative():
    """3-6. Test ParameterResidual computation for zero, positive, and negative residuals."""
    # Zero residual
    r_zero = ParameterResidual.compute("rpm", expected=5000.0, observed=5000.0, threshold=100.0)
    assert r_zero.residual == 0.0
    assert r_zero.relative_error == 0.0
    assert r_zero.warning_triggered is False

    # Positive residual
    r_pos = ParameterResidual.compute("rpm", expected=5000.0, observed=5150.0, threshold=100.0)
    assert r_pos.residual == 150.0
    assert r_pos.relative_error == 0.03
    assert r_pos.warning_triggered is True

    # Negative residual
    r_neg = ParameterResidual.compute("rpm", expected=5000.0, observed=4850.0, threshold=100.0)
    assert r_neg.residual == -150.0
    assert r_neg.relative_error == -0.03
    assert r_neg.warning_triggered is True


def test_residual_calculation_edge_cases():
    """8-12. Test zero expected value, NaN, Inf, missing telemetry handling."""
    # Zero expected value
    r_zero_exp = ParameterResidual.compute("rpm", expected=0.0, observed=50.0)
    assert r_zero_exp.residual == 50.0
    assert r_zero_exp.relative_error == 0.0
    assert r_zero_exp.quality == "VALID"

    # NaN handling
    r_nan = ParameterResidual.compute("rpm", expected=5000.0, observed=float("nan"))
    assert r_nan.quality == "INVALID_NAN"
    assert r_nan.warning_triggered is False

    # Inf handling
    r_inf = ParameterResidual.compute("rpm", expected=float("inf"), observed=5000.0)
    assert r_inf.quality == "INVALID_INF"
    assert r_inf.warning_triggered is False

    # Missing telemetry handling
    r_missing = ParameterResidual.compute("rpm", expected=None, observed=5000.0)
    assert r_missing.quality == "MISSING"
    assert r_missing.warning_triggered is False


def test_residual_analyzer_thresholds_from_yaml():
    """18. Verify threshold loading from YAML configuration."""
    analyzer = ResidualAnalyzer("configs/digital_twin_config.yaml")
    assert analyzer.thresholds["rpm"] == 100.0
    assert analyzer.thresholds["egt_c"] == 25.0

    exp = ExpectedState(rpm=5000.0, egt_c=700.0)
    obs = ObservedState(rpm=5120.0, egt_c=740.0)  # Both exceed threshold!
    res_state = analyzer.analyze(exp, obs)

    assert res_state.residuals["rpm"].warning_triggered is True
    assert res_state.residuals["egt_c"].warning_triggered is True
    assert res_state.warnings_count >= 2


def test_causal_analyzer_graph():
    """14-17. Test causal dependency graph analysis and deviation propagation."""
    causal = CausalAnalyzer()
    res_state = ResidualState()

    # Case 1: All normal
    res_state.add_residual(ParameterResidual.compute("airflow_kg_h", expected=100.0, observed=100.0, threshold=15.0))
    res_state.add_residual(ParameterResidual.compute("rpm", expected=5000.0, observed=5000.0, threshold=100.0))
    analysis_norm = causal.analyze_causal_chain(res_state)
    assert len(analysis_norm["primary_deviations"]) == 0
    assert len(analysis_norm["propagated_deviations"]) == 0

    # Case 2: Isolated Primary Deviation at MAP
    res_state.add_residual(ParameterResidual.compute("map_bar", expected=1.0, observed=1.2, threshold=0.05))
    analysis_map = causal.analyze_causal_chain(res_state, engine_index=1)
    assert any("map" in p for p in analysis_map["primary_deviations"])
    assert len(analysis_map["propagated_deviations"]) == 0

    # Case 3: Propagated Deviation from MAP to Airflow and RPM
    res_state.add_residual(ParameterResidual.compute("airflow_kg_h", expected=100.0, observed=130.0, threshold=15.0))
    res_state.add_residual(ParameterResidual.compute("rpm", expected=5000.0, observed=5300.0, threshold=100.0))
    analysis_prop = causal.analyze_causal_chain(res_state, engine_index=1)
    assert any("map" in p for p in analysis_prop["primary_deviations"])
    assert any("airflow" in p for p in analysis_prop["propagated_deviations"])


def test_digital_twin_engine_service_orchestration():
    """21-22. Test DigitalTwinEngine orchestration and state serialization."""
    sim = ThermodynamicEngineRunner()
    dt_engine = DigitalTwinEngine("configs/digital_twin_config.yaml")

    state = dt_engine.process_step(
        sim_state=sim.state,
        engine_index=1,
        timestamp=1.0,
        sequence_number=1,
        operating_context={"throttle_pct": 50.0}
    )

    assert state.engine_id == "engine_1"
    assert state.status in {DigitalTwinStatus.SYNCHRONIZED, DigitalTwinStatus.DEVIATION_DETECTED, DigitalTwinStatus.INSUFFICIENT_DATA}
    d = state.to_dict()
    assert "observed_state" in d
    assert "expected_state" in d
    assert "residual_state" in d
    assert "causal_chain_status" in d


def test_digital_twin_api_endpoints():
    """23. Test new Digital Twin API endpoints."""
    # Ensure server has run at least one step
    client.post("/api/run")

    r_state = client.get("/api/digital-twin/state?engine_index=1")
    assert r_state.status_code == 200
    assert r_state.json()["engine_id"] == "engine_1"

    r_status = client.get("/api/digital-twin/status?engine_index=1")
    assert r_status.status_code == 200
    assert "status" in r_status.json()

    r_res = client.get("/api/digital-twin/residuals?engine_index=1")
    assert r_res.status_code == 200
    assert "residuals" in r_res.json()

    r_causal = client.get("/api/digital-twin/causal?engine_index=1")
    assert r_causal.status_code == 200
    assert "summary" in r_causal.json()

    r_warn = client.get("/api/digital-twin/warnings")
    assert r_warn.status_code == 200
    assert isinstance(r_warn.json(), list)


def test_existing_endpoints_preserved():
    """26. Test existing endpoints remain fully functional."""
    r_home = client.get("/")
    assert r_home.status_code == 200
    assert "ROTAX 914" in r_home.text

    r_state = client.get("/api/state")
    assert r_state.status_code == 200
    data = r_state.json()
    assert "engines" in data
    assert "digital_twin" in data  # extended cleanly

    r_ctrl = client.post("/api/controls", json={
        "throttle_1": 50, "throttle_2": 25, "starter_1": True, "starter_2": True,
        "altitude_m": 1000, "temp_offset_c": 5, "humidity_pct": 20,
        "wind_m_s": 0, "flight_path_angle_deg": 1
    })
    assert r_ctrl.status_code == 200


def test_rotax_914_remains_active_engine():
    """29-30. Verify Rotax 914 engine profile remains active."""
    cfg = ConfigLoader.load_engine_config()
    assert cfg["metadata"]["profile_id"] == "ROTAX_914_UL_115HP"
    assert cfg["metadata"]["profile_id"] != "TAPAS_BH201_INDIGENOUS_180HP_DIESEL"
