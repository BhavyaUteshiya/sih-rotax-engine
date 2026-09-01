# Module 01 — Timestamp Architecture & Clock Mapping

## Multi-Domain Timestamp Containers
Module 01 supports 7 clock domains: `UTC`, `MONOTONIC`, `ECU_BOOT`, `MISSION_TIME`, `DEVICE_TICKS`, `UNKNOWN`.

## Mathematical Clock Mapping Formula
When a valid `ClockMapping` calibration is provided, source domain timestamps $t_{\text{source}}$ are mapped to normalized UTC epoch seconds using:

$$t_{\text{UTC}} = \text{reference\_utc} + (t_{\text{source}} - \text{reference\_source\_timestamp}) \cdot \left(1 + \frac{\text{drift\_rate\_ppm}}{1,000,000}\right) + \text{offset\_seconds}$$

### Expiration & Confidence Rules
- If `now_utc > valid_until_utc`: mapping is EXPIRED.
- If `confidence < 0.5`: mapping is LOW_CONFIDENCE.
- In either case, `normalized_source_utc = None`, `is_temporally_valid = False`, `is_sync_eligible = False`, and `temporal_quality = UNRESOLVED_CLOCK`.

### Independence of Physical Validity
If UTC mapping is unresolvable, physical measurement validity (`is_physically_valid = True`) is preserved intact so downstream modules can consume physically sound data in its native clock domain.
