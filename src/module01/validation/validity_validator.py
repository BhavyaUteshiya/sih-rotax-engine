"""
Validity & Physical Plausibility Validator (Phase 9 Correction).
SIH26054 — Module 01 Data Acquisition & Ingestion.
"""

import math
from typing import Any, Dict, Optional, Tuple

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
from src.module01.models.metadata import DecodedSignal, MeasurementLineage, TimestampModel
from src.module01.models.sensor_sample import SensorMeasurement
from src.module01.normalization.unit_normalizer import UnitConversionError, UnitNormalizer


class ValidityValidator:
    """
    Validates physical plausibility and rate-of-change constraints.
    Module 01 Scope: Validates TELEMETRY PLAUSIBILITY ONLY. NEVER evaluates engine health or faults.
    """

    def __init__(self, limits_config: Dict[str, Any], sensor_defs_config: Dict[str, Any]):
        self.limits = limits_config.get("validity_limits", {})
        self.sensor_defs = sensor_defs_config.get("sensors", {})
        self._history: Dict[str, Tuple[float, float]] = {}

    def validate_and_create_measurement(
        self,
        decoded_signal: DecodedSignal,
        timestamps: TimestampModel,
        physical_origin: PhysicalOrigin = PhysicalOrigin.ECU,
        transport_protocol: TransportProtocol = TransportProtocol.CAN,
        processing_context: ProcessingContext = ProcessingContext.LIVE_STREAM,
        state_category: StateCategory = StateCategory.ACTUAL_MEASURED,
        integrity_status: IntegrityStatus = IntegrityStatus.ORIGINAL,
        measurement_id: Optional[str] = None,
        config_version: str = "1.0.0",
    ) -> SensorMeasurement:
        """
        Validates DecodedSignal and constructs fully decorated SensorMeasurement.
        Decouples physical validity (is_physically_valid) from temporal validity (is_temporally_valid).
        """
        param_id = decoded_signal.parameter_id
        raw_val = decoded_signal.raw_numeric_value
        raw_unit = decoded_signal.raw_unit
        meas_id = measurement_id if measurement_id is not None else f"meas_{decoded_signal.signal_id}"

        # If decoded_signal contains CAN scale/offset in decoding_metadata, compute raw unit value
        meta = decoded_signal.decoding_metadata
        if meta and "scale" in meta and "offset" in meta:
            scale = float(meta.get("scale", 1.0))
            offset = float(meta.get("offset", 0.0))
            raw_val = (float(raw_val) * scale) + offset

        lineage = MeasurementLineage(raw_packet_id=decoded_signal.raw_packet_id)
        sensor_info = self.sensor_defs.get(param_id, {})
        classification_str = sensor_info.get("classification", "REPRESENTATIVE")
        classification = getattr(ParameterClassification, classification_str, ParameterClassification.REPRESENTATIVE)

        # 1. Check Unit Validity
        try:
            canonical_val, engineering_val, unit_meta = UnitNormalizer.convert_to_si(raw_val, raw_unit)
        except UnitConversionError:
            return self._build_invalid_measurement(
                meas_id=meas_id,
                param_id=param_id,
                raw_signal=decoded_signal,
                timestamps=timestamps,
                lineage=lineage,
                validity_status=ValidityStatus.INVALID,
                physical_origin=physical_origin,
                transport_protocol=transport_protocol,
                processing_context=processing_context,
                state_category=state_category,
                integrity_status=integrity_status,
                classification=classification,
                config_version=config_version,
            )

        # 2. Check Numerical Plausibility (NaN / Inf)
        if math.isnan(canonical_val) or math.isinf(canonical_val):
            return self._build_invalid_measurement(
                meas_id=meas_id,
                param_id=param_id,
                raw_signal=decoded_signal,
                timestamps=timestamps,
                lineage=lineage,
                validity_status=ValidityStatus.INVALID,
                physical_origin=physical_origin,
                transport_protocol=transport_protocol,
                processing_context=processing_context,
                state_category=state_category,
                integrity_status=integrity_status,
                classification=classification,
                config_version=config_version,
                unit_meta=unit_meta,
            )

        # 3. Check Tier 2 Physical Plausibility Limits
        limit_info = self.limits.get(param_id, {})
        min_plausible = limit_info.get("min_plausible")
        max_plausible = limit_info.get("max_plausible")

        if min_plausible is not None and canonical_val < min_plausible:
            return self._build_invalid_measurement(
                meas_id=meas_id,
                param_id=param_id,
                raw_signal=decoded_signal,
                timestamps=timestamps,
                lineage=lineage,
                validity_status=ValidityStatus.OUT_OF_RANGE,
                physical_origin=physical_origin,
                transport_protocol=transport_protocol,
                processing_context=processing_context,
                state_category=state_category,
                integrity_status=integrity_status,
                classification=classification,
                config_version=config_version,
                unit_meta=unit_meta,
                engineering_val=engineering_val,
                canonical_val=canonical_val,
            )

        if max_plausible is not None and canonical_val > max_plausible:
            return self._build_invalid_measurement(
                meas_id=meas_id,
                param_id=param_id,
                raw_signal=decoded_signal,
                timestamps=timestamps,
                lineage=lineage,
                validity_status=ValidityStatus.OUT_OF_RANGE,
                physical_origin=physical_origin,
                transport_protocol=transport_protocol,
                processing_context=processing_context,
                state_category=state_category,
                integrity_status=integrity_status,
                classification=classification,
                config_version=config_version,
                unit_meta=unit_meta,
                engineering_val=engineering_val,
                canonical_val=canonical_val,
            )

        # 4. Check Tier 6 Max Rate-of-Change Violation
        max_roc = limit_info.get("max_rate_of_change_per_sec")
        ref_time = timestamps.normalized_source_utc if timestamps.normalized_source_utc is not None else timestamps.source_timestamp

        if max_roc is not None and param_id in self._history and ref_time is not None:
            last_val, last_time = self._history[param_id]
            dt = ref_time - last_time
            if dt > 0.000001:
                roc = abs(canonical_val - last_val) / dt
                if roc > max_roc:
                    return self._build_invalid_measurement(
                        meas_id=meas_id,
                        param_id=param_id,
                        raw_signal=decoded_signal,
                        timestamps=timestamps,
                        lineage=lineage,
                        validity_status=ValidityStatus.RATE_OF_CHANGE_VIOLATION,
                        physical_origin=physical_origin,
                        transport_protocol=transport_protocol,
                        processing_context=processing_context,
                        state_category=state_category,
                        integrity_status=integrity_status,
                        classification=classification,
                        config_version=config_version,
                        unit_meta=unit_meta,
                        engineering_val=engineering_val,
                        canonical_val=canonical_val,
                    )

        if ref_time is not None:
            self._history[param_id] = (canonical_val, ref_time)

        # Decouple Physical Validity from Temporal Validity
        is_temp_valid = timestamps.normalized_source_utc is not None
        is_sync_elig = is_temp_valid
        temp_quality = TemporalQuality.SYNCHRONIZED if is_temp_valid else TemporalQuality.UNRESOLVED_CLOCK

        return SensorMeasurement(
            measurement_id=meas_id,
            parameter_id=param_id,
            value=canonical_val,
            engineering_value=engineering_val,
            raw_signal=decoded_signal,
            unit_metadata=unit_meta,
            validity_status=ValidityStatus.VALID,
            temporal_quality=temp_quality,
            transformation_metadata=TransformationMetadata.NORMALIZED,
            integrity_status=integrity_status,
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

    def _build_invalid_measurement(
        self,
        meas_id: str,
        param_id: str,
        raw_signal: DecodedSignal,
        timestamps: TimestampModel,
        lineage: MeasurementLineage,
        validity_status: ValidityStatus,
        physical_origin: PhysicalOrigin,
        transport_protocol: TransportProtocol,
        processing_context: ProcessingContext,
        state_category: StateCategory,
        integrity_status: IntegrityStatus,
        classification: ParameterClassification,
        config_version: str,
        unit_meta: Optional[UnitNormalizer] = None,
        engineering_val: Optional[float] = None,
        canonical_val: Optional[float] = None,
    ) -> SensorMeasurement:
        if unit_meta is None:
            from src.module01.models.metadata import UnitMetadata
            unit_meta = UnitMetadata(
                raw_unit=raw_signal.raw_unit,
                engineering_unit="UNKNOWN",
                canonical_si_unit="UNKNOWN",
            )

        is_temp_valid = timestamps.normalized_source_utc is not None
        temp_quality = TemporalQuality.SYNCHRONIZED if is_temp_valid else TemporalQuality.UNRESOLVED_CLOCK

        return SensorMeasurement(
            measurement_id=meas_id,
            parameter_id=param_id,
            value=None,
            engineering_value=engineering_val,
            raw_signal=raw_signal,
            unit_metadata=unit_meta,
            validity_status=validity_status,
            temporal_quality=temp_quality,
            transformation_metadata=TransformationMetadata.NORMALIZED,
            integrity_status=integrity_status,
            is_physically_valid=False,
            is_temporally_valid=is_temp_valid,
            is_sync_eligible=False,
            physical_origin=physical_origin,
            transport_protocol=transport_protocol,
            processing_context=processing_context,
            state_category=state_category,
            timestamps=timestamps,
            lineage=lineage,
            classification=classification,
            config_version=config_version,
        )
