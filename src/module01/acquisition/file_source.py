"""
Historical File Log Source Implementation (CSV / JSON).
SIH26054 — Module 01 Data Acquisition & Ingestion.
"""

import csv
import json
from pathlib import Path
import time
from typing import Any, Dict, Generator, List, Optional

from src.module01.acquisition.interfaces import FileSourceInterface
from src.module01.models.enums import PhysicalOrigin, ProcessingContext, TransportProtocol
from src.module01.models.raw_packet import DeepImmutableRawPacket


class CSVFileSource(FileSourceInterface):
    """CSV historical telemetry file reader."""

    def __init__(self, file_path: Path, stream_id: str = "csv_file_stream"):
        self.file_path = Path(file_path).resolve()
        self.stream_id = stream_id
        self._file_obj = None
        self._csv_reader = None
        self._sequence = 0

    def open(self) -> bool:
        if not self.file_path.exists():
            return False
        self._file_obj = open(self.file_path, "r", encoding="utf-8")
        self._csv_reader = csv.DictReader(self._file_obj)
        self._sequence = 0
        return True

    def read_packet(self) -> Optional[DeepImmutableRawPacket]:
        if self._csv_reader is None:
            return None

        try:
            row = next(self._csv_reader)
        except StopIteration:
            return None

        self._sequence += 1
        now_utc = time.time()
        mono_nanos = time.monotonic_ns()
        raw_bytes = json.dumps(row).encode("utf-8")

        # Parse source timestamp if present
        source_ts = float(row.get("timestamp", now_utc)) if "timestamp" in row else None

        return DeepImmutableRawPacket.create(
            physical_origin=PhysicalOrigin.UNKNOWN,
            transport_protocol=TransportProtocol.FILE,
            stream_id=self.stream_id,
            sequence_number=self._sequence,
            raw_bytes=raw_bytes,
            ingestion_timestamp_utc=now_utc,
            monotonic_ingestion_nanos=mono_nanos,
            source_timestamp=source_ts,
            metadata={
                "file_path": str(self.file_path),
                "row_num": self._sequence,
                "processing_context": ProcessingContext.HISTORICAL_FILE.value,
            },
        )

    def read_all(self) -> Generator[DeepImmutableRawPacket, None, None]:
        if not self.open():
            return
        try:
            while True:
                packet = self.read_packet()
                if packet is None:
                    break
                yield packet
        finally:
            self.close()

    def close(self) -> None:
        if self._file_obj:
            self._file_obj.close()
            self._file_obj = None
            self._csv_reader = None


class JSONFileSource(FileSourceInterface):
    """JSON Lines / JSON Array historical telemetry file reader."""

    def __init__(self, file_path: Path, stream_id: str = "json_file_stream"):
        self.file_path = Path(file_path).resolve()
        self.stream_id = stream_id
        self._records: List[Dict[str, Any]] = []
        self._index = 0
        self._sequence = 0

    def open(self) -> bool:
        if not self.file_path.exists():
            return False
        with open(self.file_path, "r", encoding="utf-8") as f:
            content = f.read().strip()
            if content.startswith("["):
                self._records = json.loads(content)
            else:
                self._records = [json.loads(line) for line in content.splitlines() if line.strip()]
        self._index = 0
        self._sequence = 0
        return True

    def read_packet(self) -> Optional[DeepImmutableRawPacket]:
        if self._index >= len(self._records):
            return None

        record = self._records[self._index]
        self._index += 1
        self._sequence += 1

        now_utc = time.time()
        mono_nanos = time.monotonic_ns()
        raw_bytes = json.dumps(record).encode("utf-8")
        source_ts = float(record.get("timestamp", now_utc)) if "timestamp" in record else None

        return DeepImmutableRawPacket.create(
            physical_origin=PhysicalOrigin.UNKNOWN,
            transport_protocol=TransportProtocol.FILE,
            stream_id=self.stream_id,
            sequence_number=self._sequence,
            raw_bytes=raw_bytes,
            ingestion_timestamp_utc=now_utc,
            monotonic_ingestion_nanos=mono_nanos,
            source_timestamp=source_ts,
            metadata={
                "file_path": str(self.file_path),
                "record_num": self._sequence,
                "processing_context": ProcessingContext.HISTORICAL_FILE.value,
            },
        )

    def read_all(self) -> Generator[DeepImmutableRawPacket, None, None]:
        if not self.open():
            return
        try:
            while True:
                packet = self.read_packet()
                if packet is None:
                    break
                yield packet
        finally:
            self.close()

    def close(self) -> None:
        self._records = []
        self._index = 0
