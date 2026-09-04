"""
Twin Internal State.
Represents the persistent, time-integrated physical state variables of the Digital Twin.
SIH26054 — Module 03 Digital Twin Core.
"""

from dataclasses import dataclass

@dataclass
class TwinInternalState:
    """
    Independent internal memory of the Digital Twin engine state.
    These variables are subject to physical inertia (rotational/thermal/fluid) 
    and evolve over time based on ExpectedBehaviorModel physics and Estimator corrections.
    """
    timestamp: float = 0.0
    
    # Air path and mechanical states
    map_bar: float = 0.35      # Starts at idle typical value
    rpm: float = 0.0           # Engine off
    
    # Thermal states (lagged variables)
    egt_c: float = 15.0        # Assumed ambient start
    cht_c: float = 15.0
    oil_temp_c: float = 15.0

    def to_dict(self) -> dict:
        return {
            "timestamp": self.timestamp,
            "map_bar": round(self.map_bar, 4),
            "rpm": round(self.rpm, 1),
            "egt_c": round(self.egt_c, 2),
            "cht_c": round(self.cht_c, 2),
            "oil_temp_c": round(self.oil_temp_c, 2),
        }
