"""
Integration Tests for End-to-End Ingestion Pipeline (Synthetic Provenance Compliant).
SIH26054 — Module 01 Data Acquisition & Ingestion.
"""

import time
import pytest
from src.module01.acquisition.mock_can_adapter import DemonstrationCanAdapter
from src.module01.acquisition.mock_ecu_adapter import MockEcuAdapter
from src.module01.config.config_loader import ConfigLoader
from src.module01.models.enums import PhysicalOrigin, StateCategory
from src.module01.pipeline.ingestion_pipeline import IngestionPipeline


def test_end_to_end_mock_can_pipeline_flow(temp_dir):
    loader = ConfigLoader()
    pipeline = IngestionPipeline(config_loader=loader)

    can_adapter = DemonstrationCanAdapter()
    can_adapter.connect()

    for _ in range(6):
        raw_frame = can_adapter.read_frame()
        assert raw_frame is not None
        success = pipeline.ingest_raw_packet(raw_frame.raw_packet)
        assert success is True

    can_adapter.close()

    now = time.time()
    frame = pipeline.generate_and_publish_frame(target_grid_utc=now, causal_mode=True)
    assert frame is not None

    rpm_meas = frame.get_measurement("engine.rpm")
    assert rpm_meas is not None
    assert rpm_meas.engineering_value == 5200.0
    assert rpm_meas.unit_metadata.canonical_si_unit == "RAD_PER_SEC"
    # Synthetic demonstration provenance compliance
    assert rpm_meas.physical_origin == PhysicalOrigin.SIMULATOR
    assert rpm_meas.state_category == StateCategory.SIMULATED

    oil_press = frame.get_measurement("engine.oil.pressure")
    assert oil_press is not None
    assert oil_press.engineering_value == 4.2
    assert oil_press.unit_metadata.canonical_si_unit == "PASCAL"

    metrics = pipeline.get_ingestion_metrics()
    assert metrics["records_received_total"] == 6
    assert metrics["records_physically_valid_total"] > 0


def test_end_to_end_mock_ecu_pipeline_flow(temp_dir):
    loader = ConfigLoader()
    pipeline = IngestionPipeline(config_loader=loader)

    ecu_adapter = MockEcuAdapter()
    ecu_adapter.connect()

    packet = ecu_adapter.read_telemetry()
    assert packet is not None
    success = pipeline.ingest_raw_packet(packet)
    assert success is True

    ecu_adapter.disconnect()

    now = time.time()
    frame = pipeline.generate_and_publish_frame(target_grid_utc=now, causal_mode=True)
    assert frame is not None

    cht1 = frame.get_measurement("engine.cylinder.1.cht")
    assert cht1 is not None
    assert cht1.engineering_value == 145.0
    assert cht1.unit_metadata.canonical_si_unit == "KELVIN"
    assert cht1.value == pytest.approx(418.15, rel=1e-5)
    # Synthetic demonstration provenance compliance
    assert cht1.physical_origin == PhysicalOrigin.SIMULATOR
    assert cht1.state_category == StateCategory.SIMULATED
