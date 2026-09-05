# CAN Transport Layer Specification

The transport layer abstracts CAN communication across development and execution environments:

1. **InMemoryTransport**: Thread-safe in-memory queue operating natively on macOS and Linux without requiring physical CAN sockets.
2. **SocketCANTransport**: Binds to Linux SocketCAN sockets (`vcan0`/`can0`), falling back to `InMemoryTransport` if native CAN sockets are unsupported on host OS.

## Wire Payload Integrity
Raw CAN payloads undergo SHA-256 calculation (`compute_payload_sha256(raw_bytes)`), creating immutable `DeepImmutableRawPacket` instances for downstream Digital Twin ingestion.
