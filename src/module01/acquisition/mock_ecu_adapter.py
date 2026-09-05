"""
Mock ECU Adapter Implementation (Synthetic Provenance Compliant).
SIH26054 — Module 01 Data Acquisition & Ingestion.
"""

import json
import time
from typing import Any, Dict, Optional

from src.module01.acquisition.interfaces import EcuInterface
from src.module01.models.enums import PhysicalOrigin, ProcessingContext, StateCategory, TransportProtocol
from src.module01.models.raw_packet import DeepImmutableRawPacket


class MockEcuAdapter(EcuInterface):
    """
    Mock ECU Adapter generating JSON-serialized synthetic demonstration ECU telemetry packets.
    ⚠ DEMONSTRATION PURPOSES ONLY — DOES NOT CLAIM TO BE A REAL DRDO FADEC/ECU PROTOCOL.
    PROVENANCE: PhysicalOrigin.SIMULATOR, StateCategory.SIMULATED, ProcessingContext.SYNTHETIC_GENERATION.
    """

    def __init__(self, stream_id: str = "ecu_stream_0"):
        self.stream_id = stream_id
        self.is_connected = False
        self._sequence = 0

    def connect(self) -> bool:
        self.is_connected = True
        return True

    def read_telemetry(self) -> Optional[DeepImmutableRawPacket]:
        if not self.is_connected:
            return None

        self._sequence += 1
        now_utc = time.time()
        mono_nanos = time.monotonic_ns()

        payload_dict = {
            "sequence": self._sequence,
            "timestamp": now_utc,
            "engine_rpm": 5200.0,
            "cht_1": 145.0,
            "cht_2": 148.0,
            "cht_3": 146.0,
            "cht_4": 147.0,
            "egt_1": 780.0,
            "egt_2": 785.0,
            "egt_3": 782.0,
            "egt_4": 788.0,
            "oil_pressure_bar": 4.2,
            "oil_temp_degc": 95.0,
            "fuel_flow_kgh": 25.5,
            "vibration_rms": 12.5,
            "battery_voltage": 28.5,
            "alternator_current": 45.0,
            "injection_timing_deg": 22.5,
        }

        raw_bytes = json.dumps(payload_dict).encode("utf-8")

        return DeepImmutableRawPacket.create(
            physical_origin=PhysicalOrigin.SIMULATOR,
            transport_protocol=TransportProtocol.API,
            stream_id=self.stream_id,
            sequence_number=self._sequence,
            raw_bytes=raw_bytes,
            ingestion_timestamp_utc=now_utc,
            monotonic_ingestion_nanos=mono_nanos,
            source_timestamp=now_utc,
            metadata={
                "protocol": "JSON_ECU_V1",
                "state_category": StateCategory.SIMULATED.value,
                "processing_context": ProcessingContext.SYNTHETIC_GENERATION.value,
            },
        )

    def get_status(self) -> Dict[str, Any]:
        return {
            "stream_id": self.stream_id,
            "is_connected": self.is_connected,
            "sequence_count": self._sequence,
        }

    def disconnect(self) -> None:
        self.is_connected = False
