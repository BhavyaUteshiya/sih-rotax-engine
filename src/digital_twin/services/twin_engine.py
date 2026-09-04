"""
Digital Twin Core Engine Orchestrator Service.
SIH26054 — Module 03 Digital Twin Core.
"""

from typing import Any, Dict, List, Optional

from src.digital_twin.analysis.causal_analyzer import CausalAnalyzer
from src.digital_twin.analysis.residual_analyzer import ResidualAnalyzer
from src.digital_twin.models.expected_state import ExpectedState
from src.digital_twin.models.observed_state import ObservedState
from src.digital_twin.models.residual_state import ResidualState
from src.digital_twin.models.twin_state import DigitalTwinState, DigitalTwinStatus
from src.digital_twin.models.twin_internal_state import TwinInternalState
from src.digital_twin.physics.expected_behavior import ExpectedBehaviorModel
from src.digital_twin.physics.estimator import AlphaFilterEstimator


class DigitalTwinEngine:
    """
    Main orchestrator service for Digital Twin Phase 1:
    Ingests Module 02 validated telemetry, extracts ExpectedState from Module 01 physics,
    computes ParameterResiduals, evaluates Causal Deviation Graph, updates Twin Status,
    and generates backend warning events.
    """

    def __init__(self, config_path: str = "configs/digital_twin_config.yaml") -> None:
        self.residual_analyzer = ResidualAnalyzer(config_path=config_path)
        self.causal_analyzer = CausalAnalyzer()
        self.estimator = AlphaFilterEstimator(alpha=0.2)
        
        # Internal states track physics inertia
        self.healthy_internal_states: Dict[int, TwinInternalState] = {
            1: TwinInternalState(timestamp=0.0),
            2: TwinInternalState(timestamp=0.0),
        }
        
        self.twin_states: Dict[int, DigitalTwinState] = {
            1: DigitalTwinState(engine_id="engine_1", healthy_internal_state=self.healthy_internal_states[1]),
            2: DigitalTwinState(engine_id="engine_2", healthy_internal_state=self.healthy_internal_states[2]),
        }
        self.history_records: List[Dict[str, Any]] = []
        self.active_warnings: List[Dict[str, Any]] = []

    def process_step(
        self,
        sim_state: Any,
        pipeline: Optional[Any] = None,
        telemetry_frame: Optional[Any] = None,
        normalized_records: Optional[List[Any]] = None,
        engine_index: int = 1,
        timestamp: float = 0.0,
        sequence_number: int = 0,
        operating_context: Optional[Dict[str, Any]] = None,
        propeller_state: Optional[Any] = None
    ) -> DigitalTwinState:
        """
        Executes a single Digital Twin evaluation step for engine_index.
        Aligns ExpectedState (from Module 01) and ObservedState (from Module 02 validated telemetry).
        """
        ctx = operating_context if operating_context is not None else {}

        # Compute time step (dt)
        prev_healthy_internal = self.healthy_internal_states.get(engine_index, TwinInternalState(timestamp=timestamp))
        dt = timestamp - prev_healthy_internal.timestamp
        if dt <= 0:
            dt = 0.05  # Default dt if time hasn't advanced or is first step

        # 1. Predict Healthy Expected State
        expected, next_healthy_internal = ExpectedBehaviorModel.predict_state(
            prev_internal=prev_healthy_internal,
            operating_context=ctx,
            dt=dt,
            engine_index=engine_index,
            sequence_number=sequence_number
        )
        
        # 1b. Store the independent healthy reference for the next timestep
        # This MUST remain completely independent of physical telemetry
        self.healthy_internal_states[engine_index] = next_healthy_internal

        # 2. Derive Observed State from telemetry
        observed = self._derive_observed_state(
            pipeline=pipeline,
            telemetry_frame=telemetry_frame,
            normalized_records=normalized_records,
            engine_index=engine_index,
            timestamp=timestamp,
            sequence_number=sequence_number,
            propeller_state=propeller_state
        )
        
        # 3. Synchronize: Produce the Estimated Actual State
        # The estimator observes the telemetry and produces our best estimate of the *actual* physical engine state.
        # This estimate does NOT feed back into the healthy model.
        estimated_actual_internal = self.estimator.synchronize(next_healthy_internal, observed)

        # 4. Calculate Residuals (Expected vs Observed)
        residuals = self.residual_analyzer.analyze(expected, observed)

        # 5. Perform Causal Deviation Analysis
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
            simulation_time=timestamp,
            engine_id=f"engine_{engine_index}",
            aircraft_id="rotax_914_uav",
            observed_state=observed,
            expected_state=expected,
            residual_state=residuals,
            healthy_internal_state=next_healthy_internal,
            estimated_actual_state=estimated_actual_internal,
            operating_context=ctx,
            data_quality=observed.data_quality,
            confidence=confidence,
            status=status,
            warnings=warnings,
            causal_chain_status=causal_res
        )

        self.twin_states[engine_index] = state
        self._record_twin_observation(state)
        return state

    def _derive_observed_state(
        self,
        pipeline: Optional[Any],
        telemetry_frame: Optional[Any],
        normalized_records: Optional[List[Any]],
        engine_index: int,
        timestamp: float,
        sequence_number: int,
        propeller_state: Optional[Any]
    ) -> ObservedState:
        """Extracts validated/normalized telemetry observations strictly from Module 02."""
        return ObservedState.from_module02_pipeline(
            pipeline=pipeline,
            engine_index=engine_index,
            target_timestamp=timestamp,
            target_sequence=sequence_number
        )

    def _generate_warning_events(
        self,
        residuals: ResidualState,
        causal_res: Dict[str, Any],
        engine_index: int
    ) -> List[Dict[str, Any]]:
        """Formulates backend Digital Twin warning event dictionaries."""
        warning_events: List[Dict[str, Any]] = []
        for param, res in residuals.residuals.items():
            if res.warning_triggered:
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
            "data_quality": st.data_quality,
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
        return st.causal_chain_status if st else {}

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
