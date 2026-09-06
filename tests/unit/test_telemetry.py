import unittest
import math
import json
import dataclasses

from src.digital_twin.telemetry.packet import TelemetryPacket
from src.digital_twin.telemetry.validator import TelemetryValidator
from src.digital_twin.telemetry.normalizer import TelemetryNormalizer

class TestTelemetry(unittest.TestCase):
    
    def create_packet(self, seq=1, ts=1.0, pid="rpm", val=3000.0) -> TelemetryPacket:
        return TelemetryPacket(
            simulation_timestamp=ts,
            engine_index=1,
            parameter_id=pid,
            value=val,
            unit="rpm",
            canonical_value=val,
            canonical_unit="rpm",
            physical_origin="SIMULATOR",
            state_category="SIMULATED",
            processing_context="SYNTHETIC",
            sequence_number=seq
        )

    # --- PACKET & SERIALIZATION ---
    def test_serialization(self):
        packet = self.create_packet()
        j = packet.to_json()
        self.assertIn("rpm", j)
        p2 = TelemetryPacket.from_json(j)
        self.assertEqual(packet.sequence_number, p2.sequence_number)
        self.assertEqual(packet.value, p2.value)

    # --- VALIDATION ---
    def test_validation_valid_numeric(self):
        p = self.create_packet(val=150.5)
        is_valid, reason = TelemetryValidator.is_valid(p)
        self.assertTrue(is_valid)
        
    def test_validation_zero(self):
        p = self.create_packet(val=0.0)
        is_valid, reason = TelemetryValidator.is_valid(p)
        self.assertTrue(is_valid)

    def test_validation_nan(self):
        p = self.create_packet(val=float('nan'))
        is_valid, reason = TelemetryValidator.is_valid(p)
        self.assertFalse(is_valid)

    def test_validation_inf(self):
        p = self.create_packet(val=float('inf'))
        is_valid, reason = TelemetryValidator.is_valid(p)
        self.assertFalse(is_valid)
        
        p = self.create_packet(val=float('-inf'))
        is_valid, _ = TelemetryValidator.is_valid(p)
        self.assertFalse(is_valid)

    def test_validation_malformed_type(self):
        p = self.create_packet(val="3000") # string instead of float
        is_valid, reason = TelemetryValidator.is_valid(p)
        self.assertFalse(is_valid)

    def test_validation_missing_value(self):
        p = self.create_packet()
        # Dataclass is frozen, need to bypass or create new
        p = TelemetryPacket(
            simulation_timestamp=1.0, engine_index=1, parameter_id="rpm",
            value=None, unit="rpm", canonical_value=None, canonical_unit="rpm",
            physical_origin="SIMULATOR", state_category="SIMULATED",
            processing_context="SYNTHETIC", sequence_number=1
        )
        is_valid, reason = TelemetryValidator.is_valid(p)
        self.assertFalse(is_valid)

    def test_validation_timestamp(self):
        # 0.0 is valid
        p = self.create_packet(ts=0.0)
        self.assertTrue(TelemetryValidator.is_valid(p)[0])
        
        # finite is valid
        p = self.create_packet(ts=123.45)
        self.assertTrue(TelemetryValidator.is_valid(p)[0])

        # nan is invalid
        p = self.create_packet(ts=float('nan'))
        self.assertFalse(TelemetryValidator.is_valid(p)[0])

        # string is invalid
        p = self.create_packet(ts="1.0")
        self.assertFalse(TelemetryValidator.is_valid(p)[0])
        
    def test_validation_sequence(self):
        p = self.create_packet(seq=None)
        self.assertFalse(TelemetryValidator.is_valid(p)[0])

    # --- NORMALIZATION ---
    def test_normalization_basic_frame(self):
        norm = TelemetryNormalizer()
        
        # Ingest sequence 1
        out1 = norm.ingest(self.create_packet(seq=1, pid="rpm", val=3000.0))
        out2 = norm.ingest(self.create_packet(seq=1, pid="map_bar", val=1.0))
        self.assertEqual(len(out1), 0)
        self.assertEqual(len(out2), 0)
        
        # Ingest sequence 2 -> flushes sequence 1
        out3 = norm.ingest(self.create_packet(seq=2, pid="rpm", val=3100.0))
        self.assertEqual(len(out3), 1)
        
        frame1 = out3[0]
        self.assertEqual(frame1.sequence_number, 1)
        self.assertEqual(frame1.engine_id, "engine_1")
        self.assertEqual(frame1.rpm, 3000.0)
        self.assertEqual(frame1.map_bar, 1.0)
        self.assertIsNone(frame1.oil_temp_c) # Missing

    def test_normalization_out_of_order_stale(self):
        norm = TelemetryNormalizer()
        norm.ingest(self.create_packet(seq=2, pid="rpm", val=3000.0))
        norm.ingest(self.create_packet(seq=3, pid="rpm", val=3100.0)) # flushes 2
        
        # Now late packet for sequence 2 arrives
        out = norm.ingest(self.create_packet(seq=2, pid="map_bar", val=1.0))
    
        # Should be flushed as partial frame to be rejected downstream
        self.assertEqual(len(out), 1)
        self.assertEqual(out[0].sequence_number, 2)
        self.assertEqual(out[0].map_bar, 1.0)

    def test_normalization_missing_channel_vs_value(self):
        norm = TelemetryNormalizer()
        
        # Valid partial telemetry: RPM present, MAP absent (Missing Channel)
        norm.ingest(self.create_packet(seq=1, pid="rpm", val=5200.0))
        out1 = norm.ingest(self.create_packet(seq=2, pid="rpm", val=5300.0)) # flushes 1
        
        frame = out1[0]
        self.assertEqual(frame.rpm, 5200.0)
        self.assertIsNone(frame.map_bar) # Missing channel is correctly None
        
        # Invalid missing value inside packet: (Missing Value)
        # Bypassing the dataclass to simulate bad JSON parse
        p = TelemetryPacket(
            simulation_timestamp=1.0, engine_index=1, parameter_id="rpm",
            value=None, unit="rpm", canonical_value=None, canonical_unit="rpm",
            physical_origin="SIMULATOR", state_category="SIMULATED",
            processing_context="SYNTHETIC", sequence_number=2
        )
        is_valid, _ = TelemetryValidator.is_valid(p)
        self.assertFalse(is_valid)
        
        out2 = norm.ingest(p)
        self.assertEqual(len(out2), 0) # Dropped, doesn't flush 2 yet
        
        # Zero is valid
        p_zero = self.create_packet(seq=2, pid="rpm", val=0.0)
        is_valid, _ = TelemetryValidator.is_valid(p_zero)
        self.assertTrue(is_valid)
        norm.ingest(p_zero)
        
        # NaN is invalid
        p_nan = self.create_packet(seq=2, pid="rpm", val=float('nan'))
        is_valid, _ = TelemetryValidator.is_valid(p_nan)
        self.assertFalse(is_valid)
        
        # Inf is invalid
        p_inf = self.create_packet(seq=2, pid="rpm", val=float('inf'))
        is_valid, _ = TelemetryValidator.is_valid(p_inf)
        self.assertFalse(is_valid)

    def test_normalization_sequence_gaps(self):
        norm = TelemetryNormalizer()
        norm.ingest(self.create_packet(seq=1, pid="rpm", val=3000.0))
        # Gap: seq 2 is missing entirely
        out = norm.ingest(self.create_packet(seq=3, pid="rpm", val=3100.0)) # Flushes 1
        
        self.assertEqual(len(out), 1)
        self.assertEqual(out[0].sequence_number, 1)
        
        frames = norm.flush_all()
        self.assertEqual(len(frames), 1)
        self.assertEqual(frames[0].sequence_number, 3)

    def test_normalization_buffer_limit_p1(self):
        norm = TelemetryNormalizer()
        # Flood the normalizer with 105 packets on the same sequence
        for i in range(105):
            norm.ingest(self.create_packet(seq=1, pid="rpm", val=3000.0 + i))
            
        # The buffer should cap at 100
        buffer_len = len(norm._buffers[(1, 1)])
        self.assertEqual(buffer_len, 100)
        
        # Flushed frame should survive
        frames = norm.flush_all()
        self.assertEqual(len(frames), 1)
        # The last value captured should be the 99th one (val 3099.0) because the last 5 were dropped
        self.assertEqual(frames[0].rpm, 3099.0)

    def test_normalization_sensor_count_p2(self):
        norm = TelemetryNormalizer()
        
        # Send RPM twice, MAP once
        norm.ingest(self.create_packet(seq=1, pid="rpm", val=3000.0))
        norm.ingest(self.create_packet(seq=1, pid="rpm", val=3100.0))
        norm.ingest(self.create_packet(seq=1, pid="map_bar", val=1.2))
        
        frames = norm.flush_all()
        self.assertEqual(len(frames), 1)
        frame = frames[0]
        
        # Unique valid sensors are 'rpm' and 'map_bar', total = 2.
        self.assertEqual(frame.valid_sensors_count, 2)
        # The RPM value should be the last one sent
        self.assertEqual(frame.rpm, 3100.0)

    def test_normalization_invalid_packet_dropped(self):
        norm = TelemetryNormalizer()
        norm.ingest(self.create_packet(seq=1, pid="rpm", val=3000.0))
        
        # Invalid packet
        bad = self.create_packet(seq=1, pid="map_bar", val=float('nan'))
        norm.ingest(bad)
        
        frames = norm.flush_all()
        frame = frames[0]
        self.assertEqual(frame.rpm, 3000.0)
        self.assertIsNone(frame.map_bar) # Dropped

    # --- TRANSPORT ---
    def test_transport_sha256_correctness(self):
        from src.digital_twin.telemetry.transport import compute_payload_sha256, DeepImmutableRawPacket
        import hashlib
        
        data = b"dummy_payload"
        expected = hashlib.sha256(data).hexdigest()
        self.assertEqual(compute_payload_sha256(data), expected)
        
    def test_transport_fifo_and_integrity(self):
        from src.digital_twin.telemetry.transport import InMemoryTransport
        
        transport = InMemoryTransport()
        
        # Should be empty initially
        self.assertIsNone(transport.receive())
        
        # Serialize packet to bytes
        p1 = self.create_packet(seq=1, pid="rpm", val=1000.0)
        p2 = self.create_packet(seq=2, pid="rpm", val=2000.0)
        
        b1 = p1.to_json().encode('utf-8')
        b2 = p2.to_json().encode('utf-8')
        
        # Send
        transport.send(b1)
        transport.send(b2)
        
        # Receive 1
        rx1 = transport.receive()
        self.assertIsNotNone(rx1)
        self.assertEqual(rx1.raw_bytes, b1)
        # Verify immutable
        with self.assertRaises(dataclasses.FrozenInstanceError):
            rx1.raw_bytes = b"hacked"
            
        # Receive 2
        rx2 = transport.receive()
        self.assertIsNotNone(rx2)
        self.assertEqual(rx2.raw_bytes, b2)
        
