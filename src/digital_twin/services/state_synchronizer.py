"""
State Synchronizer Service
SIH26054 — Module 03 Digital Twin Core.
"""

from typing import Optional

from src.digital_twin.models.healthy_expected_state import HealthyExpectedState
from src.digital_twin.models.observed_state import ObservedState
from src.digital_twin.models.operating_context import OperatingContext
from src.digital_twin.models.synchronization_result import SynchronizationResult, SynchronizationStatus


class StateSynchronizer:
    """
    Explicit synchronization layer (Phase 2C).
    Responsible for deterministic temporal, contextual, and physical alignment 
    between Observed (telemetry) and Expected (physics) states.
    """

    # Timestamp tolerance for deterministic frame alignment
    DEFAULT_TIMESTAMP_TOLERANCE_S = 0.1

    def __init__(self, timestamp_tolerance_s: float = DEFAULT_TIMESTAMP_TOLERANCE_S):
        # Explicitly documented synchronization tolerances
        self.timestamp_tolerance_s = timestamp_tolerance_s

    def synchronize(
        self,
        expected: HealthyExpectedState,
        observed: Optional[ObservedState],
        context: OperatingContext,
        last_sequence_number: int = -1
    ) -> SynchronizationResult:
        """
        Evaluates temporal alignment, data quality, engine identity, and context.
        Returns a SynchronizationResult contract.
        """
        
        # 1. Missing Observation Check
        if observed is None:
            return SynchronizationResult(
                is_synchronized=False,
                status=SynchronizationStatus.MISSING_OBSERVATION,
                observed_timestamp=-1.0,
                expected_timestamp=expected.timestamp,
                sequence_delta=0,
                engine_id=expected.engine_id,
                quality_effect="INSUFFICIENT_DATA",
                reason="No observation provided."
            )

        delta_t = observed.timestamp - expected.timestamp
        seq_delta = observed.sequence_number - last_sequence_number

        # 2. Engine Identity Check
        if observed.engine_id != expected.engine_id:
            return SynchronizationResult(
                is_synchronized=False,
                status=SynchronizationStatus.ENGINE_MISMATCH,
                observed_timestamp=observed.timestamp,
                expected_timestamp=expected.timestamp,
                sequence_delta=seq_delta,
                engine_id=expected.engine_id,
                quality_effect="INVALID",
                reason=f"Observed engine {observed.engine_id} does not match expected {expected.engine_id}."
            )

        # 3. Data Quality Checks
        if observed.data_quality == "INVALID":
            return SynchronizationResult(
                is_synchronized=False,
                status=SynchronizationStatus.INVALID_OBSERVATION,
                observed_timestamp=observed.timestamp,
                expected_timestamp=expected.timestamp,
                sequence_delta=seq_delta,
                engine_id=expected.engine_id,
                quality_effect="INVALID",
                reason="Observation data quality is marked INVALID."
            )
            
        if observed.data_quality == "INSUFFICIENT_DATA":
            return SynchronizationResult(
                is_synchronized=False,
                status=SynchronizationStatus.INSUFFICIENT_DATA,
                observed_timestamp=observed.timestamp,
                expected_timestamp=expected.timestamp,
                sequence_delta=seq_delta,
                engine_id=expected.engine_id,
                quality_effect="INSUFFICIENT_DATA",
                reason="Observation data quality is marked INSUFFICIENT_DATA."
            )

        # 4. Temporal Alignment Checks
        if observed.sequence_number <= last_sequence_number:
            # Sequence 0 is only valid if it's the very first sequence (last_sequence_number == -1)
            if not (last_sequence_number == -1 and observed.sequence_number == 0):
                return SynchronizationResult(
                    is_synchronized=False,
                status=SynchronizationStatus.OUT_OF_ORDER,
                observed_timestamp=observed.timestamp,
                expected_timestamp=expected.timestamp,
                sequence_delta=seq_delta,
                engine_id=expected.engine_id,
                quality_effect="DEGRADED",
                reason=f"Sequence {observed.sequence_number} is older than last known {last_sequence_number}."
            )

        if delta_t < -self.timestamp_tolerance_s:
            return SynchronizationResult(
                is_synchronized=False,
                status=SynchronizationStatus.STALE_OBSERVATION,
                observed_timestamp=observed.timestamp,
                expected_timestamp=expected.timestamp,
                sequence_delta=seq_delta,
                engine_id=expected.engine_id,
                quality_effect="DEGRADED",
                reason=f"Observation is too old (delta: {delta_t:.3f}s)."
            )

        if abs(delta_t) > self.timestamp_tolerance_s:
             return SynchronizationResult(
                is_synchronized=False,
                status=SynchronizationStatus.TIMESTAMP_MISMATCH,
                observed_timestamp=observed.timestamp,
                expected_timestamp=expected.timestamp,
                sequence_delta=seq_delta,
                engine_id=expected.engine_id,
                quality_effect="DEGRADED",
                reason=f"Timestamp mismatch exceeds tolerance (delta: {delta_t:.3f}s)."
            )
             
        # 5. Context Alignment Checks
        # Context synchronization is reserved for future phases.
        # Currently, the repository does not contain justified numerical tolerances for context variables.
        # We explicitly decline to falsely claim complete numeric context validation without engineering limits.
        
        # 6. Success
        final_status = SynchronizationStatus.SYNC_SUCCESS
        quality_effect = "GOOD"
        if observed.data_quality == "DEGRADED":
            final_status = SynchronizationStatus.DEGRADED_OBSERVATION
            quality_effect = "DEGRADED"

        return SynchronizationResult(
            is_synchronized=True,
            status=final_status,
            observed_timestamp=observed.timestamp,
            expected_timestamp=expected.timestamp,
            sequence_delta=seq_delta,
            engine_id=expected.engine_id,
            quality_effect=quality_effect,
            reason=None
        )
