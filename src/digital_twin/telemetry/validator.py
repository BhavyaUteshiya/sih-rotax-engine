import math
from typing import Tuple

from src.digital_twin.telemetry.packet import TelemetryPacket

class TelemetryValidator:
    """
    Validates physical parameters of TelemetryPackets.
    Strictly forbids NaN, Inf, and invalid timestamps.
    """
    
    @staticmethod
    def is_valid(packet: TelemetryPacket) -> Tuple[bool, str]:
        # Check timestamp
        if packet.simulation_timestamp is None:
            return False, "Missing simulation_timestamp"
        if not isinstance(packet.simulation_timestamp, (int, float)):
            return False, "Malformed simulation_timestamp type"
        if not math.isfinite(packet.simulation_timestamp):
            return False, "Non-finite simulation_timestamp"
            
        # Check sequence number
        if packet.sequence_number is None or not isinstance(packet.sequence_number, int):
            return False, "Malformed sequence_number"

        # Check values
        if packet.value is None or packet.canonical_value is None:
            return False, "Missing value"
            
        if not isinstance(packet.value, (int, float)) or not isinstance(packet.canonical_value, (int, float)):
            return False, "Malformed value type"

        if not math.isfinite(packet.value) or not math.isfinite(packet.canonical_value):
            return False, "Non-finite value"
            
        return True, "VALID"
