"""
Clock Mapping & Timestamp Transformation Architecture (Phase 8 Correction).
SIH26054 — Module 01 Data Acquisition & Ingestion.
"""

import time
from typing import Optional

from src.module01.models.enums import TimestampDomain
from src.module01.models.metadata import ClockMapping, TimestampModel


class ClockMapper:
    """
    Manages clock calibration mappings and converts multi-domain source timestamps to UTC epoch seconds.
    Enforces V4.3 timestamp rules: NEVER fabricate UTC if mapping is unavailable/invalid.
    """

    def __init__(self, default_clock_mapping: Optional[ClockMapping] = None):
        self.clock_mapping = default_clock_mapping

    def set_clock_mapping(self, mapping: ClockMapping) -> None:
        self.clock_mapping = mapping

    def map_to_utc(
        self,
        source_timestamp: float,
        domain: TimestampDomain,
        ingestion_utc: Optional[float] = None,
    ) -> Optional[float]:
        """
        Converts source_timestamp in given domain to normalized UTC epoch seconds.
        Formula:
        t_utc = reference_utc + (source_timestamp - reference_source_timestamp) * (1 + drift_rate_ppm / 1e6) + offset_seconds
        Returns None if mapping is unresolvable, expired, or confidence is low (< 0.5).
        """
        if domain == TimestampDomain.UTC:
            return float(source_timestamp)

        if self.clock_mapping is None:
            return None

        now_utc = ingestion_utc if ingestion_utc is not None else time.time()

        # Check mapping expiration & confidence threshold
        if now_utc > self.clock_mapping.valid_until_utc:
            return None
        if self.clock_mapping.confidence < 0.5:
            return None

        # Apply exact V4.3 drift & offset conversion formula
        ref_src = self.clock_mapping.reference_source_timestamp
        ref_utc = self.clock_mapping.reference_utc
        drift_factor = 1.0 + (self.clock_mapping.drift_rate_ppm / 1000000.0)
        offset = self.clock_mapping.offset_seconds

        delta = source_timestamp - ref_src
        normalized_utc = ref_utc + (delta * drift_factor) + offset
        return normalized_utc

    def create_timestamp_model(
        self,
        source_timestamp: float,
        domain: TimestampDomain,
        ingestion_utc: float,
        monotonic_nanos: int,
        mission_start_utc: Optional[float] = None,
    ) -> TimestampModel:
        """
        Creates TimestampModel with multi-domain tracking and unresolvable UTC handling.
        """
        norm_utc = self.map_to_utc(source_timestamp, domain, ingestion_utc)
        processing_utc = time.time()

        mission_elapsed = None
        if mission_start_utc is not None:
            ref_ts = norm_utc if norm_utc is not None else (source_timestamp if domain == TimestampDomain.MISSION_TIME else None)
            if ref_ts is not None:
                mission_elapsed = max(0.0, ref_ts - mission_start_utc)

        return TimestampModel(
            source_timestamp=source_timestamp,
            source_timestamp_domain=domain,
            normalized_source_utc=norm_utc,
            ingestion_timestamp_utc=ingestion_utc,
            processing_timestamp_utc=processing_utc,
            monotonic_ingestion_nanos=monotonic_nanos,
            mission_start_timestamp_utc=mission_start_utc,
            mission_elapsed_seconds=mission_elapsed,
            clock_mapping=self.clock_mapping,
        )
