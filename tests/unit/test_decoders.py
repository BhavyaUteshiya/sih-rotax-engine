"""
Unit Tests for Protocol Decoders (CAN, JSON, CSV).
SIH26054 — Module 01 Data Acquisition & Ingestion.
"""

import struct
import time
import pytest
from src.module01.config.config_loader import ConfigLoader
from src.module01.decoding.can_decoder import CanDecoder
from src.module01.decoding.json_decoder import JsonDecoder
from src.module01.models.enums import PhysicalOrigin, TransportProtocol
from src.module01.models.raw_packet import DeepImmutableRawPacket


def test_can_decoder_unscaled_raw_value(config_loader):
    can_mappings = config_loader.load_can_mappings()
    decoder = CanDecoder(can_mappings)

    # 0x101: ECU_ENGINE_STATUS_1 (RPM=5200, OilPress=420, FuelFlow=2550)
    payload = struct.pack("<HHH", 5200, 420, 2550) + b"\x00\x00"
    now = time.time()
    packet = DeepImmutableRawPacket.create(
        physical_origin=PhysicalOrigin.SIMULATOR,
        transport_protocol=TransportProtocol.CAN,
        stream_id="can0",
        sequence_number=1,
        raw_bytes=payload,
        ingestion_timestamp_utc=now,
        monotonic_ingestion_nanos=time.monotonic_ns(),
        metadata={"can_id": "0x101"},
    )

    signals = decoder.decode(packet)
    assert len(signals) == 3
    params = {s.parameter_id: s.raw_numeric_value for s in signals}
    # DecodedSignal.raw_numeric_value MUST be unscaled integer from CAN bytes
    assert params["engine.rpm"] == 5200
    assert params["engine.oil.pressure"] == 420
    assert params["engine.fuel.flow"] == 2550


def test_json_decoder_success(config_loader):
    sensor_defs = config_loader.load_sensor_definitions()
    decoder = JsonDecoder(sensor_defs)

    now = time.time()
    payload_bytes = b'{"engine_rpm": 5200.0, "cht_1": 145.0, "oil_pressure_bar": 4.2}'
    packet = DeepImmutableRawPacket.create(
        physical_origin=PhysicalOrigin.SIMULATOR,
        transport_protocol=TransportProtocol.API,
        stream_id="ecu0",
        sequence_number=1,
        raw_bytes=payload_bytes,
        ingestion_timestamp_utc=now,
        monotonic_ingestion_nanos=time.monotonic_ns(),
        metadata={"protocol": "JSON_ECU_V1"},
    )

    signals = decoder.decode(packet)
    assert len(signals) == 3
    params = {s.parameter_id: s.raw_numeric_value for s in signals}
    assert params["engine.rpm"] == 5200.0
    assert params["engine.cylinder.1.cht"] == 145.0
    assert params["engine.oil.pressure"] == 4.2
