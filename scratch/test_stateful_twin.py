"""
Test Script: Verify Stateful Digital Twin and Estimator logic.
"""
import sys
import os

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.digital_twin.services.twin_engine import DigitalTwinEngine
from src.digital_twin.models.observed_state import ObservedState


class MockPipeline:
    def __init__(self):
        self.map_bar = 0.35
        self.rpm = 1400.0
        
    def get_latest(self):
        pass


class MockObservedState(ObservedState):
    @classmethod
    def from_module02_pipeline(cls, pipeline, engine_index, target_timestamp, target_sequence):
        # We inject mock telemetry directly
        return cls(
            timestamp=target_timestamp,
            sequence_number=target_sequence,
            map_bar=pipeline.map_bar,
            rpm=pipeline.rpm,
            data_quality="GOOD"
        )


def main():
    engine = DigitalTwinEngine()
    pipeline = MockPipeline()
    
    # Override the _derive_observed_state temporarily to inject our mock telemetry
    original_derive = engine._derive_observed_state
    
    def mock_derive(pipeline, telemetry_frame, normalized_records, engine_index, timestamp, sequence_number, propeller_state):
        return MockObservedState.from_module02_pipeline(pipeline, engine_index, timestamp, sequence_number)
        
    engine._derive_observed_state = mock_derive

    print("--- Test 1: Stateful Spool-Up (0% -> 100% Throttle) ---")
    ctx = {"throttle_1": 100.0} # Step input
    
    for i in range(5):
        t = i * 0.5  # 0.5s steps
        
        # Telemetry reacts instantly for this test
        pipeline.map_bar = 1.15
        pipeline.rpm = 5800.0
        
        state = engine.process_step(
            sim_state=None, 
            pipeline=pipeline, 
            engine_index=1, 
            timestamp=t,
            sequence_number=i,
            operating_context=ctx
        )
        
        print(f"t={t:.1f}s | Twin Expected MAP: {state.expected_state.map_bar:.3f} (Internal MAP: {state.internal_state.map_bar:.3f}) | RPM: {state.expected_state.rpm:.1f}")

    print("\n--- Test 2: Telemetry Synchronization (Faulted Telemetry) ---")
    # Hold throttle at 100% (predicts ~1.15 map)
    # Fault the telemetry to 0.5 map
    for i in range(5, 10):
        t = i * 0.5
        pipeline.map_bar = 0.50 # Fault!
        
        state = engine.process_step(
            sim_state=None, 
            pipeline=pipeline, 
            engine_index=1, 
            timestamp=t,
            sequence_number=i,
            operating_context=ctx
        )
        
        print(f"t={t:.1f}s | Expected MAP: {state.expected_state.map_bar:.3f} | Observed: 0.500 | Internal corrected: {state.internal_state.map_bar:.3f} | Status: {state.status.name}")

if __name__ == "__main__":
    main()
