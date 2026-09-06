from typing import Dict, List, Optional
from src.digital_twin.telemetry.packet import TelemetryPacket
from src.digital_twin.telemetry.validator import TelemetryValidator
from src.digital_twin.models.observed_state import ObservedState

class TelemetryNormalizer:
    """
    Normalizes valid TelemetryPackets into Phase 2 ObservedState frames.
    
    Frame Assembly Policy (Flush-on-Strictly-Greater-Sequence):
    1. Packets are buffered by sequence_number.
    2. When a packet with a strictly greater sequence number than the currently 
       buffering sequence(s) arrives, the oldest buffered sequence is flushed 
       into an ObservedState.
    3. Stale packets (sequence_number < current) are immediately flushed as 
       partial frames to preserve transparency; the downstream Phase 2 
       StateSynchronizer will correctly reject them as OUT_OF_ORDER.
    4. An explicit flush() method allows flushing the current active frame.
    """
    def __init__(self):
        # Buffer keyed by (engine_index, sequence_number)
        self._buffers: Dict[tuple[int, int], List[TelemetryPacket]] = {}
        # Highest sequence seen per engine
        self._highest_sequence: Dict[int, int] = {}

    def ingest(self, packet: TelemetryPacket) -> List[ObservedState]:
        """
        Ingests a packet. Returns a list of completely assembled ObservedState 
        frames that are ready for handoff (usually 0 or 1).
        """
        flushed_frames = []
        
        # Validation
        is_valid, _ = TelemetryValidator.is_valid(packet)
        if not is_valid:
            return []

        seq = packet.sequence_number
        eng = packet.engine_index
        highest_seq = self._highest_sequence.get(eng, -1)
        
        # If it's a stale packet (arrived after we already flushed its sequence),
        # flush it immediately as a partial frame so Phase 2 StateSynchronizer 
        # can correctly reject it as OUT_OF_ORDER, preserving transparency.
        if seq < highest_seq:
            temp_key = (eng, seq)
            self._buffers[temp_key] = [packet]
            return [self._flush_sequence(temp_key)]

        # Flush older sequences if a newer one arrives for this engine
        if seq > highest_seq:
            for (b_eng, b_seq) in sorted(list(self._buffers.keys())):
                if b_eng == eng and b_seq < seq:
                    flushed_frames.append(self._flush_sequence((b_eng, b_seq)))
            self._highest_sequence[eng] = seq
            
        # Buffer the current packet
        key = (eng, seq)
        if key not in self._buffers:
            self._buffers[key] = []
            
        # P1 Fix: Prevent unbounded buffer growth (OOM protection)
        # If a sequence receives an absurd number of packets without advancing, drop them.
        if len(self._buffers[key]) < 100:
            self._buffers[key].append(packet)

        return flushed_frames

    def flush_all(self) -> List[ObservedState]:
        """Explicitly flushes all remaining buffers."""
        flushed_frames = []
        for key in sorted(list(self._buffers.keys())):
            flushed_frames.append(self._flush_sequence(key))
        return flushed_frames

    def _flush_sequence(self, key: tuple[int, int]) -> ObservedState:
        packets = self._buffers.pop(key)
        sequence_number = key[1]
        
        # Base metadata from the first packet
        first = packets[0]
        engine_id = f"engine_{first.engine_index}"
        timestamp = first.simulation_timestamp
        
        # Construct parameters
        kwargs = {}
        
        import dataclasses
        valid_fields = {f.name for f in dataclasses.fields(ObservedState)}
        
        for p in packets:
            # Only map known parameters, skipping metadata fields
            if p.parameter_id in valid_fields and p.parameter_id not in ["timestamp", "sequence_number", "engine_id", "aircraft_id", "data_quality", "valid_sensors_count", "corrupted_sensors_count"]:
                # P2 Fix: Duplicates overwrite safely in dict.
                kwargs[p.parameter_id] = p.canonical_value
                
        # P2 Fix: Count unique sensors safely populated in kwargs
        valid_count = len(kwargs)
                
        # We don't invent data quality logic; if we have at least one valid parameter, 
        # we consider it GOOD for telemetry ingestion (the downstream core re-evaluates).
        # We set valid_sensors_count so Phase 2 processes it correctly.
        kwargs["data_quality"] = "GOOD" if valid_count > 0 else "INSUFFICIENT_DATA"
        kwargs["valid_sensors_count"] = valid_count

        return ObservedState(
            timestamp=timestamp,
            sequence_number=sequence_number,
            engine_id=engine_id,
            **kwargs
        )
