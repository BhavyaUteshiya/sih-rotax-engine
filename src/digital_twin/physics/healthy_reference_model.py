"""
Healthy Reference Model Interface.
SIH26054 — Phase 2 Digital Twin Digital Twin Core.
"""

from typing import Any, Optional

from src.digital_twin.models.operating_context import OperatingContext
from src.digital_twin.models.healthy_expected_state import HealthyExpectedState
from src.digital_twin.simulation.simulator import DigitalTwinSimulator
from src.digital_twin.simulation.state import SimulationInput
from src.digital_twin.physics.expected_behavior import ExpectedBehaviorModel

class HealthyReferenceModel:
    """
    Authoritative, deterministic interface for generating the HEALTHY EXPECTED STATE
    of the Rotax 914 from the Phase 1 physics model and operating context.
    
    Encapsulates the Phase 1 DigitalTwinSimulator to maintain time-domain
    state without leaking simulation internals to the Twin Engine.
    """

    def __init__(self, engine_index: int = 1, initial_altitude_m: float = 0.0):
        self.engine_index = engine_index
        # Internal Phase 1 simulator representing the healthy physical baseline
        self.simulator = DigitalTwinSimulator(initial_altitude_m=initial_altitude_m)
        self.sequence_number = 0

    def step(self, context: OperatingContext, dt: float) -> HealthyExpectedState:
        """
        Advances the healthy reference model by dt based on the OperatingContext
        and returns the resulting HealthyExpectedState.
        """
        if dt <= 0.0:
            raise ValueError("Timestep dt must be strictly positive.")

        # 1. Map OperatingContext (Phase 2) to SimulationInput (Phase 1)
        sim_input = SimulationInput(
            timestep_s=dt,
            altitude_m=context.altitude_m,
            ambient_temp_c=context.ambient_temp_c,
            temperature_offset_k=0.0,
            relative_humidity_pct=context.relative_humidity_pct,
            throttle_position=context.throttle_position,
            airspeed_m_s=context.airspeed_m_s,
            fuel_pressure_pa=context.fuel_pressure_pa,
            
            # NOTE: 25000.0 Pa is a nominal engineering/calibration assumption for the 
            # fuel pressure delta. It is NOT presented as an official Rotax specification.
            # This is a nominal calibration/demo input and future calibration/configuration 
            # may replace it with an authoritative source.
            fuel_pressure_delta_pa=25000.0, 
            
            starter_engaged=context.starter_engaged
        )

        # 2. Step the Phase 1 simulator
        sim_state = self.simulator.step(sim_input)
        self.sequence_number += 1

        # 3. Adapt SimulationState to HealthyExpectedState
        expected_state = ExpectedBehaviorModel.from_simulation_state(
            sim_state=sim_state,
            engine_index=self.engine_index,
            timestamp=self.simulator.time_s,
            sequence_number=self.sequence_number,
            propeller_state=sim_state.propeller
        )

        return expected_state
