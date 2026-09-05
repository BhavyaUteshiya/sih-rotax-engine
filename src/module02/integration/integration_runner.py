"""
Master Integration Runner: Simulator -> Telemetry Transport -> Module 01 Ingestion -> Dataset Exporter.
SIH26054 — Module 02 Engine Simulator.
"""

from typing import Any, Dict, List, Optional, Tuple

from src.module01.models.sensor_sample import SensorMeasurement
from src.module01.pipeline.ingestion_pipeline import IngestionPipeline
from src.module02.config.config_loader import ConfigLoader
from src.module02.core.clock import SimulationClock
from src.module02.integration.can_transport import InMemoryTransport, SocketCANTransport, TelemetryTransport
from src.module02.integration.dataset_exporter import DatasetExporter, DatasetRecord
from src.module02.integration.module01_bridge import Module01Bridge
from src.module02.integration.telemetry_scheduler import TelemetryScheduler
from src.module02.simulation.thermodynamic_engine_runner import ThermodynamicEngineRunner


class MasterIntegrationRunner:
    """
    Master Integration Runner orchestrating continuous 100 Hz simulation,
    50 Hz CAN telemetry publishing, transport transmission, Module 01 ingestion,
    and downstream dataset export.
    """

    def __init__(
        self,
        integration_config: Optional[Dict[str, Any]] = None,
        transport_override: Optional[TelemetryTransport] = None,
        clock_dt: float = 0.01
    ) -> None:
        self.clock = SimulationClock(dt_seconds=clock_dt)
        self.simulator = ThermodynamicEngineRunner(clock=self.clock)

        # Setup Transport
        if transport_override is not None:
            self.transport = transport_override
        else:
            self.transport = InMemoryTransport(buffer_capacity=10000)

        # Setup Telemetry Scheduler (100 Hz physics, 50 Hz telemetry)
        self.scheduler = TelemetryScheduler(
            transport=self.transport,
            physics_rate_hz=100.0,
            telemetry_rate_hz=50.0
        )

        # Setup Module 01 Pipeline & Bridge
        self.pipeline = IngestionPipeline()
        self.bridge = Module01Bridge(pipeline=self.pipeline)
        self.exporter = DatasetExporter()

        self.recorded_dataset_records: List[DatasetRecord] = []
        self.run_id = "sim_run_001"

    def run_simulation(
        self,
        duration_sec: float,
        throttles: Dict[int, float],
        starter_commands: Dict[int, bool],
        flight_path_angle_rad: float = 0.0,
        scenario_id: str = "mission_stage"
    ) -> Dict[str, Any]:
        """
        Runs continuous simulation for duration_sec.
        Steps 100 Hz physics, samples 50 Hz CAN telemetry, transmits via transport,
        ingests into Module 01, and captures normalized dataset records.
        """
        dt = self.clock.dt_seconds
        steps = int(round(duration_sec / dt))

        for _ in range(steps):
            # 1. Step 100 Hz Physics
            sim_state = self.simulator.step_thermodynamic_cycle(
                throttles=throttles,
                starter_commands=starter_commands,
                flight_path_angle_rad=flight_path_angle_rad
            )

            # 2. Sample 50 Hz Telemetry & Send Across Transport
            published_frames = self.scheduler.step_physics_and_publish_telemetry(
                state=sim_state,
                simulation_time_sec=self.clock.simulation_time_sec
            )

            # 3. Receive CAN Frames from Transport Layer
            transport_frames = self.transport.receive_frames(max_frames=100)

            # 4. Ingest via Module 01 Bridge
            self.bridge.process_batch(transport_frames)

        # Collect normalized measurements from pipeline channel ring buffers for export
        self._collect_normalized_records(scenario_id=scenario_id)

        return self.get_metrics()

    def _collect_normalized_records(self, scenario_id: str = "mission") -> None:
        """Extracts validated normalized measurements from Module 01 buffers and creates DatasetRecords."""
        for sensor_id, ring_buffer in self.pipeline.channel_buffers.items():
            for meas in ring_buffer.get_all():
                record = DatasetExporter.create_record_from_measurement(
                    measurement=meas,
                    run_id=self.run_id,
                    scenario_id=scenario_id,
                    simulation_time=self.clock.simulation_time_sec
                )
                self.recorded_dataset_records.append(record)

    def export_datasets(self, csv_name: str = "telemetry_dataset.csv", jsonl_name: str = "telemetry_dataset.jsonl") -> Tuple[str, str]:
        """Exports collected dataset records to CSV and JSONL files."""
        csv_path = self.exporter.export_to_csv(self.recorded_dataset_records, filename=csv_name)
        jsonl_path = self.exporter.export_to_jsonl(self.recorded_dataset_records, filename=jsonl_name)
        return (csv_path, jsonl_path)

    def get_metrics(self) -> Dict[str, Any]:
        """Returns comprehensive integration metrics across all layers."""
        bridge_metrics = self.bridge.get_metrics()
        return {
            "run_id": self.run_id,
            "simulation_time_sec": self.clock.simulation_time_sec,
            "records_generated": self.scheduler.records_generated,
            "records_published": self.scheduler.records_published,
            "records_received": self.bridge.records_received,
            "records_ingested": self.bridge.records_ingested,
            "records_failed": self.bridge.records_failed,
            "records_dropped": self.scheduler.records_dropped,
            "records_persisted": bridge_metrics["module01_pipeline_metrics"].get("records_physically_valid_total", 0),
            "transport_metrics": self.transport.get_metrics() if isinstance(self.transport, InMemoryTransport) else {},
            "pipeline_metrics": bridge_metrics["module01_pipeline_metrics"]
        }
