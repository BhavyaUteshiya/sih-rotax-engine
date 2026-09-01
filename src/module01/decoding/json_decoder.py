"""
JSON Payload Decoder Implementation.
SIH26054 — Module 01 Data Acquisition & Ingestion.
"""

import json
from typing import Any, Dict, List

from src.module01.decoding.interfaces import DecoderError, TelemetryDecoder
from src.module01.models.enums import TimestampDomain
from src.module01.models.metadata import DecodedSignal
from src.module01.models.raw_packet import DeepImmutableRawPacket


class JsonDecoder(TelemetryDecoder):
    """
    Decodes JSON-serialized raw payloads into Layer 2 DecodedSignal objects.
    """

    def __init__(self, sensor_definitions: Dict[str, Any]):
        self.sensor_defs = sensor_definitions.get("sensors", {})

    def decode(self, raw_packet: DeepImmutableRawPacket) -> List[DecodedSignal]:
        try:
            payload_str = raw_packet.raw_bytes.decode("utf-8")
            data = json.loads(payload_str)
            if not isinstance(data, dict):
                raise DecoderError("JSON payload must be a key-value dictionary")
        except Exception as e:
            raise DecoderError(f"Failed to parse JSON payload in packet {raw_packet.packet_id}: {e}")

        source_ts = raw_packet.source_timestamp if raw_packet.source_timestamp is not None else raw_packet.ingestion_timestamp_utc
        decoded_signals: List[DecodedSignal] = []

        # Map JSON keys to parameters
        key_mapping = {
            "engine_rpm": "engine.rpm",
            "cht_1": "engine.cylinder.1.cht",
            "cht_2": "engine.cylinder.2.cht",
            "cht_3": "engine.cylinder.3.cht",
            "cht_4": "engine.cylinder.4.cht",
            "egt_1": "engine.cylinder.1.egt",
            "egt_2": "engine.cylinder.2.egt",
            "egt_3": "engine.cylinder.3.egt",
            "egt_4": "engine.cylinder.4.egt",
            "oil_pressure_bar": "engine.oil.pressure",
            "oil_temp_degc": "engine.oil.temperature",
            "fuel_flow_kgh": "engine.fuel.flow",
            "battery_voltage": "electrical.battery.voltage",
            "alternator_current": "electrical.alternator.current",
            "injection_timing_deg": "engine.injection.timing",
            "vibration_rms": "engine.vibration.rms",
        }

        for json_key, val in data.items():
            if json_key in ("sequence", "timestamp"):
                continue

            param_id = key_mapping.get(json_key, json_key)
            sensor_info = self.sensor_defs.get(param_id, {})
            raw_unit = sensor_info.get("raw_unit", "RAW")

            try:
                numeric_val = float(val)
            except (ValueError, TypeError):
                continue

            decoded_signal = DecodedSignal(
                signal_id=f"sig_{raw_packet.packet_id}_{param_id}",
                parameter_id=param_id,
                raw_numeric_value=numeric_val,
                raw_unit=raw_unit,
                source_timestamp=source_ts,
                source_timestamp_domain=TimestampDomain.UTC,
                raw_packet_id=raw_packet.packet_id,
                decoding_metadata={"json_key": json_key},
            )
            decoded_signals.append(decoded_signal)

        return decoded_signals
