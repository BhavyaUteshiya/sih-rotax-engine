from __future__ import annotations

import threading
from pathlib import Path
from typing import Dict, Any, Optional

from fastapi import FastAPI, Query
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel, ConfigDict, Field

from src.module02.integration.integration_runner import MasterIntegrationRunner
from src.module02.integration.can_transport import InMemoryTransport
from src.digital_twin.services.twin_engine import DigitalTwinEngine

ROOT = Path(__file__).resolve().parent
app = FastAPI(title="SIH26054 ROTAX 914 Simulator Dashboard", version="1.0.0")

_lock = threading.RLock()
runner = MasterIntegrationRunner(transport_override=InMemoryTransport(buffer_capacity=10000))
twin_engine = DigitalTwinEngine()

controls = {
    "throttle_1": 0.0,
    "throttle_2": 0.0,
    "starter_1": False,
    "starter_2": False,
    "altitude_m": 0.0,
    "temp_offset_c": 0.0,
    "humidity_pct": 0.0,
    "wind_m_s": 0.0,
    "flight_path_angle_deg": 0.0,
}
running = False


class ControlUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    throttle_1: float = Field(ge=0, le=100)
    throttle_2: float = Field(ge=0, le=100)
    starter_1: bool
    starter_2: bool
    altitude_m: float = Field(ge=0, le=20000)
    temp_offset_c: float = Field(ge=-100, le=100)
    humidity_pct: float = Field(ge=0, le=100)
    wind_m_s: Optional[float] = Field(default=None, ge=-150, le=150)
    flight_path_angle_deg: float = Field(ge=-30, le=30)


def _reset_locked() -> None:
    global runner, twin_engine, running
    runner = MasterIntegrationRunner(transport_override=InMemoryTransport(buffer_capacity=10000))
    twin_engine = DigitalTwinEngine()
    running = False


def _step_twin_locked() -> None:
    """Evaluates Digital Twin step for active simulation state."""
    s = runner.simulator.state
    prop1 = runner.simulator.propulsion_runner.state.propellers.get(1)
    prop2 = runner.simulator.propulsion_runner.state.propellers.get(2)
    t = runner.clock.simulation_time_sec
    seq = getattr(runner.scheduler, "records_published", 0)
    e1_st = s.engines[1].state.value if (hasattr(s.engines.get(1), "state") and hasattr(s.engines[1].state, "value")) else "RUNNING"
    e2_st = s.engines[2].state.value if (hasattr(s.engines.get(2), "state") and hasattr(s.engines[2].state, "value")) else "RUNNING"
    env_obj = s.environment

    ctx_common = {
        "throttle_1": controls["throttle_1"],
        "throttle_2": controls["throttle_2"],
        "starter_1": controls["starter_1"],
        "starter_2": controls["starter_2"],
        "engine_state_1": e1_st,
        "engine_state_2": e2_st,
        "altitude_m": controls["altitude_m"],
        "ambient_temp_c": controls["temp_offset_c"] + 15.0,
        "humidity_pct": controls["humidity_pct"],
        "wind_m_s": getattr(env_obj, "wind_speed_m_s", controls["wind_m_s"]),
        "flight_path_angle_deg": controls["flight_path_angle_deg"],
    }
    ctx_1 = {**ctx_common, "engine_index": 1, "throttle_pct": controls["throttle_1"], "starter": controls["starter_1"]}
    ctx_2 = {**ctx_common, "engine_index": 2, "throttle_pct": controls["throttle_2"], "starter": controls["starter_2"]}

    twin_engine.process_step(
        sim_state=s,
        pipeline=runner.pipeline,
        engine_index=1,
        timestamp=t,
        sequence_number=seq,
        operating_context=ctx_1,
        propeller_state=prop1
    )
    twin_engine.process_step(
        sim_state=s,
        pipeline=runner.pipeline,
        engine_index=2,
        timestamp=t,
        sequence_number=seq,
        operating_context=ctx_2,
        propeller_state=prop2
    )


def _snapshot() -> Dict[str, Any]:
    s = runner.simulator.state
    e1, e2 = s.engines[1], s.engines[2]
    t1, t2 = s.thermodynamics[1], s.thermodynamics[2]
    th1, th2 = s.thermals[1], s.thermals[2]
    l1, l2 = s.lubrication[1], s.lubrication[2]
    p1, p2 = runner.simulator.propulsion_runner.state.propellers[1], runner.simulator.propulsion_runner.state.propellers[2]
    a = s.aircraft
    env = s.environment
    elec = s.electrical
    bat = s.battery
    metrics = runner.get_metrics()

    _step_twin_locked()
    twin_state_1 = twin_engine.get_state(1)
    twin_state_2 = twin_engine.get_state(2)
    warnings = twin_engine.get_warnings()

    return {
        "running": running,
        "simulation_time_s": runner.clock.simulation_time_sec,
        "controls": controls,
        "environment": {
            "altitude_m": env.altitude_m, "temperature_c": env.ambient_temp_k - 273.15,
            "pressure_kpa": env.ambient_pressure_pa / 1000, "density_kg_m3": env.air_density_kg_m3,
            "humidity_pct": env.relative_humidity_percent, "wind_m_s": env.wind_speed_m_s,
        },
        "aircraft": {
            "altitude_m": a.altitude_m, "speed_m_s": a.velocity_m_s, "vertical_speed_m_s": a.velocity_m_s * __import__("math").sin(a.flight_path_angle_rad),
            "mass_kg": a.gross_mass_kg, "thrust_n": a.total_thrust_n, "drag_n": a.drag_force_n,
            "phase": s.flight.flight_phase.value,
        },
        "battery": {"soc_pct": bat.battery_soc * 100, "voltage_v": bat.battery_voltage_v, "current_a": bat.battery_current_a},
        "electrical": {"bus_v": elec.bus_voltage_v, "load_w": elec.electrical_load_w, "alternator_w": elec.alternator_power_w, "starter_w": elec.starter_power_w},
        "engines": {
            "1": _engine_snapshot(e1, t1, th1, l1, p1),
            "2": _engine_snapshot(e2, t2, th2, l2, p2),
        },
        "integration": metrics,
        "digital_twin": {
            "1": twin_state_1,
            "2": twin_state_2,
        },
        "digital_twin_warnings": warnings,
    }


