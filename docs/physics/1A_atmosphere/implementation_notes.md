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

## 3. Frontend and Time Independence
The physics model operates strictly on continuous physical floats. 
There are no strings like `"hot_day"`, `"high_altitude"`, or UI booleans anywhere in this layer. 
A frontend UI, a mission-script replay, or a live telemetry feed would all map their data to the `EnvironmentInput` dataclass. The `AtmosphereModel` does not know or care where the input originated.

Furthermore, the model is strictly **stateless**. It evaluates the physical environment instantaneously. It does not implement transition dynamics or climb rates; representing a trajectory like $h(t)$ is the responsibility of an upstream mission or controller layer.

## 4. Internal Units
All internal math uses SI base units to prevent conversion errors:
- Temperature: Kelvin (K)
- Pressure: Pascals (Pa)
- Density: kg/m³
- Altitude: meters (m)

Where user-friendly units are common (e.g. Celsius for temperature), they are converted explicitly at the boundary.

## 5. Numerical Safeguards and Domain Bounds
- `altitude_m` is strictly validated. The model requires the altitude to be within the Troposphere (0 to 11,000 meters). If it is outside this domain, the model raises an explicit `ValueError` rather than silently clamping. This ensures out-of-bounds mission profiles fail loudly. (Note: 30,000 ft is ~9,144 m, well within this supported domain).
- Absolute temperature ($T$) is strictly validated. A nonphysical temperature ($T \le 0$ K) raises an explicit `ValueError`. Valid cold-weather scenarios (e.g. -40°C) are naturally > 0 K and supported.
- `relative_humidity_pct` is strictly validated. It must be between 0.0 and 100.0%. Values outside this range will raise an explicit `ValueError`.
- Vapor partial pressure is capped at total pressure to prevent physically impossible partial-pressure fractions if wild values are injected.

## 6. Precedence Rules and Weather Limitations
- **Temperature:** If `ambient_temp_c` is provided, it strictly overrides `temperature_offset_k`. The model supports standard day, actual specific ambient temperature, or ISA+delta.
- **Pressure:** The pressure calculation is strictly tied to the ISA baseline at the given altitude. True meteorological barometric weather variations (e.g., passing low-pressure fronts) are NOT currently modeled as independent offsets.

## 6. Validation
Validation tests are located in `scratch/test_atmosphere.py`.
They verify:
- Exact ISA sea level standards (15°C, 101325 Pa, 1.225 kg/m³)
- Pressure monotonicity across the 30,000 ft envelope.
- Thermodynamic relationships (increasing temperature or humidity appropriately decreases density).

## 7. Future Consumption by Layer 1B
Layer 1B (Turbocharger and Intake) will import `AtmosphericState`. It will use `pressure_pa` and `temperature_k` to determine the inlet conditions for the compressor, and `density_kg_m3` will heavily influence the air mass flow rate downstream. The atmosphere model does *not* know anything about engines or turbochargers.
