import hashlib
import queue
from dataclasses import dataclass
from typing import Optional

def compute_payload_sha256(raw_bytes: bytes) -> str:
    """Calculates SHA-256 digest over the exact transmitted raw bytes."""
    return hashlib.sha256(raw_bytes).hexdigest()

@dataclass(frozen=True)
class DeepImmutableRawPacket:
    """
    Immutable envelope required by docs/integration/03_can_transport.md.
    Prevents accidental mutation of the received raw payload and its integrity metadata.
    """
    raw_bytes: bytes
    sha256_digest: str

class InMemoryTransport:
    """
    Thread-safe in-memory queue operating natively without requiring physical CAN sockets.
    Provides deterministic FIFO queue semantics.
    """
    def __init__(self):
        self._queue: queue.Queue = queue.Queue()

    def send(self, raw_bytes: bytes) -> None:
        """
        Calculates SHA-256 and enqueues the immutable packet.
        """
        digest = compute_payload_sha256(raw_bytes)
        packet = DeepImmutableRawPacket(
            raw_bytes=raw_bytes,
            sha256_digest=digest
        )
        self._queue.put(packet)

    def receive(self) -> Optional[DeepImmutableRawPacket]:
        """
        Receives the next packet in FIFO order. 
        Returns None if the queue is empty.
        """
        try:
            return self._queue.get_nowait()
        except queue.Empty:
            return None
