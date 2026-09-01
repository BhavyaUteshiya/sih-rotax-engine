"""
Demonstration CAN Bus Adapter Implementation (Synthetic Provenance Compliant).
SIH26054 — Module 01 Data Acquisition & Ingestion.
"""

import struct
import time
from typing import Optional

from src.module01.acquisition.interfaces import CanInterface
from src.module01.models.enums import PhysicalOrigin, ProcessingContext, StateCategory, TransportProtocol
from src.module01.models.raw_packet import DeepImmutableRawPacket, RawCanFrame


class DemonstrationCanAdapter(CanInterface):
    """
    Demonstration CAN Adapter generating synthetic CAN frames based on demonstration mappings.
    ⚠ DEMONSTRATION PURPOSES ONLY — DOES NOT CLAIM TO BE REAL DRDO AIRCRAFT HARDWARE.
    PROVENANCE: PhysicalOrigin.SIMULATOR, StateCategory.SIMULATED, ProcessingContext.SYNTHETIC_GENERATION.
    """

    def __init__(self, interface_name: str = "vcan0", stream_id: str = "can0"):
        self.interface_name = interface_name
        self.stream_id = stream_id
        self.is_connected = False
        self._sequence = 0

    def connect(self) -> bool:
        self.is_connected = True
        return True

    def read_frame(self, timeout_seconds: float = 1.0) -> Optional[RawCanFrame]:
        if not self.is_connected:
            return None

        self._sequence += 1
        now_utc = time.time()
        mono_nanos = time.monotonic_ns()

        # Cycle through demonstration messages 0x101, 0x102, 0x103
        msg_type = (self._sequence % 3)
        if msg_type == 1:
            # 0x101: ECU_ENGINE_STATUS_1 (RPM=5200, OilPress=4.2bar -> 420, FuelFlow=25.5kg/h -> 2550)
            can_id = 0x101
            payload = struct.pack("<HHH", 5200, 420, 2550) + b"\x00\x00"
        elif msg_type == 2:
            # 0x102: ECU_TEMPERATURES_1 (CHT1=145.0°C -> +40=185 -> 1850, CHT2=148.0°C -> 1880, OilTemp=95.0°C -> 1350)
            can_id = 0x102
            payload = struct.pack("<HHH", 1850, 1880, 1350) + b"\x00\x00"
        else:
            # 0x103: ECU_ELECTRICAL_STATUS (BattVolt=28.5V -> 2850, AltCurr=45.0A -> 450)
            can_id = 0x103
            payload = struct.pack("<HH", 2850, 450) + b"\x00\x00\x00\x00"

        raw_packet = DeepImmutableRawPacket.create(
            physical_origin=PhysicalOrigin.SIMULATOR,
            transport_protocol=TransportProtocol.CAN,
            stream_id=self.stream_id,
            sequence_number=self._sequence,
            raw_bytes=payload,
            ingestion_timestamp_utc=now_utc,
            monotonic_ingestion_nanos=mono_nanos,
            source_timestamp=now_utc,
            metadata={
                "can_id": hex(can_id),
                "interface": self.interface_name,
                "state_category": StateCategory.SIMULATED.value,
                "processing_context": ProcessingContext.SYNTHETIC_GENERATION.value,
            },
        )

        return RawCanFrame(
            raw_packet=raw_packet,
            can_id=can_id,
            dlc=len(payload),
            is_extended=False,
            interface_name=self.interface_name,
        )

    def send_frame(self, can_id: int, payload: bytes, is_extended: bool = False) -> bool:
        if not self.is_connected:
            return False
        return True

    def close(self) -> None:
        self.is_connected = False
