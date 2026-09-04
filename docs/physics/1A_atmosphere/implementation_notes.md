# Phase 1A: Atmosphere Implementation Notes

## 1. Implementation Module
- **File:** `src/digital_twin/physics/atmosphere.py`
- **Class:** `AtmosphereModel`
- **Method:** `calculate(env: EnvironmentInput) -> AtmosphericState`

## 2. Public Interface
The design exposes a clean, stateless function. 
It receives an `EnvironmentInput` dataclass:
- `altitude_m`
- `ambient_temp_c` (optional override)
- `temperature_offset_k` (optional delta from ISA)
- `relative_humidity_pct`

It returns an `AtmosphericState` dataclass:
- `altitude_m`
- `temperature_c`, `temperature_k`
- `pressure_pa`
- `density_kg_m3`
- `vapor_pressure_pa`
- `speed_of_sound_m_s`

## 3. Frontend Independence
The physics model operates strictly on continuous physical floats. 
There are no strings like `"hot_day"`, `"high_altitude"`, or UI booleans anywhere in this layer. 
A frontend UI, a mission-script replay, or a live telemetry feed would all map their data to the `EnvironmentInput` dataclass. The `AtmosphereModel` does not know or care where the input originated.

## 4. Internal Units
All internal math uses SI base units to prevent conversion errors:
- Temperature: Kelvin (K)
- Pressure: Pascals (Pa)
- Density: kg/m³
- Altitude: meters (m)

Where user-friendly units are common (e.g. Celsius for temperature), they are converted explicitly at the boundary.

## 5. Numerical Safeguards
Several `max()` and `min()` clamps are used to prevent impossible thermodynamics from crashing the simulation:
- `altitude_m` is clamped between 0 and 11,000 m before calculating ISA pressure/temp. This prevents the standard lapse rate from erroneously predicting temperatures below absolute zero if a caller passes an altitude of 100,000 m.
- Absolute temperature is clamped to a minimum of 1.0 K to prevent `ZeroDivisionError` in the ideal gas law equations.
- `relative_humidity_pct` is clamped strictly between 0.0 and 100.0%.
- Vapor partial pressure is capped at total pressure to prevent physically impossible partial-pressure fractions if wild values are injected.

## 6. Validation
Validation tests are located in `scratch/test_atmosphere.py`.
They verify:
- Exact ISA sea level standards (15°C, 101325 Pa, 1.225 kg/m³)
- Pressure monotonicity across the 30,000 ft envelope.
- Thermodynamic relationships (increasing temperature or humidity appropriately decreases density).

## 7. Future Consumption by Layer 1B
Layer 1B (Turbocharger and Intake) will import `AtmosphericState`. It will use `pressure_pa` and `temperature_k` to determine the inlet conditions for the compressor, and `density_kg_m3` will heavily influence the air mass flow rate downstream. The atmosphere model does *not* know anything about engines or turbochargers.
