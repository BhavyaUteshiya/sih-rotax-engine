"""
Configuration-Driven Demonstration CAN Bus Decoder Implementation.
SIH26054 — Module 01 Data Acquisition & Ingestion.
"""

import struct
from typing import Any, Dict, List

from src.module01.decoding.interfaces import DecoderError, TelemetryDecoder
from src.module01.models.enums import TimestampDomain
from src.module01.models.metadata import DecodedSignal
from src.module01.models.raw_packet import DeepImmutableRawPacket, RawCanFrame


class CanDecoder(TelemetryDecoder):
    """
    Decodes RawCanFrame payloads into Layer 2 DecodedSignal objects using YAML CAN mappings.
    ⚠ DEMONSTRATION CAN MAPPINGS ONLY — DOES NOT CLAIM TO BE A PROPRIETARY DRDO ECU CAN BUS.
    """

    def __init__(self, can_mappings: Dict[str, Any]):
        self.can_mappings = can_mappings.get("messages", {})

    def decode(self, raw_packet: DeepImmutableRawPacket) -> List[DecodedSignal]:
        can_id_hex = raw_packet.metadata.get("can_id")
        if can_id_hex is None:
            raise DecoderError(f"RawPacket {raw_packet.packet_id} missing can_id in metadata")

        try:
            can_id = int(can_id_hex, 16) if isinstance(can_id_hex, str) else int(can_id_hex)
        except Exception as e:
            raise DecoderError(f"Invalid CAN ID format {can_id_hex}: {e}")

        msg_def = self.can_mappings.get(can_id)
        if msg_def is None:
            raise DecoderError(f"Unknown CAN ID: {hex(can_id)}")

        signals_def = msg_def.get("signals", {})
        payload = raw_packet.raw_bytes
        if len(payload) < msg_def.get("dlc", 0):
            raise DecoderError(f"Payload DLC mismatch for {hex(can_id)}: expected {msg_def.get('dlc')}, got {len(payload)}")

        decoded_signals: List[DecodedSignal] = []
        source_ts = raw_packet.source_timestamp if raw_packet.source_timestamp is not None else raw_packet.ingestion_timestamp_utc

        for param_id, sig in signals_def.items():
            start_bit = sig.get("start_bit", 0)
            bit_len = sig.get("bit_length", 16)
            byte_order = sig.get("byte_order", "LITTLE_ENDIAN")
            scale = sig.get("scale", 1.0)
            offset = sig.get("offset", 0.0)
            raw_unit = sig.get("raw_unit", "RAW")

            byte_offset = start_bit // 8
            byte_count = bit_len // 8

            if byte_offset + byte_count > len(payload):
                raise DecoderError(f"Signal {param_id} out of bounds in CAN payload {hex(can_id)}")

            sub_bytes = payload[byte_offset : byte_offset + byte_count]
            fmt = "<H" if byte_count == 2 else ("<B" if byte_count == 1 else "<I")
            if byte_order == "BIG_ENDIAN":
                fmt = fmt.replace("<", ">")

            raw_int = struct.unpack(fmt, sub_bytes)[0]

            # DecodedSignal.raw_numeric_value MUST be the unscaled integer value from CAN bytes
            decoded_signal = DecodedSignal(
                signal_id=f"sig_{raw_packet.packet_id}_{param_id}",
                parameter_id=param_id,
                raw_numeric_value=raw_int,       # Unscaled raw integer from CAN bytes
                raw_unit=raw_unit,
                source_timestamp=source_ts,
                source_timestamp_domain=TimestampDomain.UTC,
                raw_packet_id=raw_packet.packet_id,
                decoding_metadata={
                    "can_id": hex(can_id),
                    "raw_int": raw_int,
                    "scale": scale,
                    "offset": offset,
                },
            )
            decoded_signals.append(decoded_signal)

        return decoded_signals
