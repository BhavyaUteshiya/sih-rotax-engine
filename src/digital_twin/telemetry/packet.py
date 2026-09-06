import json
from dataclasses import dataclass, asdict

@dataclass(frozen=True)
class TelemetryPacket:
    """
    Matches the schema defined in docs/integration/02_telemetry_contract.md
    """
    simulation_timestamp: float
    engine_index: int
    parameter_id: str
    value: float | None
    unit: str
    canonical_value: float | None
    canonical_unit: str
    physical_origin: str
    state_category: str
    processing_context: str
    sequence_number: int

    def to_json(self) -> str:
        """Serialize to JSON string."""
        return json.dumps(asdict(self))

    @classmethod
    def from_json(cls, data: str) -> "TelemetryPacket":
        """Deserialize from JSON string."""
        return cls(**json.loads(data))
