# Module 01 — Protocol Decoding & SI Unit Normalization

## Protocol Decoding Architecture
`CanDecoder`, `JsonDecoder`, and `CsvDecoder` convert raw immutable wire byte payloads into Layer 2 `DecodedSignal` objects.

- `CanDecoder`: Extracts unscaled raw integer bits (`raw_numeric_value = raw_int`) from standard byte offsets and attaches `scale` & `offset` in `decoding_metadata`.
- Limitation Note: The demonstration CAN decoder supports standard 8/16/32-bit unsigned little/big endian signals. Complex arbitrary bit-masking or CAN-FD multiplexing beyond standard byte boundaries are not required by the demonstration spec.

## Canonical SI Unit Conversions
`UnitNormalizer` converts raw engineering display units to SI standards:

| Parameter Type | Raw / Display Unit | Canonical SI Unit | Conversion Formula |
| :--- | :--- | :--- | :--- |
| Rotational Speed | RPM | `RAD_PER_SEC` ($\text{rad/s}$) | $\omega = \text{RPM} \cdot \frac{\pi}{30}$ |
| Temperature | $^\circ\text{C}$ (`DEGC`) | `KELVIN` ($\text{K}$) | $T_{\text{SI}} = T_{^\circ\text{C}} + 273.15$ |
| Pressure | bar (`BAR`) | `PASCAL` ($\text{Pa}$) | $P_{\text{SI}} = P_{\text{bar}} \cdot 100,000$ |
| Fuel Flow | kg/h (`KG_PER_HOUR`) | `KG_PER_SEC` ($\text{kg/s}$) | $\dot{m}_{\text{SI}} = \frac{\dot{m}_{\text{kg/h}}}{3600}$ |
