"""
CSV Payload Decoder Implementation.
SIH26054 — Module 01 Data Acquisition & Ingestion.
"""

from typing import Any, Dict, List

from src.module01.decoding.interfaces import DecoderError, TelemetryDecoder
from src.module01.decoding.json_decoder import JsonDecoder
from src.module01.models.metadata import DecodedSignal
from src.module01.models.raw_packet import DeepImmutableRawPacket


class CsvDecoder(TelemetryDecoder):
    """
    Decodes CSV-derived JSON row payloads into Layer 2 DecodedSignal objects.
    Reuses JsonDecoder mapping logic.
    """

    def __init__(self, sensor_definitions: Dict[str, Any]):
        self._json_decoder = JsonDecoder(sensor_definitions)

    def decode(self, raw_packet: DeepImmutableRawPacket) -> List[DecodedSignal]:
        return self._json_decoder.decode(raw_packet)
