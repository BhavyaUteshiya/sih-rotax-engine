"""
Physical Controls Isolation & Security Test Suite.
SIH26054 — Module 03 Digital Twin Core.
"""

from pathlib import Path

from fastapi.testclient import TestClient
from app.server import app


client = TestClient(app)


def test_valid_physical_controls_accepted():
    """Verifies that legitimate physical/environmental controls are accepted."""
    valid_payload = {
        "throttle_1": 85.0,
        "throttle_2": 85.0,
        "starter_1": True,
        "starter_2": True,
        "altitude_m": 1500.0,
        "temp_offset_c": 5.0,
        "humidity_pct": 50.0,
        "wind_m_s": 0.0,
        "flight_path_angle_deg": 2.0
    }
    response = client.post("/api/controls", json=valid_payload)
    assert response.status_code == 200
    res_json = response.json()
    assert res_json["controls"]["throttle_1"] == 85.0
    assert res_json["controls"]["altitude_m"] == 1500.0


def test_internal_output_controls_rejected():
    """Verifies that direct command attempts for internal outputs (map, rpm, egt, thrust, etc.) are rejected."""
    invalid_outputs = ["map", "rpm", "egt", "cht", "torque", "fuel_flow", "airflow", "thrust"]

    for internal_param in invalid_outputs:
        payload = {
            "throttle_1": 50.0,
            "throttle_2": 50.0,
            "starter_1": True,
            "starter_2": True,
            "altitude_m": 0.0,
            "temp_offset_c": 0.0,
            "humidity_pct": 0.0,
            "wind_m_s": 0.0,
            "flight_path_angle_deg": 0.0,
            internal_param: 100.0  # Forbidden extra field!
        }
        response = client.post("/api/controls", json=payload)
        assert response.status_code == 422, f"Attempting to directly write internal output '{internal_param}' must be rejected with 422"


def test_user_dashboard_html_contains_no_test_injection_panels():
    """Verifies that index.html contains zero user-facing test-mode fault injection controls."""
    html_path = Path("app/static/index.html")
    assert html_path.exists()
    content = html_path.read_text()

    forbidden_ui_strings = [
        "DIGITAL TWIN TEST MODE — CONTROLLED DEVIATION CONTROL",
        "INJECT TEST DEVIATION",
        "CLEAR TEST DEVIATION",
        "dt-test-param",
        "dt-inject-btn",
        "dt-clear-btn"
    ]

    for s in forbidden_ui_strings:
        assert s not in content, f"Dashboard UI must not contain user-facing test injection element '{s}'"


def test_internal_engine_parameters_are_emergent():
    """Verifies that internal parameters emerge strictly from physical stepping."""
    # Reset simulation
    client.post("/api/reset")

    # Set throttle 85%
    client.post("/api/controls", json={
        "throttle_1": 85.0,
        "throttle_2": 85.0,
        "starter_1": True,
        "starter_2": True,
        "altitude_m": 1000.0,
        "temp_offset_c": 0.0,
        "humidity_pct": 0.0,
        "wind_m_s": 0.0,
        "flight_path_angle_deg": 0.0
    })

    # Step simulation 20 times
    for _ in range(20):
        r_step = client.post("/api/run")
        assert r_step.status_code == 200

    r_state = client.get("/api/state")
    st = r_state.json()
    e1 = st["engines"]["1"]

    # Internal outputs calculated by physical model
    assert e1["rpm"] > 1000.0
    assert e1["map_bar"] > 1.0
    assert e1["egt_c"] > 100.0
    assert e1["fuel_kg_h"] > 1.0
    assert e1["thrust_n"] > 100.0