class TestReplay(unittest.TestCase):
    def test_replay_jsonl(self):
        from src.digital_twin.telemetry.replay import DatasetReplayer
        
        # Out of order records
        lines = [
            '{"timestamp": 10.0, "simulation_time": 10.0, "engine_id": "engine_1", "parameter_id": "rpm", "display_value": 3100.0, "canonical_value": 3100.0, "sequence_number": 2}',
            '{"timestamp": 9.0, "simulation_time": 9.0, "engine_id": "engine_1", "parameter_id": "map_bar", "display_value": 1.0, "canonical_value": 1.0, "sequence_number": 1}',
            '{"timestamp": 9.0, "simulation_time": 9.0, "engine_id": "engine_1", "parameter_id": "rpm", "display_value": 3000.0, "canonical_value": 3000.0, "sequence_number": 1}'
        ]
        
        replayer = DatasetReplayer()
        frames = list(replayer.replay_jsonl(lines))
        
        # Seq 2 arrives first, so seq 1 is flushed as a partial frame when it arrives.
        # Since there are two seq 1 packets, each gets flushed individually as it arrives stale.
        self.assertEqual(len(frames), 3)
        self.assertEqual(frames[0].sequence_number, 1)
        self.assertEqual(frames[0].map_bar, 1.0)
        self.assertEqual(frames[1].sequence_number, 1)
        self.assertEqual(frames[1].rpm, 3000.0)
        self.assertEqual(frames[2].sequence_number, 2)
        self.assertEqual(frames[2].rpm, 3100.0)
        
    def test_replay_csv_multi_engine_and_determinism(self):
        from src.digital_twin.telemetry.replay import DatasetReplayer
        
        csv_lines = [
            "timestamp,simulation_time,engine_id,parameter_id,display_value,canonical_value,sequence_number",
            "10.0,10.0,engine_1,rpm,3000.0,3000.0,1",
            "10.0,10.0,engine_2,rpm,4000.0,4000.0,1",
            "11.0,11.0,engine_1,rpm,3100.0,3100.0,2"
        ]
        
        replayer = DatasetReplayer()
        frames1 = list(replayer.replay_csv(csv_lines))
        frames2 = list(replayer.replay_csv(csv_lines))
        
        # Determinism check
        self.assertEqual(len(frames1), len(frames2))
        self.assertEqual(len(frames1), 3)
        
        f1_eng1_seq1 = next(f for f in frames1 if f.engine_id == "engine_1" and f.sequence_number == 1)
        f1_eng2_seq1 = next(f for f in frames1 if f.engine_id == "engine_2" and f.sequence_number == 1)
        f1_eng1_seq2 = next(f for f in frames1 if f.engine_id == "engine_1" and f.sequence_number == 2)
        
        self.assertEqual(f1_eng1_seq1.rpm, 3000.0)
        self.assertEqual(f1_eng2_seq1.rpm, 4000.0)
        self.assertEqual(f1_eng1_seq2.rpm, 3100.0)
        
    def test_replay_invalid_and_unknown_parameters(self):
        from src.digital_twin.telemetry.replay import DatasetReplayer
        
        lines = [
            # Valid
            '{"timestamp": 9.0, "simulation_time": 9.0, "engine_id": "engine_1", "parameter_id": "rpm", "display_value": 3000.0, "canonical_value": 3000.0, "sequence_number": 1}',
            # Unknown parameter
            '{"timestamp": 9.0, "simulation_time": 9.0, "engine_id": "engine_1", "parameter_id": "magic_dust", "display_value": 99.0, "canonical_value": 99.0, "sequence_number": 1}',
            # NaN value
            '{"timestamp": 9.0, "simulation_time": 9.0, "engine_id": "engine_1", "parameter_id": "map_bar", "display_value": "NaN", "canonical_value": "NaN", "sequence_number": 1}',
            # Missing required key
            '{"timestamp": 10.0, "engine_id": "engine_1", "parameter_id": "rpm", "sequence_number": 2}',
        ]
        
        replayer = DatasetReplayer()
        frames = list(replayer.replay_jsonl(lines))
        
        self.assertEqual(len(frames), 1)
        self.assertEqual(frames[0].rpm, 3000.0)
        # map_bar should be None due to NaN rejection
        self.assertIsNone(frames[0].map_bar)
        # Unknown dropped
        self.assertFalse(hasattr(frames[0], "magic_dust"))
        # Missing required key drops the whole record due to KeyError in parser
        self.assertTrue(all(f.sequence_number != 2 for f in frames))

    def test_replay_zero_and_empty_values(self):
        from src.digital_twin.telemetry.replay import DatasetReplayer
        
        lines = [
            # Zero value (should be preserved as 0.0)
            '{"timestamp": 9.0, "simulation_time": 9.0, "engine_id": "engine_1", "parameter_id": "rpm", "display_value": 0, "canonical_value": 0, "sequence_number": 1}',
            # Empty values (should be treated as None, thus invalid packet rejected/dropped)
            '{"timestamp": 11.0, "simulation_time": 11.0, "engine_id": "engine_1", "parameter_id": "map_bar", "display_value": "", "canonical_value": "", "sequence_number": 3}',
            # Missing values entirely
            '{"timestamp": 12.0, "simulation_time": 12.0, "engine_id": "engine_1", "parameter_id": "oil_temp_c", "sequence_number": 4}'
        ]
        
        replayer = DatasetReplayer()
        frames = list(replayer.replay_jsonl(lines))
        
        # Sequence 1 should be valid and flushed
        self.assertEqual(len(frames), 1)
        
        # Check Sequence 1
        self.assertEqual(frames[0].sequence_number, 1)
        self.assertEqual(frames[0].rpm, 0.0)


if __name__ == '__main__':
    unittest.main()
