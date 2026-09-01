"""
Public API Interfaces & Module 02 / Module 03 Contracts (V4.3 Final Cleanup).
SIH26054 — Module 01 Data Acquisition & Ingestion.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Callable, Dict, Iterator, List, Optional

from src.module01.models.enums import TimestampDomain
from src.module01.models.metadata import MeasurementLineage
from src.module01.models.raw_packet import DeepImmutableRawPacket
from src.module01.models.sensor_sample import SensorMeasurement
from src.module01.models.telemetry_frame import TelemetryFrame


@dataclass(frozen=True)
class TimeRange:
    """Typed time range query structure supporting multi-domain timestamps."""
    start_time: float
    end_time: float
    timestamp_domain: TimestampDomain = TimestampDomain.UTC


class TelemetryIngestor(ABC):
    """Public interface for ingesting raw telemetry packets into Module 01."""

    @abstractmethod
    def ingest_raw_packet(self, packet: DeepImmutableRawPacket) -> bool:
        """Ingests a raw packet into the pipeline. Returns True if accepted."""
        pass


class TelemetryPublisher(ABC):
    """Interface for publishing TelemetryFrame snapshots to internal subscribers."""

    @abstractmethod
    def publish_frame(self, frame: TelemetryFrame) -> None:
        """Publishes a synchronized TelemetryFrame to active subscribers."""
        pass


class TelemetryConsumer(ABC):
    """Public interface for downstream consumers to query TelemetryFrame snapshots."""

    @abstractmethod
    def get_latest_frame(self) -> Optional[TelemetryFrame]:
        """Returns the most recent TelemetryFrame snapshot."""
        pass

    @abstractmethod
    def get_frame_range(self, time_range: TimeRange, causal_mode: bool = True) -> List[TelemetryFrame]:
        """Queries synchronized TelemetryFrame snapshots within the specified TimeRange."""
        pass


class LineageResolver(ABC):
    """Interface for resolving forensic packet and measurement lineage."""

    @abstractmethod
    def resolve_raw_packet(self, raw_packet_id: str) -> Optional[DeepImmutableRawPacket]:
        """Retrieves raw packet by packet_id."""
        pass

    @abstractmethod
    def resolve_measurement_lineage(self, measurement_id: str) -> Optional[MeasurementLineage]:
        """Retrieves 4-stage processing lineage for a measurement_id."""
        pass


class MetricsProvider(ABC):
    """Interface for retrieving real-time ingestion observability metrics."""

    @abstractmethod
    def get_ingestion_metrics(self) -> Dict[str, Any]:
        """Returns snapshot dictionary of active pipeline metrics."""
        pass


# =====================================================================
# MODULE 02 CONTRACT (Simulation & Replay Interface)
# =====================================================================

class ISimulationTelemetrySink(ABC):
    """
    Interface for Module 02 Physics Simulator to inject simulated telemetry streams into Module 01.
    Module 01 preserves PhysicalOrigin.SIMULATOR and StateCategory.SIMULATED flags intact.
    """

    @abstractmethod
    def inject_simulated_measurement(self, measurement: SensorMeasurement) -> bool:
        """Injects a single simulated measurement into Module 01."""
        pass

    @abstractmethod
    def inject_simulated_frame(self, frame: TelemetryFrame) -> bool:
        """Injects a simulated TelemetryFrame into Module 01."""
        pass


class IReplayTelemetryProvider(ABC):
    """
    Interface contract for Module 02 Replay engine to read historical telemetry streams.
    NOTE: Module 01 provides this interface contract only. Mission-aware historical replay,
    time-sync replay, and physics reconstruction are deferred to Module 02.
    """

    @abstractmethod
    def get_historical_stream(self, mission_id: str, time_range: TimeRange) -> Iterator[TelemetryFrame]:
        """Demonstration placeholder method contract for Module 02 historical replay retrieval."""
        pass


# =====================================================================
# MODULE 03 CONTRACT (Digital Twin Core Interface)
# =====================================================================

class IDigitalTwinTelemetryStream(ABC):
    """
    Interface for Module 03 Digital Twin Core to consume real-time ACTUAL_MEASURED telemetry.
    Module 01 publishes actual telemetry. Module 01 DOES NOT store estimated Twin states.
    """

    @abstractmethod
    def subscribe_actual_state(self, callback: Callable[[TelemetryFrame], None]) -> str:
        """Subscribes callback function to real-time TelemetryFrame stream. Returns subscription ID."""
        pass

    @abstractmethod
    def unsubscribe(self, subscription_id: str) -> bool:
        """Unsubscribes callback by subscription ID."""
        pass
