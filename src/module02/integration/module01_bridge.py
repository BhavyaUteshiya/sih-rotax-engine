"""
Module 01 Bridge: Converts Encoded CAN Frames to Module 01 RawPackets and Ingests via Pipeline.
SIH26054 — Module 02 Engine Simulator.
"""

import time
from typing import Any, Dict, List, Optional

from src.module01.models.enums import PhysicalOrigin, ProcessingContext, StateCategory, TransportProtocol
from src.module01.models.raw_packet import DeepImmutableRawPacket
from src.module01.pipeline.ingestion_pipeline import IngestionPipeline
from src.module02.integration.can_transport import EncodedCanFrame


class Module01BridgeError(ValueError):
    """Raised when Module 01 bridge processing fails."""
    pass


class Module01Bridge:
    """
    Bridge coupling Module 02 Simulator CAN frames into Module 01's ingestion pipeline.
    CRITICAL MANDATE: Does NOT bypass Module 01. Telemetry passes through the identical acquisition,
    decoding, SI normalization, validity validation, and raw/normalized persistence path used for real telemetry.
    """

    def __init__(self, pipeline: Optional[IngestionPipeline] = None) -> None:
        self.pipeline = pipeline if pipeline is not None else IngestionPipeline()
        self.records_received = 0
        self.records_ingested = 0
        self.records_failed = 0

    def process_can_frame(self, frame: EncodedCanFrame) -> bool:
        """
        Converts an EncodedCanFrame into Module 01 DeepImmutableRawPacket and executes
        IngestionPipeline.ingest_raw_packet(packet).
        Preserves strict simulator provenance metadata.
        """
        self.records_received += 1

        ingestion_utc = time.time()
        monotonic_nanos = time.monotonic_ns()

        metadata_dict = {
            "can_id": hex(frame.can_id),
            "dlc": frame.dlc,
            "state_category": "SIMULATED",
            "physical_origin": "SIMULATOR",
            "processing_context": "SYNTHETIC_GENERATION",
            "engine_index": frame.engine_index,
        }

        packet = DeepImmutableRawPacket.create(
            physical_origin=PhysicalOrigin.SIMULATOR,
            transport_protocol=TransportProtocol.CAN,
            stream_id=frame.stream_id,
            sequence_number=frame.sequence_number,
            raw_bytes=frame.payload,
            ingestion_timestamp_utc=ingestion_utc,
            monotonic_ingestion_nanos=monotonic_nanos,
            source_timestamp=frame.source_timestamp,
            metadata=metadata_dict
        )

        # Enforce Payload SHA-256 Wire Integrity Verification
        if packet.payload_sha256 != frame.payload_sha256:
            self.records_failed += 1
            raise Module01BridgeError(
                f"Payload SHA-256 mismatch for packet {packet.packet_id}: "
                f"expected {frame.payload_sha256}, got {packet.payload_sha256}"
            )

        # Feed packet through Module 01's 4-stage ingestion pipeline
        success = self.pipeline.ingest_raw_packet(packet)
        if success:
            self.records_ingested += 1
        else:
            self.records_failed += 1

        return success

    def process_batch(self, frames: List[EncodedCanFrame]) -> int:
        """Processes a list of EncodedCanFrame objects through Module 01 pipeline."""
        count = 0
        for f in frames:
            if self.process_can_frame(f):
                count += 1
        return count

    def get_metrics(self) -> Dict[str, Any]:
        """Returns bridge ingestion metrics and Module 01 pipeline metrics."""
        pipeline_metrics = self.pipeline.get_ingestion_metrics()
        return {
            "bridge_records_received": self.records_received,
            "bridge_records_ingested": self.records_ingested,
            "bridge_records_failed": self.records_failed,
            "module01_pipeline_metrics": pipeline_metrics
        }
