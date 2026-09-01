"""
TelemetryFrame Model Specification (V4.3 Implementation Gate Approved).
SIH26054 — Module 01 Data Acquisition & Ingestion.
"""

from dataclasses import dataclass
from types import MappingProxyType
from typing import Dict, Optional

from src.module01.models.enums import ProcessingContext, StateCategory
from src.module01.models.metadata import FrameTime, SyncMetadata
from src.module01.models.sensor_sample import SensorMeasurement


@dataclass(frozen=True)
class TelemetryFrame:
    """
    Synchronized consumer transport view (aggregation) of SensorMeasurement instances aligned to a grid timestamp.
    
    CRITICAL MANDATORY INVARIANT:
    TelemetryFrame.state_category is strictly a derived summary / convenience metadata field.
    It MUST NOT override, replace, or be used as authoritative provenance for individual SensorMeasurement objects.
    Individual SensorMeasurement.state_category remains the sole authoritative state classification.
    Downstream modules MUST inspect SensorMeasurement.state_category when determining value provenance.
    """
    frame_id: str
    schema_version: str                          # e.g., "1.0.0"
    frame_time: FrameTime                        # Flexible multi-domain frame timestamp
    ingestion_timestamp_utc: float               # Host UTC epoch seconds recorded upon pipeline entry
    processing_context: ProcessingContext        # LIVE_STREAM, FLIGHT_REPLAY, SIMULATION_RUN
    state_category: StateCategory                # Derived summary convenience state (ACTUAL_MEASURED, DERIVED, SIMULATED)
    measurements: MappingProxyType               # Immutable map: parameter_id (str) -> SensorMeasurement
    sync_metadata: SyncMetadata                  # Frame alignment mode, grid dt, latency metrics

    @classmethod
    def create(
        cls,
        frame_id: str,
        frame_time: FrameTime,
        ingestion_timestamp_utc: float,
        processing_context: ProcessingContext,
        measurements_dict: Dict[str, SensorMeasurement],
        sync_metadata: SyncMetadata,
        schema_version: str = "1.0.0",
    ) -> "TelemetryFrame":
        """
        Factory method to construct TelemetryFrame with immutable measurements mapping proxy and derived convenience state_category.
        """
        frozen_measurements = MappingProxyType(dict(measurements_dict))

        # Derive summary convenience state_category
        # If all measurements are ACTUAL_MEASURED, frame state is ACTUAL_MEASURED.
        # Otherwise, frame state is DERIVED (or SIMULATED if all are SIMULATED).
        states = {m.state_category for m in measurements_dict.values()} if measurements_dict else {StateCategory.ACTUAL_MEASURED}
        if len(states) == 1:
            frame_state = next(iter(states))
        else:
            frame_state = StateCategory.DERIVED

        return cls(
            frame_id=frame_id,
            schema_version=schema_version,
            frame_time=frame_time,
            ingestion_timestamp_utc=ingestion_timestamp_utc,
            processing_context=processing_context,
            state_category=frame_state,
            measurements=frozen_measurements,
            sync_metadata=sync_metadata,
        )

    def get_measurement(self, parameter_id: str) -> Optional[SensorMeasurement]:
        """
        Retrieves a measurement by parameter_id. Downstream modules MUST inspect
        measurement.state_category for authoritative provenance truth.
        """
        return self.measurements.get(parameter_id)
