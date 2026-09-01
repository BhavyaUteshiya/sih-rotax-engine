"""
Dataset Exporter: Converts Validated Module 01 Telemetry into ML & Digital-Twin Ready Datasets (CSV & JSONL).
SIH26054 — Module 02 Engine Simulator.
"""

import csv
import json
import os
from dataclasses import asdict, dataclass
from typing import Any, Dict, List, Optional

from src.module01.models.sensor_sample import SensorMeasurement


@dataclass(frozen=True)
class DatasetRecord:
    """Standardized Machine-Learning & Digital-Twin Ready Telemetry Dataset Record."""
    timestamp: float
    simulation_time: float
    run_id: str
    engine_id: str
    parameter_id: str
    display_value: float
    display_unit: str
    canonical_value: float
    canonical_unit: str
    validity: str
    state_category: str
    physical_origin: str
    scenario_id: str
    sequence_number: int
    schema_version: str = "1.0.0"


class DatasetExporter:
    """
    Downstream Exporter transforming validated normalized SensorMeasurement objects from Module 01
    into standardized CSV and JSONL telemetry datasets for Digital Twin Core ingestion and replay.
    """

    def __init__(self, output_dir: str = "data/exports") -> None:
        self.output_dir = output_dir
        os.makedirs(self.output_dir, exist_ok=True)

    @classmethod
    def create_record_from_measurement(
        cls,
        measurement: SensorMeasurement,
        run_id: str = "run_001",
        scenario_id: str = "mission_demo",
        simulation_time: Optional[float] = None
    ) -> DatasetRecord:
        """Converts a Module 01 SensorMeasurement object into a DatasetRecord."""
        ts = measurement.timestamps.normalized_source_utc if measurement.timestamps.normalized_source_utc is not None else measurement.timestamps.source_timestamp
        ts_val = float(ts) if ts is not None else 0.0
        sim_time = float(simulation_time) if simulation_time is not None else ts_val
        eng_id = f"engine_{measurement.lineage.engine_index}" if hasattr(measurement.lineage, "engine_index") and measurement.lineage.engine_index else "engine_1"

        disp_unit = measurement.unit_metadata.engineering_unit if measurement.unit_metadata else "RAW"
        canon_unit = measurement.unit_metadata.canonical_si_unit if measurement.unit_metadata else "RAW"

        return DatasetRecord(
            timestamp=ts_val,
            simulation_time=sim_time,
            run_id=run_id,
            engine_id=eng_id,
            parameter_id=measurement.parameter_id,
            display_value=float(measurement.engineering_value) if measurement.engineering_value is not None else 0.0,
            display_unit=disp_unit,
            canonical_value=float(measurement.value) if measurement.value is not None else 0.0,
            canonical_unit=canon_unit,
            validity=measurement.validity_status.value if hasattr(measurement.validity_status, "value") else str(measurement.validity_status),
            state_category=measurement.state_category.value if hasattr(measurement.state_category, "value") else str(measurement.state_category),
            physical_origin=measurement.physical_origin.value if hasattr(measurement.physical_origin, "value") else str(measurement.physical_origin),
            scenario_id=scenario_id,
            sequence_number=measurement.lineage.sequence_number if hasattr(measurement.lineage, "sequence_number") else 0,
            schema_version="1.0.0"
        )

    def export_to_csv(self, records: List[DatasetRecord], filename: str = "telemetry_dataset.csv") -> str:
        """Exports dataset records to CSV format."""
        filepath = os.path.join(self.output_dir, filename)
        fieldnames = [
            "timestamp", "simulation_time", "run_id", "engine_id", "parameter_id",
            "display_value", "display_unit", "canonical_value", "canonical_unit",
            "validity", "state_category", "physical_origin", "scenario_id",
            "sequence_number", "schema_version"
        ]

        with open(filepath, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for r in records:
                writer.writerow(asdict(r))

        return filepath

    def export_to_jsonl(self, records: List[DatasetRecord], filename: str = "telemetry_dataset.jsonl") -> str:
        """Exports dataset records to JSONL format."""
        filepath = os.path.join(self.output_dir, filename)

        with open(filepath, "w", encoding="utf-8") as f:
            for r in records:
                f.write(json.dumps(asdict(r)) + "\n")

        return filepath
