"""
TimestampSynchronizer Service Implementation (Phase 13 Compliance Fix).
SIH26054 — Module 01 Data Acquisition & Ingestion.
"""

import time
from typing import Dict, List, Optional

from src.module01.buffering.ring_buffer import RingBuffer
from src.module01.models.enums import (
    AlignmentMethod,
    ProcessingContext,
    TemporalQuality,
    TimestampDomain,
    TransformationMetadata,
)
from src.module01.models.metadata import AlignmentMetadata, FrameTime, SyncMetadata
from src.module01.models.sensor_sample import SensorMeasurement
from src.module01.models.telemetry_frame import TelemetryFrame


class SynchronizationError(Exception):
    """Exception raised when synchronization rule invariants are violated."""
    pass


class TimestampSynchronizer:
    """
    On-demand temporal synchronization service generating consumer TelemetryFrame snapshots.
    Supports REALTIME_CAUSAL_MODE and OFFLINE_REPLAY_MODE.
    """

    def __init__(self, staleness_limit_seconds: float = 5.0):
        self.staleness_limit = staleness_limit_seconds

    def generate_frame(
        self,
        target_grid_timestamp_utc: float,
        channel_buffers: Dict[str, RingBuffer],
        causal_mode: bool = True,
        grid_domain: TimestampDomain = TimestampDomain.UTC,
        processing_context: ProcessingContext = ProcessingContext.LIVE_STREAM,
        mission_start_utc: Optional[float] = None,
        clock_mapping_version: str = "1.0.0",
        frame_id: Optional[str] = None,
    ) -> TelemetryFrame:
        """
        Generates a synchronized TelemetryFrame at target_grid_timestamp_utc.
        Enforces causal invariants: in REALTIME_CAUSAL_MODE, LINEAR_INTERPOLATE is strictly FORBIDDEN.
        """
        now_utc = time.time()
        fid = frame_id if frame_id is not None else f"frame_{int(target_grid_timestamp_utc * 1000)}"

        aligned_measurements: Dict[str, SensorMeasurement] = {}
        total_channels = len(channel_buffers)
        valid_channels = 0

        for param_id, buffer in channel_buffers.items():
            samples = buffer.get_all()
            aligned_meas = self._align_channel(
                param_id=param_id,
                samples=samples,
                target_grid_time=target_grid_timestamp_utc,
                causal_mode=causal_mode,
                grid_domain=grid_domain,
            )
            if aligned_meas is not None:
                aligned_measurements[param_id] = aligned_meas
                if aligned_meas.is_physically_valid and aligned_meas.is_sync_eligible:
                    valid_channels += 1

        sync_score = (valid_channels / total_channels) if total_channels > 0 else 0.0
        mission_elapsed = (target_grid_timestamp_utc - mission_start_utc) if mission_start_utc is not None else None

        frame_time = FrameTime(
            primary_timestamp=target_grid_timestamp_utc,
            primary_timestamp_domain=grid_domain,
            normalized_utc=target_grid_timestamp_utc if grid_domain == TimestampDomain.UTC else None,
            mission_elapsed_seconds=mission_elapsed,
            sync_quality_score=sync_score,
            clock_mapping_version=clock_mapping_version,
        )

        mode_str = "REALTIME_CAUSAL" if causal_mode else "OFFLINE_REPLAY"
        sync_meta = SyncMetadata(
            alignment_mode=mode_str,
            target_grid_dt=0.02,                # Default 50 Hz grid dt (20 ms)
            sync_quality_score=sync_score,
            total_channels=total_channels,
            valid_channels=valid_channels,
            latency_ms=(now_utc - target_grid_timestamp_utc) * 1000.0,
        )

        return TelemetryFrame.create(
            frame_id=fid,
            frame_time=frame_time,
            ingestion_timestamp_utc=now_utc,
            processing_context=processing_context,
            measurements_dict=aligned_measurements,
            sync_metadata=sync_meta,
        )

    def _align_channel(
        self,
        param_id: str,
        samples: List[SensorMeasurement],
        target_grid_time: float,
        causal_mode: bool,
        grid_domain: TimestampDomain,
    ) -> Optional[SensorMeasurement]:
        """
        Aligns a single channel to target_grid_time following causal / offline rules.
        CRITICAL V4.3 INVARIANT: Consumes ONLY samples where is_sync_eligible == True.
        """
        if not samples:
            return None

        # Filter sync-eligible samples STRICTLY
        sync_eligible_samples = [s for s in samples if s.is_sync_eligible and s.is_physically_valid]
        if not sync_eligible_samples:
            return None

        def get_ts(s: SensorMeasurement) -> float:
            return s.timestamps.normalized_source_utc if s.timestamps.normalized_source_utc is not None else s.timestamps.source_timestamp

        # Sort samples by event timestamp
        sorted_samples = sorted(sync_eligible_samples, key=get_ts)

        # Check for EXACT match
        for s in sorted_samples:
            if abs(get_ts(s) - target_grid_time) < 1e-6:
                align_meta = AlignmentMetadata(
                    alignment_method=AlignmentMethod.EXACT,
                    target_grid_timestamp=target_grid_time,
                    target_domain=grid_domain,
                    sample_timestamps_used=(get_ts(s),),
                    time_distance_seconds=0.0,
                    is_causal=causal_mode,
                )
                return self._copy_with_alignment(s, AlignmentMethod.EXACT, align_meta)

        # Separate into past samples (t <= target_grid_time) and future samples (t > target_grid_time)
        past_samples = [s for s in sorted_samples if get_ts(s) <= target_grid_time]
        future_samples = [s for s in sorted_samples if get_ts(s) > target_grid_time]

        if causal_mode:
            # REALTIME_CAUSAL_MODE: Look-ahead strictly PROHIBITED!
            if not past_samples:
                return None  # No past sample available

            latest_past = past_samples[-1]
            time_dist = target_grid_time - get_ts(latest_past)

            if time_dist > self.staleness_limit:
                align_meta = AlignmentMetadata(
                    alignment_method=AlignmentMethod.HOLD_LAST,
                    target_grid_timestamp=target_grid_time,
                    target_domain=grid_domain,
                    sample_timestamps_used=(get_ts(latest_past),),
                    time_distance_seconds=time_dist,
                    is_causal=True,
                )
                return self._copy_with_alignment(latest_past, AlignmentMethod.HOLD_LAST, align_meta, temporal_quality=TemporalQuality.STALE)
            else:
                align_meta = AlignmentMetadata(
                    alignment_method=AlignmentMethod.HOLD_LAST,
                    target_grid_timestamp=target_grid_time,
                    target_domain=grid_domain,
                    sample_timestamps_used=(get_ts(latest_past),),
                    time_distance_seconds=time_dist,
                    is_causal=True,
                )
                return self._copy_with_alignment(latest_past, AlignmentMethod.HOLD_LAST, align_meta)

        else:
            # OFFLINE_REPLAY_MODE: Retrospective interpolation permitted
            if past_samples and future_samples:
                prev_s = past_samples[-1]
                next_s = future_samples[0]
                t_prev = get_ts(prev_s)
                t_next = get_ts(next_s)
                dt = t_next - t_prev

                if dt > 1e-6 and prev_s.value is not None and next_s.value is not None:
                    # Linear interpolation calculation
                    factor = (target_grid_time - t_prev) / dt
                    interp_value = prev_s.value + factor * (next_s.value - prev_s.value)
                    interp_eng = prev_s.engineering_value + factor * (next_s.engineering_value - prev_s.engineering_value) if (prev_s.engineering_value is not None and next_s.engineering_value is not None) else interp_value

                    align_meta = AlignmentMetadata(
                        alignment_method=AlignmentMethod.LINEAR_INTERPOLATE,
                        target_grid_timestamp=target_grid_time,
                        target_domain=grid_domain,
                        sample_timestamps_used=(t_prev, t_next),
                        time_distance_seconds=min(target_grid_time - t_prev, t_next - target_grid_time),
                        is_causal=False,
                    )

                    return SensorMeasurement(
                        measurement_id=f"interp_{prev_s.measurement_id}_{next_s.measurement_id}",
                        parameter_id=prev_s.parameter_id,
                        value=interp_value,
                        engineering_value=interp_eng,
                        raw_signal=None,
                        unit_metadata=prev_s.unit_metadata,
                        validity_status=prev_s.validity_status,
                        temporal_quality=TemporalQuality.SYNCHRONIZED,
                        transformation_metadata=TransformationMetadata.INTERPOLATED,
                        integrity_status=prev_s.integrity_status,
                        is_physically_valid=True,
                        is_temporally_valid=True,
                        is_sync_eligible=True,
                        physical_origin=prev_s.physical_origin,
                        transport_protocol=prev_s.transport_protocol,
                        processing_context=prev_s.processing_context,
                        state_category=prev_s.state_category,
                        timestamps=prev_s.timestamps,
                        lineage=prev_s.lineage,
                        alignment_metadata=align_meta,
                        classification=prev_s.classification,
                        config_version=prev_s.config_version,
                    )

            if past_samples:
                latest_past = past_samples[-1]
                time_dist = target_grid_time - get_ts(latest_past)
                align_meta = AlignmentMetadata(
                    alignment_method=AlignmentMethod.HOLD_LAST,
                    target_grid_timestamp=target_grid_time,
                    target_domain=grid_domain,
                    sample_timestamps_used=(get_ts(latest_past),),
                    time_distance_seconds=time_dist,
                    is_causal=False,
                )
                return self._copy_with_alignment(latest_past, AlignmentMethod.HOLD_LAST, align_meta)

            return None

    def _copy_with_alignment(
        self,
        sample: SensorMeasurement,
        method: AlignmentMethod,
        align_meta: AlignmentMetadata,
        temporal_quality: TemporalQuality = TemporalQuality.SYNCHRONIZED,
    ) -> SensorMeasurement:
        trans_meta = TransformationMetadata.HELD if method == AlignmentMethod.HOLD_LAST else TransformationMetadata.NORMALIZED
        return SensorMeasurement(
            measurement_id=sample.measurement_id,
            parameter_id=sample.parameter_id,
            value=sample.value,
            engineering_value=sample.engineering_value,
            raw_signal=sample.raw_signal,
            unit_metadata=sample.unit_metadata,
            validity_status=sample.validity_status,
            temporal_quality=temporal_quality,
            transformation_metadata=trans_meta,
            integrity_status=sample.integrity_status,
            is_physically_valid=sample.is_physically_valid,
            is_temporally_valid=sample.is_temporally_valid,
            is_sync_eligible=sample.is_sync_eligible,
            physical_origin=sample.physical_origin,
            transport_protocol=sample.transport_protocol,
            processing_context=sample.processing_context,
            state_category=sample.state_category,
            timestamps=sample.timestamps,
            lineage=sample.lineage,
            alignment_metadata=align_meta,
            classification=sample.classification,
            config_version=sample.config_version,
        )
