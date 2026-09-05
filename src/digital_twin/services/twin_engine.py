"""
Digital Twin Core Engine Orchestrator Service.
SIH26054 — Phase 2 Digital Twin Digital Twin Core.
"""

from typing import Any, Dict, List, Optional

from src.digital_twin.analysis.causal_analyzer import CausalAnalyzer
from src.digital_twin.analysis.residual_analyzer import ResidualAnalyzer
from src.digital_twin.models.health_state import HealthState, HealthLevel
from src.digital_twin.models.healthy_expected_state import HealthyExpectedState
from src.digital_twin.models.observed_state import ObservedState
from src.digital_twin.models.residual_state import ResidualState
from src.digital_twin.models.twin_state import DigitalTwinState, DigitalTwinStatus, DigitalTwinDataQuality
from src.digital_twin.models.operating_context import OperatingContext
from src.digital_twin.physics.healthy_reference_model import HealthyReferenceModel
from src.digital_twin.services.state_synchronizer import StateSynchronizer
from src.digital_twin.models.estimated_actual_state import EstimatedActualState
from src.digital_twin.estimation.state_estimator import StateEstimator


class DigitalTwinEngine:
    """
    Main orchestrator service for Digital Twin Phase 2A - 2C:
    Aligns HealthyExpectedState (from Physics) and ObservedState (from telemetry),
    computes ParameterResiduals, evaluates Causal Deviation Graph, and updates Twin Status.
    NOTE: Telemetry ingestion is deliberately externalized from the Core Engine.
    """

    def __init__(self, config_path: str = "configs/digital_twin_config.yaml") -> None:
        self.residual_analyzer = ResidualAnalyzer(config_path=config_path)
        self.causal_analyzer = CausalAnalyzer()
        self.twin_states: Dict[int, DigitalTwinState] = {
            1: DigitalTwinState(engine_id="engine_1"),
            2: DigitalTwinState(engine_id="engine_2"),
        }
        self.reference_models: Dict[int, HealthyReferenceModel] = {
            1: HealthyReferenceModel(engine_index=1),
            2: HealthyReferenceModel(engine_index=2),
        }
        self.synchronizer = StateSynchronizer()
        self.last_sequence: Dict[int, int] = {1: -1, 2: -1}
        self.history_records: List[Dict[str, Any]] = []
        self.active_warnings: List[Dict[str, Any]] = []
        self.last_causal_analysis: Dict[int, Dict[str, Any]] = {1: {}, 2: {}}
        
        # Phase 2D State Estimators
        self.estimators: Dict[int, StateEstimator] = {
            1: StateEstimator(),
            2: StateEstimator()
        }

    def process_step(
        self,
        operating_context: OperatingContext,
        dt: float,
        observed_state: Optional[ObservedState] = None,
        engine_index: int = 1,
        timestamp: float = 0.0,
        sequence_number: int = 0
    ) -> DigitalTwinState:
        """
        Executes a single Digital Twin evaluation step for engine_index.
        
        Semantics:
        - Internal simulator time defines the reference physics state.
        - The telemetry (ObservedState) timestamp/sequence acts as the explicit synchronization frame.
        - The expected state is intentionally tagged with this synchronization frame to guarantee logical alignment.
        - The expected state itself is generated PURELY from physics/context, NEVER from observed telemetry.
        """
        # 1. Derive Expected State from internal Healthy Reference Model
        expected = self.reference_models[engine_index].step(context=operating_context, dt=dt)
        expected.timestamp = timestamp
        expected.sequence_number = sequence_number

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

        # 3. Synchronize Observed and Expected (Phase 2C)
        sync_result = self.synchronizer.synchronize(
            expected=expected,
            observed=observed,
            context=operating_context,
            last_sequence_number=self.last_sequence[engine_index]
        )
        
        valid_evidence_count = 0
        
        # 4. Only Calculate Residuals if Synchronized
        if not sync_result.is_synchronized:
            # Bypass downstream evaluation if we cannot align the signals deterministically.
            residuals = ResidualState()
            causal_res = self.last_causal_analysis.get(engine_index, {})
            
            # Map quality based on sync result
            if sync_result.quality_effect == "INVALID":
                status = DigitalTwinStatus.SYNC_FAILED
                data_quality = DigitalTwinDataQuality.INVALID
                confidence = 0.0  # Zero confidence when sync explicitly fails due to invalid observation
            elif sync_result.quality_effect == "INSUFFICIENT_DATA":
                status = DigitalTwinStatus.INSUFFICIENT_DATA
                data_quality = DigitalTwinDataQuality.INSUFFICIENT_DATA
                confidence = 0.0
            else:
                status = DigitalTwinStatus.SYNC_FAILED
                data_quality = DigitalTwinDataQuality.DEGRADED
                confidence = 0.0
            warnings = []
            
            # Run estimator in prediction-only mode by passing empty observed state
            empty_observed = ObservedState()
            estimated_state = self.estimators[engine_index].estimate(expected, empty_observed, dt)
            estimated_state.estimation_confidence = 0.0
        else:
            # Update sequence tracker on success
            if observed.sequence_number is not None:
                self.last_sequence[engine_index] = observed.sequence_number
                
            # Phase 2D State Estimation (UKF)
            estimated_state = self.estimators[engine_index].estimate(expected, observed, dt)

            # 5. Calculate Residuals
            residuals = self.residual_analyzer.analyze(expected, observed, estimated_state)
    
            for param in ["rpm", "map_bar", "turbo_rpm", "airflow_kg_h", "fuel_flow_kg_h",
                          "afr", "combustion_energy", "combustion_efficiency", "indicated_power_kw",
                          "torque_n_m", "egt_c", "cht_c", "coolant_temp_c", "oil_temp_c",
                          "oil_pressure_bar", "turbo_boost_bar", "gearbox_rpm", "propeller_load_nm", "thrust_n"]:
                res = getattr(residuals, param)
                if res and res.status not in ("MISSING", "INVALID_NAN", "INVALID_INF"):
                    valid_evidence_count += 1

            # 6. Perform Causal Deviation Analysis
            causal_res = self.causal_analyzer.analyze_causal_chain(residuals, engine_index=engine_index)
            self.last_causal_analysis[engine_index] = causal_res
    
            # 7. Determine Twin Lifecycle Status based on Analysis & Sync Result
            warnings = []
            
            # Confidence logic based on residual counts
            # Note: These confidence values (0.3, 0.7, 0.85, 1.0) are strictly deterministic
            # engineering/calibration policy values reflecting the twin's confidence in its
            # assessment of the engine state. They are NOT probabilities and do NOT imply
            # ML/stochastic probability of engine health.
            if valid_evidence_count == 0:
                status = DigitalTwinStatus.INSUFFICIENT_DATA
                data_quality = DigitalTwinDataQuality.INSUFFICIENT_DATA
                confidence = 0.0  # Policy: Insufficient/invalid residual inputs block assessment. Confidence drops.
                warnings = self._generate_warning_events(residuals, causal_res, engine_index)
            elif residuals.criticals_count > 0:
                status = DigitalTwinStatus.DEVIATION_DETECTED
                data_quality = DigitalTwinDataQuality.GOOD if sync_result.quality_effect == "GOOD" else DigitalTwinDataQuality.DEGRADED
                confidence = 0.3  # Policy: Critical physical deviations severely degrade twin confidence
                warnings = self._generate_warning_events(residuals, causal_res, engine_index)
            elif residuals.warnings_count > 0:
                status = DigitalTwinStatus.DATA_QUALITY_DEGRADED
                data_quality = DigitalTwinDataQuality.GOOD if sync_result.quality_effect == "GOOD" else DigitalTwinDataQuality.DEGRADED
                confidence = 0.85  # Policy: Minor physical deviations slightly degrade twin confidence
                warnings = self._generate_warning_events(residuals, causal_res, engine_index)
            elif sync_result.status == "DEGRADED_OBSERVATION":
                status = DigitalTwinStatus.DATA_QUALITY_DEGRADED
                data_quality = DigitalTwinDataQuality.DEGRADED
                confidence = 0.7  # Policy: Poor telemetry data quality caps overall confidence
            else:
                status = DigitalTwinStatus.SYNCHRONIZED
                data_quality = DigitalTwinDataQuality.GOOD
                # Policy: Nominal state. Inherit estimator confidence (default 1.0)
                confidence = estimated_state.estimation_confidence if hasattr(estimated_state, 'estimation_confidence') else 1.0

        # 8. Phase 2F Health State Determination
        # Determine dominant parameter if any
        dominant_parameter = "NONE"
        for param in ["rpm", "map_bar", "turbo_rpm", "airflow_kg_h", "fuel_flow_kg_h",
                      "afr", "combustion_energy", "combustion_efficiency", "indicated_power_kw",
                      "torque_n_m", "egt_c", "cht_c", "coolant_temp_c", "oil_temp_c",
                      "oil_pressure_bar", "turbo_boost_bar", "gearbox_rpm", "propeller_load_nm", "thrust_n"]:
            res = getattr(residuals, param)
            if res and res.status == "CRITICAL":
                dominant_parameter = param.upper()
                break
        
        if dominant_parameter == "NONE":
            for param in ["rpm", "map_bar", "turbo_rpm", "airflow_kg_h", "fuel_flow_kg_h",
                          "afr", "combustion_energy", "combustion_efficiency", "indicated_power_kw",
                          "torque_n_m", "egt_c", "cht_c", "coolant_temp_c", "oil_temp_c",
                          "oil_pressure_bar", "turbo_boost_bar", "gearbox_rpm", "propeller_load_nm", "thrust_n"]:
                res = getattr(residuals, param)
                if res and res.status == "WARNING":
                    dominant_parameter = param.upper()
                    break

        is_assessable = True
        if not sync_result.is_synchronized:
            health_level = HealthLevel.UNKNOWN
            is_assessable = False
            assessment_reason = "Synchronization failed."
        elif valid_evidence_count == 0:
            health_level = HealthLevel.UNKNOWN
            is_assessable = False
            assessment_reason = "Insufficient valid evidence for assessment."
        elif residuals.criticals_count > 0:
            health_level = HealthLevel.CRITICAL
            assessment_reason = "Critical physical deviation detected."
        elif residuals.warnings_count > 0:
            health_level = HealthLevel.WARNING
            assessment_reason = "Warning physical deviation detected."
        elif data_quality == DigitalTwinDataQuality.DEGRADED:
            health_level = HealthLevel.DEGRADED
            assessment_reason = "Data quality or estimator limitations degrade assessment."
        else:
            health_level = HealthLevel.HEALTHY
            assessment_reason = "Nominal operation."

        health_state = HealthState(
            timestamp=timestamp,
            engine_id=f"engine_{engine_index}",
            health_level=health_level,
            is_assessable=is_assessable,
            health_confidence=confidence,
            assessment_reason=assessment_reason,
            dominant_parameter=dominant_parameter,
            critical_count=residuals.criticals_count,
            warning_count=residuals.warnings_count,
            missing_count=residuals.missing_count,
            invalid_count=residuals.invalid_count
        )

        # 9. Package Master Digital Twin State
        state = DigitalTwinState(
            timestamp=timestamp,
            engine_id=f"engine_{engine_index}",
            aircraft_id="rotax_914_uav",
            operating_context=operating_context,
            observed_state=observed,
            healthy_expected_state=expected,
            estimated_actual_state=estimated_state,
            residual_state=residuals,
            health_state=health_state,
            synchronization_result=sync_result,
            data_quality=data_quality,
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
            if res and res.status in ("WARNING", "CRITICAL"):
                warning_events.append({
                    "engine_index": engine_index,
                    "parameter": param.upper(),
                    "expected": res.expected,
                    "actual": res.actual,
                    "actual_source": res.actual_source,
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
        return self.last_causal_analysis.get(engine_index, {})

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
            "residuals_count": state.residual_state.warnings_count + state.residual_state.criticals_count
        })
        if len(self.history_records) > 500:
            self.history_records.pop(0)
