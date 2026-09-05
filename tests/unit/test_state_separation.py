"""
Minimal Integration Check: Verify separation of Healthy Expected State and Estimated Actual State.
"""
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.digital_twin.services.twin_engine import DigitalTwinEngine
from src.digital_twin.models.observed_state import ObservedState

class MockPipeline:
    def __init__(self):
        self.map_bar = 0.35
        self.rpm = 1400.0

class MockObservedState(ObservedState):
    @classmethod
    def from_pipeline(cls, pipeline, engine_index, target_timestamp, target_sequence):
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
    
    # Override for mock telemetry
    engine._derive_observed_state = lambda *args, **kwargs: MockObservedState.from_pipeline(kwargs.get('pipeline') or args[0], kwargs.get('engine_index', 1), kwargs.get('timestamp', 0.0), kwargs.get('sequence_number', 0))

    print("--- Testing Healthy vs Estimated Separation ---")
    ctx = {"throttle_1": 100.0}
    
    # 1. Spool up cleanly for 2 seconds (telemetry matches expected)
    print("\n[Phase 1: Normal Spool Up]")
    for i in range(5):
        t = i * 0.5
        pipeline.map_bar = 1.15
        state = engine.process_step(None, pipeline, engine_index=1, timestamp=t, sequence_number=i, operating_context=ctx)
        
    print(f"t={t:.1f}s | Healthy MAP: {state.healthy_internal_state.map_bar:.3f} | Estimated Actual MAP: {state.estimated_actual_state.map_bar:.3f}")

    # 2. Inject a massive telemetry fault.
    # The healthy state should remain at ~1.15. The estimated state should get pulled down.
    print("\n[Phase 2: Telemetry Fault Injected (MAP drops to 0.5)]")
    pipeline.map_bar = 0.50
    for i in range(5, 10):
        t = i * 0.5
        state = engine.process_step(None, pipeline, engine_index=1, timestamp=t, sequence_number=i, operating_context=ctx)
        print(f"t={t:.1f}s | Healthy MAP: {state.healthy_internal_state.map_bar:.3f} | Observed MAP: {pipeline.map_bar:.3f} | Estimated Actual MAP: {state.estimated_actual_state.map_bar:.3f} | Status: {state.status.name}")

    if state.healthy_internal_state.map_bar > 1.10 and state.estimated_actual_state.map_bar < 1.05:
        print("\nSUCCESS: Healthy Internal State remained independent of the physical telemetry fault!")
    else:
        print("\nFAILURE: Separation failed.")

if __name__ == "__main__":
    main()
