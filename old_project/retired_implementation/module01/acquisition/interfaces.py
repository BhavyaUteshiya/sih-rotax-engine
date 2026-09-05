"""
Source Adapter Interfaces (Phase 5).
SIH26054 — Module 01 Data Acquisition & Ingestion.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, Generator, Optional

from src.module01.models.raw_packet import DeepImmutableRawPacket, RawCanFrame


class CanInterface(ABC):
    """Abstract interface for CAN bus communication."""

    @abstractmethod
    def connect(self) -> bool:
        """Establishes connection to physical or virtual CAN interface."""
        pass

    @abstractmethod
    def read_frame(self, timeout_seconds: float = 1.0) -> Optional[RawCanFrame]:
        """Reads a single RawCanFrame from the bus."""
        pass

    @abstractmethod
    def send_frame(self, can_id: int, payload: bytes, is_extended: bool = False) -> bool:
        """Sends a raw CAN payload onto the bus."""
        pass

    @abstractmethod
    def close(self) -> None:
        """Closes the CAN interface."""
        pass


class EcuInterface(ABC):
    """Abstract interface for ECU / FADEC telemetry communication."""

    @abstractmethod
    def connect(self) -> bool:
        """Establishes connection to ECU interface."""
        pass

    @abstractmethod
    def read_telemetry(self) -> Optional[DeepImmutableRawPacket]:
        """Reads a raw telemetry packet from the ECU stream."""
        pass

    @abstractmethod
    def get_status(self) -> Dict[str, Any]:
        """Returns ECU connection status metadata."""
        pass

    @abstractmethod
    def disconnect(self) -> None:
        """Disconnects from the ECU interface."""
        pass


class FileSourceInterface(ABC):
    """Abstract interface for historical log file sources (CSV / JSON)."""

    @abstractmethod
    def open(self) -> bool:
        """Opens the source file."""
        pass

    @abstractmethod
    def read_packet(self) -> Optional[DeepImmutableRawPacket]:
        """Reads the next record as a DeepImmutableRawPacket."""
        pass

    @abstractmethod
    def read_all(self) -> Generator[DeepImmutableRawPacket, None, None]:
        """Generates all records from the file."""
        pass

    @abstractmethod
    def close(self) -> None:
        """Closes the file source."""
        pass
