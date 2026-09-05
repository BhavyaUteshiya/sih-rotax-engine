# Module 02 — 02. Complete Telemetry Parameter Catalog

## Parameter Catalog Summary
Module 02 maintains a central registry (`ParameterRegistry`) containing 45 parameters across 12 categories.

| Parameter ID | Display Name | Display Unit | Canonical SI Unit | Category | Description | Upstream Causes | Downstream Effects |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `altitude` | Altitude | m | METER | ENVIRONMENT | UAV flight altitude | vertical_speed | ambient_pressure, ambient_temperature, air_density |
| `ambient_temperature` | Ambient Temp | °C | KELVIN | ENVIRONMENT | Ambient temperature | altitude | air_density, cht_cyl1..4, oil_temperature |
| `ambient_pressure` | Ambient Press | bar | PASCAL | ENVIRONMENT | Atmospheric pressure | altitude | air_density, manifold_pressure |
| `air_density` | Moist Air Density | kg/m³ | KG_PER_M3 | ENVIRONMENT | Moist air density | ambient_pressure, ambient_temp, humidity | air_mass_flow, drag, propeller_thrust |
| `relative_humidity` | Relative Humidity | % | PERCENT | ENVIRONMENT | Moisture percentage | None | air_density, air_fuel_ratio |
| `wind_speed` | Wind Speed | m/s | M_PER_SEC | ENVIRONMENT | Wind vector magnitude | None | airspeed |
| `airspeed` | Airspeed | m/s | M_PER_SEC | FLIGHT | Forward airspeed V_inf | propeller_thrust, drag, wind_speed | vertical_speed, cooling_airflow |
| `vertical_speed` | Vertical Speed | m/s | M_PER_SEC | FLIGHT | Rate of climb V_z | airspeed | altitude |
| `aircraft_mass` | Aircraft Mass | kg | KILOGRAM | FLIGHT | Total mass m_ac | fuel_flow | airspeed, vertical_speed |
| `throttle` | Throttle Demand | % | PERCENT | ENGINE_CONTROL | Throttle command theta | None | manifold_pressure |
| `manifold_pressure` | Manifold Pressure | bar | PASCAL | ENGINE_DYNAMICS | Manifold pressure p_m | throttle, ambient_pressure | air_mass_flow, ring_wear |
| `engine_rpm` | Engine Speed | RPM | RAD_PER_SEC | ENGINE_DYNAMICS | Shaft speed omega | indicated_torque, propeller_load, friction | air_mass_flow, propeller_thrust, alternator_current |
| `injection_timing` | Injection Timing | °BTDC | DEGREE | ENGINE_CONTROL | Injection advance | engine_rpm, manifold_pressure | combustion_efficiency, egt_cyl1..4 |
| `air_mass_flow` | Air Mass Flow | kg/h | KG_PER_SEC | ENGINE_DYNAMICS | Air intake rate m_air | manifold_pressure, air_density, engine_rpm | fuel_flow, air_fuel_ratio |
| `fuel_flow` | Fuel Mass Flow | kg/h | KG_PER_SEC | ENGINE_DYNAMICS | Fuel delivery rate m_fuel | air_mass_flow, injector_wear | indicated_torque, aircraft_mass, AFR |
| `air_fuel_ratio` | Air-Fuel Ratio | Ratio | RATIO | COMBUSTION | AFR ratio | air_mass_flow, fuel_flow | combustion_efficiency, egt_cyl1..4 |
| `indicated_torque` | Indicated Torque | N·m | NEWTON_METER | ENGINE_DYNAMICS | Total torque T_ind,total | fuel_flow, combustion_efficiency | engine_rpm, brake_thermal_efficiency |
| `cht_cyl1..4` | CHT Cylinder 1-4 | °C | KELVIN | THERMAL | Head Temperature 1-4 | fuel_flow, combustion_efficiency, cooling | oil_temperature, vibration_rms |
| `egt_cyl1..4` | EGT Cylinder 1-4 | °C | KELVIN | THERMAL | Exhaust Temp 1-4 | fuel_flow, air_fuel_ratio, injection_timing | None |
| `oil_temperature` | Oil Temperature | °C | KELVIN | LUBRICATION | Sump temperature T_oil | friction_torque, cht_cyl1, ambient_temp | oil_viscosity, oil_pressure |
| `oil_pressure` | Oil Pressure | bar | PASCAL | LUBRICATION | Oil pressure P_oil | engine_rpm, oil_viscosity | bearing_wear |
| `vibration_rms` | Vibration RMS | m/s² | M_PER_SEC2 | MECHANICAL | Vibration acceleration RMS | engine_rpm, cht_cyl1, bearing_wear | None |
| `alternator_current` | Alternator Current | A | AMPERE | ELECTRICAL | Output current I_alt | engine_rpm | battery_soc, alternator_load_torque |
| `battery_voltage` | Battery Voltage | V | VOLT | ELECTRICAL | Bus voltage V_bat | battery_soc, alternator_current | alternator_load_torque |
| `bearing_wear` | Bearing Wear | State | RATIO | DEGRADATION | Wear state D_bearing | engine_rpm, oil_temperature | friction_torque, vibration_rms |
| `injector_wear` | Injector Wear | State | RATIO | DEGRADATION | Wear state D_injector | fuel_flow | fuel_flow |
| `ring_wear` | Ring Wear | State | RATIO | DEGRADATION | Wear state D_ring | manifold_pressure, cht_cyl1 | air_mass_flow |
