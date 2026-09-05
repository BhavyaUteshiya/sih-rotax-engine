"""
Digital Twin Core Engine Orchestrator Service.
SIH26054 — Module 03 Digital Twin Core.
"""

from typing import Any, Dict, List, Optional

from src.digital_twin.analysis.causal_analyzer import CausalAnalyzer
from src.digital_twin.analysis.residual_analyzer import ResidualAnalyzer
from src.digital_twin.models.healthy_expected_state import HealthyExpectedState
from src.digital_twin.models.observed_state import ObservedState
from src.digital_twin.models.residual_state import ResidualState
from src.digital_twin.models.twin_state import DigitalTwinState, DigitalTwinStatus, DigitalTwinDataQuality
from src.digital_twin.physics.expected_behavior import ExpectedBehaviorModel


class DigitalTwinEngine:
    """
    Main orchestrator service for Digital Twin Phase 2A:
    Aligns HealthyExpectedState (from Module 01) and ObservedState (from telemetry),
    computes ParameterResiduals, evaluates Causal Deviation Graph, and updates Twin Status.
    NOTE: Telemetry ingestion is deliberately excluded from Phase 2A.
    """

    def __init__(self, config_path: str = "configs/digital_twin_config.yaml") -> None:
        self.residual_analyzer = ResidualAnalyzer(config_path=config_path)
        self.causal_analyzer = CausalAnalyzer()
        self.twin_states: Dict[int, DigitalTwinState] = {
            1: DigitalTwinState(engine_id="engine_1"),
            2: DigitalTwinState(engine_id="engine_2"),
        }
        self.history_records: List[Dict[str, Any]] = []
        self.active_warnings: List[Dict[str, Any]] = []

    def process_step(
        self,
        sim_state: Any,
        observed_state: Optional[ObservedState] = None,
        engine_index: int = 1,
        timestamp: float = 0.0,
        sequence_number: int = 0,
        operating_context: Optional[Dict[str, Any]] = None,
        propeller_state: Optional[Any] = None
    ) -> DigitalTwinState:
        """
        Executes a single Digital Twin evaluation step for engine_index.
        """
        ctx = operating_context if operating_context is not None else {}

        # 1. Derive Expected State from Module 01 physics
        expected = ExpectedBehaviorModel.from_simulation_state(
            sim_state=sim_state,
            engine_index=engine_index,
            timestamp=timestamp,
            sequence_number=sequence_number,
            propeller_state=propeller_state
        )

        # 2. Use provided Observed State (Telemetry ingestion is external in Phase 2A)
        if observed_state is None:
             observed = ObservedState(
                timestamp=timestamp, 
                sequence_number=sequence_number, 
                engine_id=f"engine_{engine_index}", 
                data_quality="INSUFFICIENT_DATA"
             )
        else:
             observed = observed_state

        # 3. Calculate Residuals
        residuals = self.residual_analyzer.analyze(expected, observed)

        # 4. Perform Causal Deviation Analysis
        causal_res = self.causal_analyzer.analyze_causal_chain(residuals, engine_index=engine_index)

        # 5. Determine Twin Lifecycle Status
        if observed.data_quality == "INSUFFICIENT_DATA":
            status = DigitalTwinStatus.INSUFFICIENT_DATA
            confidence = 0.0
            warnings = []
        elif observed.data_quality == "INVALID":
            status = DigitalTwinStatus.DATA_QUALITY_DEGRADED
            confidence = 0.5
            warnings = self._generate_warning_events(residuals, causal_res, engine_index)
        elif residuals.warnings_count > 0:
            status = DigitalTwinStatus.DEVIATION_DETECTED
            confidence = 0.85
            warnings = self._generate_warning_events(residuals, causal_res, engine_index)
        elif observed.data_quality == "DEGRADED":
            status = DigitalTwinStatus.DATA_QUALITY_DEGRADED
            confidence = 0.7
            warnings = self._generate_warning_events(residuals, causal_res, engine_index)
        else:
            status = DigitalTwinStatus.SYNCHRONIZED
            confidence = 1.0
            warnings = []

        # 7. Package Master Digital Twin State
        state = DigitalTwinState(
            timestamp=timestamp,
            engine_id=f"engine_{engine_index}",
            aircraft_id="rotax_914_uav",
            observed_state=observed,
            healthy_expected_state=expected,
            residual_state=residuals,
            data_quality=DigitalTwinDataQuality.GOOD,
            confidence=confidence,
            status=status,
            warnings=warnings,
        )

        self.twin_states[engine_index] = state
        self._record_twin_observation(state)
        return state

    def _generate_warning_events(
        self,
        residuals: ResidualState,
        causal_res: Dict[str, Any],
        engine_index: int
    ) -> List[Dict[str, Any]]:
        """Formulates backend Digital Twin warning event dictionaries."""
        warning_events: List[Dict[str, Any]] = []
        for param in ["rpm", "map_bar", "turbo_rpm", "airflow_kg_h", "fuel_flow_kg_h",
                      "afr", "combustion_energy", "combustion_efficiency", "indicated_power_kw",
                      "torque_n_m", "egt_c", "cht_c", "coolant_temp_c", "oil_temp_c",
                      "oil_pressure_bar", "turbo_boost_bar", "gearbox_rpm", "propeller_load_nm", "thrust_n"]:
            res = getattr(residuals, param)
            if res and res.warning_triggered:
                warning_events.append({
                    "engine_index": engine_index,
                    "parameter": param.upper(),
                    "expected": res.expected,
                    "observed": res.observed,
                    "residual": res.residual,
                    "relative_error": res.relative_error,
                    "unit": res.unit,
                    "timestamp": res.timestamp,
                    "causal_status": causal_res.get("nodes", {}).get(param, {}).get("status", "PRIMARY_DEVIATION")
                })
        return warning_events

    def get_state(self, engine_index: int = 1) -> Dict[str, Any]:
        """Retrieves master Digital Twin state dictionary for engine_index."""
        st = self.twin_states.get(engine_index)
        return st.to_dict() if st else {}

    def get_status(self, engine_index: int = 1) -> Dict[str, Any]:
        """Retrieves Digital Twin status summary for engine_index."""
        st = self.twin_states.get(engine_index)
        if not st:
            return {"status": "OFFLINE", "confidence": 0.0}
        return {
            "engine_id": st.engine_id,
            "status": st.status.value if hasattr(st.status, "value") else str(st.status),
            "data_quality": str(st.data_quality),
            "confidence": st.confidence,
            "timestamp": st.timestamp,
            "warnings_count": len(st.warnings)
        }

    def get_residuals(self, engine_index: int = 1) -> Dict[str, Any]:
        """Retrieves residual state analysis dictionary for engine_index."""
        st = self.twin_states.get(engine_index)
        return st.residual_state.to_dict() if st else {}

    def get_causal_analysis(self, engine_index: int = 1) -> Dict[str, Any]:
        """Retrieves physical causal chain graph status for engine_index."""
        st = self.twin_states.get(engine_index)
        # Not fully implemented in 2A, return empty dict for now.
        return {}

    def get_warnings(self) -> List[Dict[str, Any]]:
        """Retrieves active backend warning events across all engines."""
        warns: List[Dict[str, Any]] = []
        for eng_idx, st in self.twin_states.items():
            warns.extend(st.warnings)
        return warns

    def _record_twin_observation(self, state: DigitalTwinState) -> None:
        """Appends state observation to rolling history log."""
        self.history_records.append({
            "timestamp": state.timestamp,
            "engine_id": state.engine_id,
            "status": state.status,
            "data_quality": state.data_quality,
            "residuals_count": state.residual_state.warnings_count
        })
        if len(self.history_records) > 500:
            self.history_records.pop(0)
