"""
Module 01 End-to-End Execution Demonstration Script (V4.3 Final Cleanup).
SIH26054 — Module 01 Data Acquisition & Ingestion.
"""

import sys
from pathlib import Path

# Add project root to sys.path
root_dir = Path(__file__).resolve().parent.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

import json
import time
from src.module01.acquisition.mock_can_adapter import DemonstrationCanAdapter
from src.module01.acquisition.mock_ecu_adapter import MockEcuAdapter
from src.module01.config.config_loader import ConfigLoader
from src.module01.pipeline.ingestion_pipeline import IngestionPipeline
from src.module01.utils.logger import get_logger

logger = get_logger("run_ingestion_demo")


def main():
    print("==========================================================================")
    print("SIH26054 — MODULE 01 DATA ACQUISITION & INGESTION DEMONSTRATION")
    print("Aero Piston Engine Digital Twin Data Pipeline")
    print("==========================================================================\n")

    loader = ConfigLoader()
    pipeline = IngestionPipeline(config_loader=loader)

    print("1. Starting Demonstration CAN Adapter and Mock ECU Stream...")
    can_adapter = DemonstrationCanAdapter(stream_id="can0")
    can_adapter.connect()

    ecu_adapter = MockEcuAdapter(stream_id="ecu0")
    ecu_adapter.connect()

    print("2. Ingesting Raw Telemetry Packets (Raw Immutability & SHA-256)...")
    for i in range(9):
        if i % 2 == 0:
            frame = can_adapter.read_frame()
            if frame:
                pipeline.ingest_raw_packet(frame.raw_packet)
        else:
            packet = ecu_adapter.read_telemetry()
            if packet:
                pipeline.ingest_raw_packet(packet)
        time.sleep(0.01)

    can_adapter.close()
    ecu_adapter.disconnect()

    print("3. Generating Synchronized TelemetryFrame v1.0.0 Snapshot...")
    now = time.time()
    frame = pipeline.generate_and_publish_frame(target_grid_utc=now, causal_mode=True)

    print("\n--------------------------------------------------------------------------")
    print(f"TELEMETRY FRAME SNAPSHOT (ID: {frame.frame_id}, Schema: {frame.schema_version})")
    print(f"Frame Time (UTC): {frame.frame_time.primary_timestamp:.6f}")
    print(f"Alignment Mode: {frame.sync_metadata.alignment_mode}")
    print(f"Sync Quality Score: {frame.sync_metadata.sync_quality_score * 100:.1f}%")
    print(f"Frame Summary State Category (Convenience Metadata): {frame.state_category.value}")
    print("--------------------------------------------------------------------------\n")

    print(f"{'PARAMETER ID':<30} | {'DISPLAY VAL':<12} | {'CANONICAL SI VALUE':<20} | {'ORIGIN':<10} | {'STATE CATEGORY':<16} | {'VALIDITY'}")
    print("-" * 110)

    for param_id, meas in frame.measurements.items():
        disp = f"{meas.engineering_value:.1f} {meas.unit_metadata.engineering_unit}" if meas.engineering_value is not None else "N/A"
        si_val = f"{meas.value:.4f} {meas.unit_metadata.canonical_si_unit}" if meas.value is not None else "N/A"
        print(f"{param_id:<30} | {disp:<12} | {si_val:<20} | {meas.physical_origin.value:<10} | {meas.state_category.value:<16} | {meas.validity_status.value}")

    print("\n--------------------------------------------------------------------------")
    print("PIPELINE OBSERVABILITY METRICS SUMMARY:")
    metrics = pipeline.get_ingestion_metrics()
    print(json.dumps(metrics, indent=2))
    print("--------------------------------------------------------------------------\n")

    print("PIPELINE PROCESSING STATUS: SUCCESS")
    storage_failures = metrics.get("storage_failures_total", 0)
    recovery_state = metrics.get("storage_recovery_state", "NORMAL")

    if storage_failures > 0 or recovery_state != "NORMAL":
        print(f"PERSISTENCE STATUS: DEGRADED (Storage failures: {storage_failures})")
        print(f"RECOVERY STATE: {recovery_state}")
    else:
        print("PERSISTENCE STATUS: SUCCESS")
        print("RECOVERY STATE: NORMAL")

    print("\nDemonstration execution finished.")


if __name__ == "__main__":
    main()
