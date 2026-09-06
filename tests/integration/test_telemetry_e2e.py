import unittest
import math
import hashlib

from src.digital_twin.telemetry.packet import TelemetryPacket
from src.digital_twin.telemetry.validator import TelemetryValidator
from src.digital_twin.telemetry.normalizer import TelemetryNormalizer
from src.digital_twin.telemetry.transport import InMemoryTransport, compute_payload_sha256
from src.digital_twin.telemetry.replay import DatasetReplayer

from src.digital_twin.models.operating_context import OperatingContext
from src.digital_twin.services.twin_engine import DigitalTwinEngine

class TestTelemetryE2E(unittest.TestCase):
    
    def setUp(self):
        self.dt_engine = DigitalTwinEngine()
        # Override debounce for immediate reactions
        for key in self.dt_engine.residual_analyzer.thresholds:
            self.dt_engine.residual_analyzer.thresholds[key]["debounce_sec"] = 0.0
            
    def _create_packet(self, seq=1, eng=1, ts=1.0, pid="rpm", val=3000.0) -> TelemetryPacket:
        return TelemetryPacket(
            simulation_timestamp=ts,
            engine_index=eng,
            parameter_id=pid,
            value=val,
            unit="unit",
            canonical_value=val,
            canonical_unit="unit",
            physical_origin="SIMULATOR",
            state_category="SIMULATED",
            processing_context="SYNTHETIC",
            sequence_number=seq
        )

    def test_full_transport_to_dt_engine(self):
        transport = InMemoryTransport()
        normalizer = TelemetryNormalizer()
        
        # 1. Serialization & Transport
        p1 = self._create_packet(seq=1, ts=1.0, pid="rpm", val=3000.0)
        p2 = self._create_packet(seq=1, ts=1.0, pid="map_bar", val=1.0)
        
        b1 = p1.to_json().encode('utf-8')
        b2 = p2.to_json().encode('utf-8')
        
        transport.send(b1)
        transport.send(b2)
        
        # 2. Deserialization & Normalization (Simulating sequence flush via sequence 2)
        p3 = self._create_packet(seq=2, ts=2.0, pid="rpm", val=3100.0)
        transport.send(p3.to_json().encode('utf-8'))
        
        frames = []
        while True:
            raw = transport.receive()
            if not raw:
                break
            
            # Transport Integrity Check
            self.assertEqual(raw.sha256_digest, compute_payload_sha256(raw.raw_bytes))
            
            # Deserialization
            packet = TelemetryPacket.from_json(raw.raw_bytes.decode('utf-8'))
            frames.extend(normalizer.ingest(packet))
            
        # We should have flushed sequence 1
        self.assertEqual(len(frames), 1)
        frame_seq1 = frames[0]
        
        # 3. DigitalTwinEngine Handoff
        ctx = OperatingContext(throttle_position=0.3)
        dt_state = self.dt_engine.process_step(
            operating_context=ctx,
            dt=0.1,
            observed_state=frame_seq1,
            engine_index=1,
            timestamp=frame_seq1.timestamp,
            sequence_number=frame_seq1.sequence_number
        )
        
        self.assertTrue(dt_state.synchronization_result.is_synchronized)
        self.assertEqual(dt_state.observed_state.rpm, 3000.0)
        self.assertEqual(dt_state.observed_state.map_bar, 1.0)
        # Partial telemetry missing fields check
        self.assertIsNone(dt_state.observed_state.cht_c)

    def test_invalid_telemetry_blocked(self):
        normalizer = TelemetryNormalizer()
        
        # NaN is blocked at TelemetryValidator
        p_nan = self._create_packet(seq=1, ts=1.0, pid="rpm", val=float('nan'))
        p_inf = self._create_packet(seq=1, ts=1.0, pid="map_bar", val=float('inf'))
        p_valid = self._create_packet(seq=1, ts=1.0, pid="torque_n_m", val=50.0)
        
        normalizer.ingest(p_nan)
        normalizer.ingest(p_inf)
        normalizer.ingest(p_valid)
        
        frames = normalizer.flush_all()
        self.assertEqual(len(frames), 1)
        
        frame = frames[0]
        # Valid passed through
        self.assertEqual(frame.torque_n_m, 50.0)
        # Invalid dropped natively
        self.assertIsNone(frame.rpm)
        self.assertIsNone(frame.map_bar)
        
        ctx = OperatingContext()
        dt_state = self.dt_engine.process_step(
            operating_context=ctx, dt=0.1, observed_state=frame,
            engine_index=1, timestamp=1.0, sequence_number=1
        )
        self.assertEqual(dt_state.observed_state.torque_n_m, 50.0)
        self.assertIsNone(dt_state.observed_state.rpm)

    def test_stale_telemetry_blocked(self):
        normalizer = TelemetryNormalizer()
        
        # Ingest sequence 2
        normalizer.ingest(self._create_packet(seq=2, ts=2.0, pid="rpm", val=3000.0))
        # Flush by ingesting sequence 3
        out = normalizer.ingest(self._create_packet(seq=3, ts=3.0, pid="rpm", val=3100.0))
        
        self.assertEqual(len(out), 1)
        self.assertEqual(out[0].sequence_number, 2)
        
        # Now late packet for sequence 1 arrives
        out_late = normalizer.ingest(self._create_packet(seq=1, ts=1.0, pid="rpm", val=2900.0))
        
        # Should be flushed as partial frame to be rejected by Phase 2 StateSynchronizer
        self.assertEqual(len(out_late), 1)
        self.assertEqual(out_late[0].sequence_number, 1)

    def test_multi_engine_isolation(self):
        normalizer = TelemetryNormalizer()
        
        # Engine 1 and Engine 2 send sequence 10
        normalizer.ingest(self._create_packet(seq=10, eng=1, pid="rpm", val=1000.0))
        normalizer.ingest(self._create_packet(seq=10, eng=2, pid="rpm", val=2000.0))
        
        # Flush both via sequence 11
        out = normalizer.ingest(self._create_packet(seq=11, eng=1, pid="rpm", val=1100.0))
        out.extend(normalizer.ingest(self._create_packet(seq=11, eng=2, pid="rpm", val=2100.0)))
        
        self.assertEqual(len(out), 2)
        
        # They must be independent
        eng1_frame = next(f for f in out if f.engine_id == "engine_1")
        eng2_frame = next(f for f in out if f.engine_id == "engine_2")
        
        self.assertEqual(eng1_frame.rpm, 1000.0)
        self.assertEqual(eng2_frame.rpm, 2000.0)

    def test_replay_e2e_path(self):
        replayer = DatasetReplayer()
        lines = [
            '{"timestamp": 10.0, "simulation_time": 10.0, "engine_id": "engine_1", "parameter_id": "rpm", "display_value": 3100.0, "canonical_value": 3100.0, "sequence_number": 1}',
            '{"timestamp": 10.0, "simulation_time": 10.0, "engine_id": "engine_1", "parameter_id": "map_bar", "display_value": 1.2, "canonical_value": 1.2, "sequence_number": 1}'
        ]
        
        frames = list(replayer.replay_jsonl(lines))
        self.assertEqual(len(frames), 1)
        
        ctx = OperatingContext()
        dt_state = self.dt_engine.process_step(
            operating_context=ctx,
            dt=0.1,
            observed_state=frames[0],
            engine_index=1,
            timestamp=10.0,
            sequence_number=1
        )
        
        self.assertTrue(dt_state.synchronization_result.is_synchronized)
        self.assertEqual(dt_state.observed_state.rpm, 3100.0)
        self.assertEqual(dt_state.observed_state.map_bar, 1.2)

    def test_replay_stale_rejection_and_streaming(self):
        replayer = DatasetReplayer()
        lines = [
            '{"timestamp": 12.0, "simulation_time": 12.0, "engine_id": "engine_1", "parameter_id": "rpm", "display_value": 3200.0, "canonical_value": 3200.0, "sequence_number": 3}',
            '{"timestamp": 10.0, "simulation_time": 10.0, "engine_id": "engine_1", "parameter_id": "rpm", "display_value": 3000.0, "canonical_value": 3000.0, "sequence_number": 1}',
            '{"timestamp": 13.0, "simulation_time": 13.0, "engine_id": "engine_1", "parameter_id": "rpm", "display_value": 3300.0, "canonical_value": 3300.0, "sequence_number": 4}'
        ]
        
        # Seq 3 arrives first, then seq 1 (stale), then seq 4 (flushes 3)
        frames = list(replayer.replay_jsonl(lines))
        
        # We expect three frames: seq 1 (flushed immediately as partial), seq 3 (flushed when 4 arrives), and seq 4.
        self.assertEqual(len(frames), 3)
        self.assertEqual(frames[0].sequence_number, 1)
        self.assertEqual(frames[0].rpm, 3000.0)
        self.assertEqual(frames[1].sequence_number, 3)
        self.assertEqual(frames[1].rpm, 3200.0)
        self.assertEqual(frames[2].sequence_number, 4)
        self.assertEqual(frames[2].rpm, 3300.0)

    def test_determinism(self):
        replayer = DatasetReplayer()
        lines = [
            '{"timestamp": 10.0, "simulation_time": 10.0, "engine_id": "engine_1", "parameter_id": "rpm", "display_value": 3100.0, "canonical_value": 3100.0, "sequence_number": 1}',
            '{"timestamp": 11.0, "simulation_time": 11.0, "engine_id": "engine_2", "parameter_id": "rpm", "display_value": 4100.0, "canonical_value": 4100.0, "sequence_number": 2}'
        ]
        
        frames1 = list(replayer.replay_jsonl(lines))
        frames2 = list(replayer.replay_jsonl(lines))
        
        # Identical input must yield identical Observation frames
        self.assertEqual(len(frames1), len(frames2))
        for f1, f2 in zip(frames1, frames2):
            self.assertEqual(f1.sequence_number, f2.sequence_number)
            self.assertEqual(f1.engine_id, f2.engine_id)
            self.assertEqual(f1.timestamp, f2.timestamp)
            self.assertEqual(f1.rpm, f2.rpm)

if __name__ == '__main__':
    unittest.main()
