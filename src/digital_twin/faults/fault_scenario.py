from dataclasses import dataclass

@dataclass
class FaultScenario:
    """
    Configuration for a deterministic fault scenario.
    
    Attributes:
        fault_type: E.g., 'COOLING_DEGRADATION', 'LUBRICATION_DEGRADATION', 'AIRFLOW_RESTRICTION', 'TORQUE_DEGRADATION'
        enabled: Whether this scenario is active.
        severity: Target severity level from 0.0 (no effect) to 1.0 (max configured effect).
        start_time: Simulation time when this fault begins.
        ramp_duration: Duration (seconds) for the fault severity to linearly increase from 0.0 to `severity`. If 0.0, the fault is instantaneous.
    """
    fault_type: str
    enabled: bool = True
    severity: float = 0.0
    start_time: float = 0.0
    ramp_duration: float = 0.0
