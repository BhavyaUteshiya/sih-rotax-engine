"""
Telemetry Scheduler: Manages 100 Hz Physics vs 50 Hz Telemetry Publication Rate & Sequence Numbers.
SIH26054 — Module 02 Engine Simulator.
"""

from typing import Dict, List, Optional

from src.module02.integration.can_transport import EncodedCanFrame, TelemetryTransport
from src.module02.integration.telemetry_encoder import TelemetryEncoder
from src.module02.models.states import SimulationState


class TelemetryScheduler:
    """
    Manages deterministic dual-rate timing:
    - 100 Hz Physics Integration (dt = 0.01 s)
    - 50 Hz Telemetry Sampling & Publication (dt_telemetry = 0.02 s)
    Ensures monotonically increasing sequence numbers per CAN stream with zero duplicate numbers.
    """

    def __init__(
        self,
        transport: TelemetryTransport,
        physics_rate_hz: float = 100.0,
        telemetry_rate_hz: float = 50.0
    ) -> None:
        self.transport = transport
        self.physics_rate_hz = physics_rate_hz
        self.telemetry_rate_hz = telemetry_rate_hz
        self.sample_divider = int(round(physics_rate_hz / telemetry_rate_hz))

        self._step_counter = 0
        self.sequence_numbers: Dict[str, int] = {
            "can0_eng1": 0,
            "can0_eng2": 0,
            "can0_aircraft": 0,
        }

        self.records_generated = 0
        self.records_published = 0
        self.records_dropped = 0

    def step_physics_and_publish_telemetry(
        self,
        state: SimulationState,
        simulation_time_sec: float
    ) -> List[EncodedCanFrame]:
        """
        Invoked on every 100 Hz physics tick.
        Publishes telemetry frames on 50 Hz sampling intervals (every 2nd physics tick).
        """
        self._step_counter += 1
        published_frames: List[EncodedCanFrame] = []

        if self._step_counter % self.sample_divider == 0:
            encoded_frames = TelemetryEncoder.encode_simulation_state(
                state=state,
                sequence_numbers=self.sequence_numbers,
                source_timestamp=simulation_time_sec
            )

            self.records_generated += len(encoded_frames)

            for frame in encoded_frames:
                success = self.transport.send_frame(frame)
                if success:
                    self.records_published += 1
                    published_frames.append(frame)
                    # Advance sequence number monotonically for stream
                    self.sequence_numbers[frame.stream_id] = self.sequence_numbers.get(frame.stream_id, 0) + 1
                else:
                    self.records_dropped += 1

        return published_frames

    def reset() -> None:
        """Resets step counter and sequence numbers."""
        self._step_counter = 0
        for stream in self.sequence_numbers:
            self.sequence_numbers[stream] = 0
        self.records_generated = 0
        self.records_published = 0
        self.records_dropped = 0