def _engine_snapshot(e, t, thermal, lub, prop):
    return {
        "rpm": e.engine_rpm, "throttle_pct": e.throttle_percent, "state": e.operating_state.value,
        "map_bar": e.manifold_pressure_pa / 100000, "boost_bar": max(0, e.manifold_pressure_pa - runner.simulator.state.environment.ambient_pressure_pa) / 100000,
        "airflow_kg_h": e.air_mass_flow_kg_s * 3600, "fuel_kg_h": e.fuel_mass_flow_kg_s * 3600,
        "afr": e.air_fuel_ratio, "injection_deg": e.injection_timing_deg_btdc,
        "egt_c": t.egt_k - 273.15, "cht_c": t.cht_k - 273.15, "coolant_c": t.coolant_temp_k - 273.15,
        "oil_c": t.oil_temp_k - 273.15, "oil_pressure_bar": lub.oil_pressure_pa / 100000,
        "eta_comb_pct": t.combustion_efficiency * 100, "derate_pct": t.thermal_derating_factor * 100,
        "turbo_rpm": e.turbocharger.turbo_speed_rpm, "thrust_n": prop.thrust_n, "prop_rpm": prop.propeller_rpm,
        "vibration_m_s2": runner.simulator.propulsion_runner.state.vibration[e.engine_index].vibration_rms_m_s2 if e.engine_index in runner.simulator.propulsion_runner.state.vibration else 0,
        "wear_pct": runner.simulator.propulsion_runner.state.degradation[e.engine_index].bearing_wear * 100 if e.engine_index in runner.simulator.propulsion_runner.state.degradation else 0,
    }


@app.get("/")
def index():
    return FileResponse(ROOT / "static" / "index.html")


@app.get("/api/state")
def state():
    with _lock:
        return JSONResponse(_snapshot())


@app.post("/api/controls")
def update_controls(update: ControlUpdate):
    with _lock:
        controls.update({k: v for k, v in update.model_dump().items() if v is not None})
        runner.simulator.set_environment_inputs(
            altitude_m=controls["altitude_m"],
            temp_offset_k=controls["temp_offset_c"],
            relative_humidity_percent=controls["humidity_pct"],
            wind_speed_m_s=controls.get("wind_m_s", 0.0),
        )
        return JSONResponse(_snapshot())


@app.post("/api/export")
def export():
    with _lock:
        runner._collect_normalized_records(scenario_id="dashboard_run")
        csv_path, jsonl_path = runner.export_datasets()
        return JSONResponse({"csv": csv_path, "jsonl": jsonl_path, "records": len(runner.recorded_dataset_records)})


@app.post("/api/reset")
def reset():
    with _lock:
        _reset_locked()
        return JSONResponse(_snapshot())


@app.post("/api/run")
def run_step():
    with _lock:
        runner.simulator.set_environment_inputs(
            altitude_m=controls["altitude_m"],
            temp_offset_k=controls["temp_offset_c"],
            relative_humidity_percent=controls["humidity_pct"],
            wind_speed_m_s=controls["wind_m_s"],
        )
        for _ in range(5):
            runner.simulator.step_thermodynamic_cycle(
                throttles={1: controls["throttle_1"], 2: controls["throttle_2"]},
                starter_commands={1: controls["starter_1"], 2: controls["starter_2"]},
                flight_path_angle_rad=controls["flight_path_angle_deg"] * 3.141592653589793 / 180.0,
            )
            runner.scheduler.step_physics_and_publish_telemetry(
                state=runner.simulator.state,
                simulation_time_sec=runner.clock.simulation_time_sec,
            )
            frames = runner.transport.receive_frames(max_frames=100)
            runner.bridge.process_batch(frames)
        return JSONResponse(_snapshot())


# ==============================================================================
# DIGITAL TWIN PHASE 1 API ENDPOINTS
# ==============================================================================

@app.get("/api/digital-twin/state")
def get_digital_twin_state(engine_index: int = Query(default=1, ge=1, le=2)):
    with _lock:
        return JSONResponse(twin_engine.get_state(engine_index))


@app.get("/api/digital-twin/status")
def get_digital_twin_status(engine_index: int = Query(default=1, ge=1, le=2)):
    with _lock:
        return JSONResponse(twin_engine.get_status(engine_index))


@app.get("/api/digital-twin/residuals")
def get_digital_twin_residuals(engine_index: int = Query(default=1, ge=1, le=2)):
    with _lock:
        return JSONResponse(twin_engine.get_residuals(engine_index))


@app.get("/api/digital-twin/causal")
def get_digital_twin_causal(engine_index: int = Query(default=1, ge=1, le=2)):
    with _lock:
        return JSONResponse(twin_engine.get_causal_analysis(engine_index))


@app.get("/api/digital-twin/warnings")
def get_digital_twin_warnings():
    with _lock:
        return JSONResponse(twin_engine.get_warnings())



