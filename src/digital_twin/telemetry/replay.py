import json
import csv
from typing import List, Iterable, Union, TextIO, Iterator

from src.digital_twin.telemetry.packet import TelemetryPacket
from src.digital_twin.telemetry.normalizer import TelemetryNormalizer
from src.digital_twin.models.observed_state import ObservedState

class DatasetReplayer:
    """
    Replay mechanism that reads exported telemetry datasets (JSONL or CSV)
    and streams them sequentially into the TelemetryNormalizer to reconstruct 
    deterministic ObservedState frames for downstream ingestion.
    """
    
    @staticmethod
    def _parse_engine_id(engine_id: str) -> int:
        """Parses 'engine_1' -> 1"""
        if engine_id.startswith("engine_"):
            return int(engine_id.split("_")[1])
        return 1
        
    @staticmethod
    def _create_packet_from_dict(row: dict) -> TelemetryPacket:
        """Shared parser path for both JSONL and CSV rows."""
        # Convert types as CSV yields strings
        return TelemetryPacket(
            simulation_timestamp=float(row["simulation_time"]),
            engine_index=DatasetReplayer._parse_engine_id(row["engine_id"]),
            parameter_id=row["parameter_id"],
            value=float(row["display_value"]) if row.get("display_value") is not None and row.get("display_value") != "" else None,
            unit=row.get("display_unit", ""),
            canonical_value=float(row["canonical_value"]) if row.get("canonical_value") is not None and row.get("canonical_value") != "" else None,
            canonical_unit=row.get("canonical_unit", ""),
            physical_origin=row.get("physical_origin", "SIMULATOR"),
            state_category=row.get("state_category", "SIMULATED"),
            processing_context="REPLAY",
            sequence_number=int(row["sequence_number"])
        )

    def replay_jsonl(self, file_or_iterable: Iterable[str]) -> Iterator[ObservedState]:
        """Parses a JSONL stream and yields frames sequentially."""
        normalizer = TelemetryNormalizer()
        for line in file_or_iterable:
            line = line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
                packet = self._create_packet_from_dict(row)
                for frame in normalizer.ingest(packet):
                    yield frame
            except (ValueError, TypeError, KeyError):
                pass
                
        for frame in normalizer.flush_all():
            yield frame

    def replay_csv(self, file_or_iterable: Iterable[str]) -> Iterator[ObservedState]:
        """Parses a CSV stream and yields frames sequentially."""
        normalizer = TelemetryNormalizer()
        for row in csv.DictReader(file_or_iterable):
            try:
                packet = self._create_packet_from_dict(row)
                for frame in normalizer.ingest(packet):
                    yield frame
            except (ValueError, TypeError, KeyError):
                pass
                
        for frame in normalizer.flush_all():
            yield frame
