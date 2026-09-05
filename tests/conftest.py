"""
Pytest Fixtures for Module 01 Testing.
SIH26054 — Data Acquisition & Ingestion.
"""

import time
import pytest
from pathlib import Path
from tempfile import TemporaryDirectory

from src.module01.config.config_loader import ConfigLoader
from src.module01.models.enums import PhysicalOrigin, TransportProtocol
from src.module01.models.raw_packet import DeepImmutableRawPacket
from src.module01.pipeline.ingestion_pipeline import IngestionPipeline


@pytest.fixture
def temp_dir():
    with TemporaryDirectory() as tmp:
        yield Path(tmp)


@pytest.fixture
def config_loader():
    return ConfigLoader()


@pytest.fixture
def sample_raw_packet():
    now = time.time()
    mono = time.monotonic_ns()
    payload = b'{"engine_rpm": 5200.0, "cht_1": 145.0, "oil_pressure_bar": 4.2}'
    return DeepImmutableRawPacket.create(
        physical_origin=PhysicalOrigin.ECU,
        transport_protocol=TransportProtocol.CAN,
        stream_id="can0",
        sequence_number=101,
        raw_bytes=payload,
        ingestion_timestamp_utc=now,
        monotonic_ingestion_nanos=mono,
        source_timestamp=now,
    )
