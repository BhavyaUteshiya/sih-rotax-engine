"""
SensorMeasurement Model Implementation.
SIH26054 — Module 01 Data Acquisition & Ingestion.
"""

from dataclasses import dataclass
from typing import Optional, FrozenSet

from src.module01.models.enums import (
    IntegrityStatus,
    ParameterClassification,
    PhysicalOrigin,
    ProcessingContext,
    StateCategory,
    TemporalQuality,
    TransformationMetadata,
    TransportProtocol,
    ValidityStatus,
)
from src.module01.models.metadata import (
    AlignmentMetadata,
    DecodedSignal,
    MeasurementLineage,
    TimestampModel,
    UnitMetadata,
)


UNUSABLE_VALIDITY_FLAGS = frozenset({
    ValidityStatus.INVALID,
    ValidityStatus.OUT_OF_RANGE,
    ValidityStatus.RATE_OF_CHANGE_VIOLATION,
})


@dataclass(frozen=True)
class SensorMeasurement:
    """
    Granular representation of a single physical, derived, or simulated sensor measurement.
    Preserves explicit 4-tier quality, multi-domain timestamps, provenance, and 4-stage lineage.
    """
    measurement_id: str                          # Unique UUID / sequence ID
    parameter_id: str                            # Stable sensor key (e.g. "engine.rpm")
    value: Optional[float]                       # Canonical SI value (or None if physically invalid)
    engineering_value: Optional[float]           # Human-facing display value (e.g. 5200.0 RPM)
    raw_signal: Optional[DecodedSignal]          # Layer 2 decoded raw signal
    unit_metadata: UnitMetadata                  # Explicit unit metadata
    validity_status: ValidityStatus              # Physical validity status
    temporal_quality: TemporalQuality            # Timestamp quality & alignment status
    transformation_metadata: TransformationMetadata # Data transformation stage
    integrity_status: IntegrityStatus            # Packet transmission integrity status
    is_physically_valid: bool                    # True if physically plausible & sound
    is_temporally_valid: bool                    # True if timestamp is valid & resolvable
    is_sync_eligible: bool                       # True if eligible for temporal grid alignment
    physical_origin: PhysicalOrigin              # Origin classification (SENSOR, ECU, FADEC, etc.)
    transport_protocol: TransportProtocol        # Transport mechanism (CAN, SOCKETCAN, FILE, etc.)
    processing_context: ProcessingContext        # Stream context (LIVE_STREAM, REPLAY, etc.)
    state_category: StateCategory                # State classification (ACTUAL_MEASURED, SIMULATED, etc.)
    timestamps: TimestampModel                   # Multi-domain timestamp container
    lineage: MeasurementLineage                  # Traceability ancestry
    alignment_metadata: Optional[AlignmentMetadata] = None # Frame alignment details
    classification: ParameterClassification = ParameterClassification.REPRESENTATIVE
    config_version: str = "1.0.0"                # Active configuration hash

    @classmethod
    def create_valid(
        cls,
        measurement_id: str,
        parameter_id: str,
        value: float,
        engineering_value: float,
        unit_metadata: UnitMetadata,
        timestamps: TimestampModel,
        lineage: MeasurementLineage,
        physical_origin: PhysicalOrigin = PhysicalOrigin.ECU,
        transport_protocol: TransportProtocol = TransportProtocol.CAN,
        processing_context: ProcessingContext = ProcessingContext.LIVE_STREAM,
        state_category: StateCategory = StateCategory.ACTUAL_MEASURED,
        raw_signal: Optional[DecodedSignal] = None,
        classification: ParameterClassification = ParameterClassification.SIH_REQUIRED,
        config_version: str = "1.0.0",
    ) -> "SensorMeasurement":
        """
        Factory helper to create a valid physical measurement.
        """
        is_temp_valid = timestamps.normalized_source_utc is not None
        is_sync_elig = is_temp_valid

        return cls(
            measurement_id=measurement_id,
            parameter_id=parameter_id,
            value=value,
            engineering_value=engineering_value,
            raw_signal=raw_signal,
            unit_metadata=unit_metadata,
            validity_status=ValidityStatus.VALID,
            temporal_quality=TemporalQuality.SYNCHRONIZED if is_temp_valid else TemporalQuality.UNRESOLVED_CLOCK,
            transformation_metadata=TransformationMetadata.NORMALIZED,
            integrity_status=IntegrityStatus.ORIGINAL,
            is_physically_valid=True,
            is_temporally_valid=is_temp_valid,
            is_sync_eligible=is_sync_elig,
            physical_origin=physical_origin,
            transport_protocol=transport_protocol,
            processing_context=processing_context,
            state_category=state_category,
            timestamps=timestamps,
            lineage=lineage,
            classification=classification,
            config_version=config_version,
        )
