"""
Telemetry Decoder Abstract Interfaces (Phase 6).
SIH26054 — Module 01 Data Acquisition & Ingestion.
"""

from abc import ABC, abstractmethod
from typing import List

from src.module01.models.metadata import DecodedSignal
from src.module01.models.raw_packet import DeepImmutableRawPacket


class DecoderError(Exception):
    """Exception raised when raw payload decoding fails."""
    pass


class TelemetryDecoder(ABC):
    """Abstract interface for raw payload decoders."""

    @abstractmethod
    def decode(self, raw_packet: DeepImmutableRawPacket) -> List[DecodedSignal]:
        """
        Decodes a DeepImmutableRawPacket into a list of Layer 2 DecodedSignal objects.
        Must raise DecoderError on corrupt payloads.
        """
        pass
