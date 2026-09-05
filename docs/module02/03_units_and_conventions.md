# Module 02 — 03. Units & Canonical SI Conventions

## 1. Canonical SI Unit Mandate
All internal physics differential equations, thermodynamic calculations, dynamic balances, and state models MUST use canonical SI units. Display unit conversions are handled explicitly at the outer interface boundary via `UnitConverter`.

| Physical Quantity | Display Unit | Canonical SI Unit | Conversion Factor / Formula |
| :--- | :--- | :--- | :--- |
| Rotational Speed | RPM | `RAD_PER_SEC` | $\text{rad/s} = \text{RPM} \times \frac{\pi}{30}$ |
| Temperature | °C | `KELVIN` | $T \, (\text{K}) = T \, (^\circ\text{C}) + 273.15$ |
| Pressure | bar | `PASCAL` | $P \, (\text{Pa}) = P \, (\text{bar}) \times 100,000$ |
| Fuel / Air Flow | kg/h | `KG_PER_SEC` | $\dot{m} \, (\text{kg/s}) = \frac{\dot{m} \, (\text{kg/h})}{3600}$ |
| Power | HP | `WATT` | $P \, (\text{W}) = P \, (\text{HP}) \times 745.7$ |

## 2. Unit Converter Module
The utility module `src/module02/utils/unit_converter.py` provides exact, bidirectional conversion functions tested to within $<10^{-6}$ precision.
