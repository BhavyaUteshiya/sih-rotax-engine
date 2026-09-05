"""
CAN & SocketCAN Transport Abstraction Hierarchy.
SIH26054 — Module 02 Engine Simulator.
"""

import queue
import socket
import struct
import threading
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Tuple

from src.module02.integration.telemetry_encoder import EncodedCanFrame


class TransportError(Exception):
    """Raised when CAN transport failure occurs."""
    pass


class TelemetryTransport(ABC):
    """
    Abstract CAN Transport Interface supporting both deterministic In-Memory queue
    and Linux SocketCAN (vcan0/can0) raw socket communication.
    """

    @abstractmethod
    def send_frame(self, frame: EncodedCanFrame) -> bool:
        """Transmits an EncodedCanFrame payload across the transport layer."""
        pass

    @abstractmethod
    def receive_frames(self, max_frames: int = 100) -> List[EncodedCanFrame]:
        """Receives available EncodedCanFrame list from transport layer."""
        pass

    @abstractmethod
    def close(self) -> None:
        """Closes transport connection and releases underlying resources."""
        pass


class InMemoryTransport(TelemetryTransport):
    """
    Deterministic Thread-Safe In-Memory Queue CAN Transport.
    Operates natively across macOS and Linux development environments without physical CAN hardware.
    """

    def __init__(self, buffer_capacity: int = 10000, backpressure_policy: str = "BUFFERING") -> None:
        self.buffer_capacity = max(100, buffer_capacity)
        self.backpressure_policy = backpressure_policy.upper()
        self._queue: queue.Queue[EncodedCanFrame] = queue.Queue(maxsize=self.buffer_capacity)
        self._lock = threading.Lock()
        self.records_published = 0
        self.records_received = 0
        self.records_dropped = 0
        self.transport_errors = 0

    def send_frame(self, frame: EncodedCanFrame) -> bool:
        try:
            self._queue.put_nowait(frame)
            with self._lock:
                self.records_published += 1
            return True
        except queue.Full:
            with self._lock:
                self.records_dropped += 1
                if self.backpressure_policy == "DROPPING":
                    try:
                        self._queue.get_nowait()
                        self._queue.put_nowait(frame)
                        return True
                    except Exception:
                        self.transport_errors += 1
                        return False
                else:
                    self.transport_errors += 1
                    return False

    def receive_frames(self, max_frames: int = 100) -> List[EncodedCanFrame]:
        frames: List[EncodedCanFrame] = []
        for _ in range(max_frames):
            try:
                frame = self._queue.get_nowait()
                frames.append(frame)
                with self._lock:
                    self.records_received += 1
            except queue.Empty:
                break
        return frames

    def get_metrics(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "records_published": self.records_published,
                "records_received": self.records_received,
                "records_dropped": self.records_dropped,
                "transport_errors": self.transport_errors,
                "queue_size": self._queue.qsize(),
                "buffer_capacity": self.buffer_capacity,
                "buffer_utilization": self._queue.qsize() / float(self.buffer_capacity)
            }

    def close(self) -> None:
        with self._lock:
            while not self._queue.empty():
                try:
                    self._queue.get_nowait()
                except queue.Empty:
                    break


class SocketCANTransport(TelemetryTransport):
    """
    Linux Native SocketCAN Transport (vcan0/can0 raw socket interface).
    Gracefully falls back to InMemoryTransport if AF_CAN is unsupported on the current OS.
    """

    def __init__(self, interface_name: str = "vcan0", buffer_capacity: int = 10000) -> None:
        self.interface_name = interface_name
        self.in_memory_fallback = InMemoryTransport(buffer_capacity=buffer_capacity)
        self._sock: Optional[socket.socket] = None
        self._has_native_socketcan = False

        if hasattr(socket, "AF_CAN") and hasattr(socket, "CAN_RAW"):
            try:
                self._sock = socket.socket(socket.AF_CAN, socket.SOCK_RAW, socket.CAN_RAW)
                self._sock.bind((interface_name,))
                self._sock.setblocking(False)
                self._has_native_socketcan = True
            except Exception:
                self._has_native_socketcan = False
                self._sock = None

    def send_frame(self, frame: EncodedCanFrame) -> bool:
        if self._has_native_socketcan and self._sock is not None:
            try:
                # CAN raw frame format: struct can_frame { can_id_t can_id; __u8 can_dlc; __u8 __pad; __u8 __res0; __u8 __res1; __u8 data[8]; };
                can_id_flags = frame.can_id
                dlc = len(frame.payload)
                padded_payload = frame.payload.ljust(8, b'\x00')[:8]
                can_pkt = struct.pack("=IBBB5x", can_id_flags, dlc, 0, 0) + padded_payload
                self._sock.send(can_pkt)
                self.in_memory_fallback.send_frame(frame)
                return True
            except Exception:
                return self.in_memory_fallback.send_frame(frame)
        else:
            return self.in_memory_fallback.send_frame(frame)

    def receive_frames(self, max_frames: int = 100) -> List[EncodedCanFrame]:
        return self.in_memory_fallback.receive_frames(max_frames=max_frames)

    def close(self) -> None:
        if self._sock is not None:
            try:
                self._sock.close()
            except Exception:
                pass
            self._sock = None
        self.in_memory_fallback.close()
