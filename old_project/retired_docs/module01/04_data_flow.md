# Module 01 — Data Flow & Stage Processing

## Unidirectional 4-Stage Processing Pipeline

1. **Stage 1: Raw Input & Forensic Immutability**
   - Receives byte stream from `CanInterface`, `EcuInterface`, or `FileSourceInterface`.
   - Constructs `DeepImmutableRawPacket`.
   - Computes `payload_sha256` content hash and `packet_id` identity hash.
   - Classifies transmission integrity: `ORIGINAL`, `EXACT_DUPLICATE`, `RETRANSMISSION`, `CONFLICTING_PAYLOAD`.
   - Appends packet to `RawStore` log in strict `ARRIVAL_ORDER`.

2. **Stage 2: Decoding & SI Unit Normalization**
   - `CanDecoder`, `JsonDecoder`, or `CsvDecoder` decodes payload into `DecodedSignal`.
   - Raw numeric values (e.g. unscaled integer from CAN bytes) and unit scale/offset metadata are extracted.
   - `UnitNormalizer` converts raw values into canonical SI values ($\text{RPM} \rightarrow \text{rad/s}$, $^\circ\text{C} \rightarrow \text{K}$, $\text{bar} \rightarrow \text{Pa}$, $\text{kg/h} \rightarrow \text{kg/s}$).

3. **Stage 3: Validation & Quality/Usability Flagging**
   - `ValidityValidator` evaluates Tier 2 physical plausibility min/max limits and Tier 6 rate-of-change delta limits.
   - Decouples physical validity (`is_physically_valid`) from temporal validity (`is_temporally_valid`).
   - Marks `is_sync_eligible = (is_physically_valid and is_temporally_valid and normalized_source_utc is not None)`.

4. **Stage 4: Multi-Rate Buffering & Storage**
   - Pushes measurement into channel-specific bounded `RingBuffer`.
   - Appends measurement to `NormalizedStore` log in `SOURCE_EVENT_ORDER`.

5. **On-Demand Temporal Synchronization**
   - `TimestampSynchronizer` generates `TelemetryFrame v1.0.0` at target grid timestamp $T_{\text{grid}}$.
   - In `REALTIME_CAUSAL_MODE`, consumes ONLY `is_sync_eligible == True` samples with $t \le T_{\text{grid}}$ (`HOLD_LAST`). Linear interpolation is strictly forbidden.
   - In `OFFLINE_REPLAY_MODE`, permits retrospective `LINEAR_INTERPOLATE` between enclosing samples.
