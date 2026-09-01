"""
Causal Analyzer — Evaluates Physical Causal Chains and Deviation Propagation.
SIH26054 — Module 03 Digital Twin Core.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

from src.digital_twin.models.residual_state import ResidualState


class CausalNodeStatus(str, Enum):
    NORMAL = "NORMAL"
    PRIMARY_DEVIATION = "PRIMARY_DEVIATION"
    PROPAGATED_DEVIATION = "PROPAGATED_DEVIATION"
    UNTESTED = "UNTESTED"


@dataclass
class CausalChainNode:
    """
    Represents a single node in the physical causal dependency DAG.
    """
    node_id: str
    name: str
    param_key: str
    upstream_parents: List[str] = field(default_factory=list)
    downstream_children: List[str] = field(default_factory=list)
    status: CausalNodeStatus = CausalNodeStatus.NORMAL
    residual_val: float = 0.0


class CausalAnalyzer:
    """
    Analyzes physical parameter deviations across authoritative propulsion and environmental causal chains.
    MANDATE: Performs CAUSAL DEVIATION ANALYSIS. Preserves E1 and E2 engine identity independently.
    Distinguishes Engine Start/Stop from Starter Command. Supports intermediate physics DAG concepts.
    Does NOT claim automated fault diagnosis or failure prediction.
    """

    def _get_engine_graph(self, engine_index: int = 1) -> Dict[str, CausalChainNode]:
        suffix = f" E{engine_index}"
        e_tag = f"_{engine_index}"
        th_key = f"throttle_{engine_index}"

        return {
            # Category A & B: Controller & Environmental Inputs (Upstream Context Nodes)
            "throttle": CausalChainNode(f"throttle{e_tag}", f"Throttle{suffix}", th_key, [], ["map", "turbo_speed"]),
            "engine_start_stop": CausalChainNode(f"engine_start_stop{e_tag}", f"Engine Start/Stop{suffix}", f"engine_state_{engine_index}", [], ["combustion", "fuel_flow", "rpm"]),
            "starter_command": CausalChainNode(f"starter_command{e_tag}", f"Starter Command{suffix}", f"starter_{engine_index}", [], ["rpm", "combustion"]),
            "altitude": CausalChainNode("altitude", "Altitude", "altitude_m", [], ["map", "airflow"]),
            "ambient_temperature": CausalChainNode("ambient_temperature", "Ambient Temp", "ambient_temp_c", [], ["airflow", "cht", "coolant_temp", "oil_temp"]),
            "wind_speed": CausalChainNode("wind_speed", "Wind Speed", "wind_m_s", [], ["relative_airspeed"]),
            "humidity": CausalChainNode("humidity", "Humidity", "humidity_pct", [], ["airflow", "afr"]),
            "flight_path_angle": CausalChainNode("flight_path_angle", "Flight Path Angle", "flight_path_angle_deg", [], ["flight_condition"]),

            # Intermediate Physical Concepts (Causal DAG Intermediate Nodes)
            "relative_airspeed": CausalChainNode("relative_airspeed", "Relative Airspeed", "airspeed_m_s", ["wind_speed"], ["aerodynamic_loading"]),
            "flight_condition": CausalChainNode("flight_condition", "Flight Condition", "flight_path_angle_deg", ["flight_path_angle"], ["aerodynamic_loading"]),
            "aerodynamic_loading": CausalChainNode(f"aerodynamic_loading{e_tag}", f"Aerodynamic Loading{suffix}", "aerodynamic_loading", ["relative_airspeed", "flight_condition"], ["propeller_load"]),
            "engine_operating_point": CausalChainNode(f"engine_operating_point{e_tag}", f"Engine Operating Point{suffix}", "engine_operating_point", ["propeller_load"], ["torque", "rpm", "thrust"]),

            # Category C: Internal / Emergent Parameters (Forward Physics DAG per engine)
            "map": CausalChainNode(f"map{e_tag}", f"MAP{suffix}", "map_bar", ["throttle", "altitude", "ambient_temperature"], ["turbo_boost", "turbo_speed", "airflow"]),
            "turbo_boost": CausalChainNode(f"turbo_boost{e_tag}", f"Turbo Boost{suffix}", "turbo_boost_bar", ["map"], []),
            "turbo_speed": CausalChainNode(f"turbo_speed{e_tag}", f"Turbo Speed{suffix}", "turbo_rpm", ["map", "throttle"], []),
            "airflow": CausalChainNode(f"airflow{e_tag}", f"Airflow{suffix}", "airflow_kg_h", ["map", "altitude", "ambient_temperature", "humidity"], ["fuel_flow", "afr"]),
            "fuel_flow": CausalChainNode(f"fuel_flow{e_tag}", f"Fuel Flow{suffix}", "fuel_flow_kg_h", ["airflow", "engine_start_stop"], ["afr", "combustion"]),
            "afr": CausalChainNode(f"afr{e_tag}", f"AFR{suffix}", "afr", ["airflow", "fuel_flow", "humidity"], ["combustion"]),
            "combustion": CausalChainNode(f"combustion{e_tag}", f"Combustion{suffix}", "combustion_efficiency", ["fuel_flow", "afr", "starter_command", "engine_start_stop"], ["indicated_power", "torque", "egt", "cht"]),
            "indicated_power": CausalChainNode(f"indicated_power{e_tag}", f"Indicated Power{suffix}", "indicated_power_kw", ["combustion"], ["torque"]),
            "torque": CausalChainNode(f"torque{e_tag}", f"Torque{suffix}", "torque_n_m", ["indicated_power", "combustion", "engine_operating_point"], ["rpm"]),
            "rpm": CausalChainNode(f"rpm{e_tag}", f"RPM{suffix}", "rpm", ["torque", "starter_command", "engine_start_stop", "engine_operating_point"], ["gearbox_rpm", "oil_pressure", "propeller_load", "thrust"]),
            "gearbox_rpm": CausalChainNode(f"gearbox_rpm{e_tag}", f"Gearbox RPM{suffix}", "gearbox_rpm", ["rpm"], ["propeller_load"]),
            "propeller_load": CausalChainNode(f"propeller_load{e_tag}", f"Propeller Load{suffix}", "propeller_load_nm", ["gearbox_rpm", "rpm", "aerodynamic_loading"], ["engine_operating_point", "thrust"]),
            "thrust": CausalChainNode(f"thrust{e_tag}", f"Thrust{suffix}", "thrust_n", ["propeller_load", "rpm", "engine_operating_point"], []),

            # Thermal & Lubrication Chain
            "egt": CausalChainNode(f"egt{e_tag}", f"EGT{suffix}", "egt_c", ["combustion", "engine_start_stop"], []),
            "cht": CausalChainNode(f"cht{e_tag}", f"CHT{suffix}", "cht_c", ["combustion", "ambient_temperature", "engine_start_stop"], ["coolant_temp", "oil_temp"]),
            "coolant_temp": CausalChainNode(f"coolant_temp{e_tag}", f"Coolant Temp{suffix}", "coolant_temp_c", ["cht", "ambient_temperature", "engine_start_stop"], ["oil_temp"]),
            "oil_temp": CausalChainNode(f"oil_temp{e_tag}", f"Oil Temp{suffix}", "oil_temp_c", ["coolant_temp", "cht", "ambient_temperature", "engine_start_stop"], ["oil_pressure"]),
            "oil_pressure": CausalChainNode(f"oil_pressure{e_tag}", f"Oil Pressure{suffix}", "oil_pressure_bar", ["rpm", "oil_temp", "engine_start_stop"], []),
        }

    def analyze_causal_chain(
        self,
        residual_state: ResidualState,
        engine_index: int = 1
    ) -> Dict[str, Any]:
        """
        Evaluates physical residuals against the engine causal graph.
        Distinguishes PRIMARY_DEVIATION from PROPAGATED_DEVIATION via recursive parent search.
        """
        graph = self._get_engine_graph(engine_index)
        residuals = residual_state.residuals if residual_state else {}

        # 1. Update node residual values and initial warning flags
        warning_keys = set()
        for key, node in graph.items():
            param_res = residuals.get(node.param_key)
            if param_res:
                node.residual_val = param_res.residual
                if param_res.warning_triggered and param_res.quality == "VALID":
                    warning_keys.add(key)

        # 2. Recursive helper to check if any upstream ancestor has an active warning
        def has_upstream_warning(n_key: str, visited: Optional[set] = None) -> bool:
            if visited is None:
                visited = set()
            if n_key in visited:
                return False
            visited.add(n_key)

            node = graph.get(n_key)
            if not node:
                return False

            for p_key in node.upstream_parents:
                if p_key in warning_keys:
                    return True
                if has_upstream_warning(p_key, visited):
                    return True
            return False

        # 3. Classify node status
        for key, node in graph.items():
            if key in warning_keys:
                if has_upstream_warning(key):
                    node.status = CausalNodeStatus.PROPAGATED_DEVIATION
                else:
                    node.status = CausalNodeStatus.PRIMARY_DEVIATION
            else:
                node.status = CausalNodeStatus.NORMAL

        primary_nodes = [n.node_id for n in graph.values() if n.status == CausalNodeStatus.PRIMARY_DEVIATION]
        propagated_nodes = [n.node_id for n in graph.values() if n.status == CausalNodeStatus.PROPAGATED_DEVIATION]

        return {
            "engine_index": engine_index,
            "summary": f"Causal deviation analysis for engine {engine_index}",
            "has_deviations": len(warning_keys) > 0,
            "primary_deviations": primary_nodes,
            "propagated_deviations": propagated_nodes,
            "nodes": {
                k: {
                    "node_id": v.node_id,
                    "name": v.name,
                    "status": v.status.value,
                    "residual": v.residual_val,
                    "param_key": v.param_key
                }
                for k, v in graph.items()
            }
        }
