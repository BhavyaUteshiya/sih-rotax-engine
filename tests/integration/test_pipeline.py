"""
Integration Tests for End-to-End Ingestion Pipeline (Synthetic Provenance Compliant).
SIH26054 — Module 01 Data Acquisition & Ingestion.
"""

import time
import unittest
from src.module01.acquisition.mock_can_adapter import DemonstrationCanAdapter
from src.module01.acquisition.mock_ecu_adapter import MockEcuAdapter
from src.module01.config.config_loader import ConfigLoader
from src.module01.models.enums import PhysicalOrigin, StateCategory
from src.module01.pipeline.ingestion_pipeline import IngestionPipeline


class TestPipeline(unittest.TestCase):
    def test_end_to_end_mock_can_pipeline_flow(self):
        loader = ConfigLoader()
        pipeline = IngestionPipeline(config_loader=loader)

        can_adapter = DemonstrationCanAdapter()
        can_adapter.connect()

        for _ in range(6):
            raw_frame = can_adapter.read_frame()
            self.assertIsNotNone(raw_frame)
            success = pipeline.ingest_raw_packet(raw_frame.raw_packet)
            self.assertTrue(success)

        can_adapter.close()

        now = time.time()
        frame = pipeline.generate_and_publish_frame(target_grid_utc=now, causal_mode=True)
        self.assertIsNotNone(frame)

        rpm_meas = frame.get_measurement("engine.rpm")
        self.assertIsNotNone(rpm_meas)
        self.assertEqual(rpm_meas.engineering_value, 5200.0)
        self.assertEqual(rpm_meas.unit_metadata.canonical_si_unit, "RAD_PER_SEC")
        # Synthetic demonstration provenance compliance
        self.assertEqual(rpm_meas.physical_origin, PhysicalOrigin.SIMULATOR)
        self.assertEqual(rpm_meas.state_category, StateCategory.SIMULATED)

        oil_press = frame.get_measurement("engine.oil.pressure")
        self.assertIsNotNone(oil_press)
        self.assertEqual(oil_press.engineering_value, 4.2)
        self.assertEqual(oil_press.unit_metadata.canonical_si_unit, "PASCAL")

        metrics = pipeline.get_ingestion_metrics()
        self.assertEqual(metrics["records_received_total"], 6)
        self.assertTrue(metrics["records_physically_valid_total"] > 0)

    def test_end_to_end_mock_ecu_pipeline_flow(self):
        loader = ConfigLoader()
        pipeline = IngestionPipeline(config_loader=loader)

        ecu_adapter = MockEcuAdapter()
        ecu_adapter.connect()

        packet = ecu_adapter.read_telemetry()
        self.assertIsNotNone(packet)
        success = pipeline.ingest_raw_packet(packet)
        self.assertTrue(success)

        ecu_adapter.disconnect()

        now = time.time()
        frame = pipeline.generate_and_publish_frame(target_grid_utc=now, causal_mode=True)
        self.assertIsNotNone(frame)

        cht1 = frame.get_measurement("engine.cylinder.1.cht")
        self.assertIsNotNone(cht1)
        self.assertEqual(cht1.engineering_value, 145.0)
        self.assertEqual(cht1.unit_metadata.canonical_si_unit, "KELVIN")
        self.assertAlmostEqual(cht1.value, 418.15, places=3)
        # Synthetic demonstration provenance compliance
        self.assertEqual(cht1.physical_origin, PhysicalOrigin.SIMULATOR)
        self.assertEqual(cht1.state_category, StateCategory.SIMULATED)
