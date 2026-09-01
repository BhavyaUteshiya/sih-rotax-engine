"""
Vibration Telemetry Data Models.
SIH26054 — Module 01 Data Acquisition & Ingestion.
"""

from dataclasses import dataclass
from types import MappingProxyType
from typing import Any, Dict, Optional

from src.module01.models.metadata import MeasurementLineage
from src.module01.models.sensor_sample import SensorMeasurement


@dataclass(frozen=True)
class ScalarVibrationContainer:
    """Container for tri-axial scalar vibration metrics (RMS and Peak acceleration)."""
    vibration_x: Optional[SensorMeasurement] = None
    vibration_y: Optional[SensorMeasurement] = None
    vibration_z: Optional[SensorMeasurement] = None
    vibration_rms: Optional[SensorMeasurement] = None
    vibration_peak: Optional[SensorMeasurement] = None


@dataclass(frozen=True)
class VibrationWaveformChunk:
    """
    High-frequency raw accelerometer waveform packet (e.g. 10 kHz).
    Preserved separately from low-rate telemetry frames to prevent forced downsampling.
    """
    chunk_id: str
    channel_id: str                              # e.g., "vibration.front_bearing.accel_z"
    sampling_rate_hz: float                      # e.g., 10000.0 Hz
    start_timestamp_utc: float                   # UTC timestamp of first sample
    sample_count: int                            # Number of samples (e.g. 1024)
    raw_samples: bytes                           # Binary array of float32 accelerometer values (m/s^2)
    lineage: MeasurementLineage                  # Ancestry link to DeepImmutableRawPacket
    window_metadata: MappingProxyType            # Window function info (e.g., Hanning, rectangle)

    @classmethod
    def create(
        cls,
        chunk_id: str,
        channel_id: str,
        sampling_rate_hz: float,
        start_timestamp_utc: float,
        sample_count: int,
        raw_samples: bytes,
        lineage: MeasurementLineage,
        window_metadata: Optional[Dict[str, Any]] = None,
    ) -> "VibrationWaveformChunk":
        meta = MappingProxyType(window_metadata if window_metadata is not None else {})
        return cls(
            chunk_id=chunk_id,
            channel_id=channel_id,
            sampling_rate_hz=sampling_rate_hz,
            start_timestamp_utc=start_timestamp_utc,
            sample_count=sample_count,
            raw_samples=bytes(raw_samples),
            lineage=lineage,
            window_metadata=meta,
        )
