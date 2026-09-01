import os

yaml_path = r"configs\module02\engines\rotax_914.yaml"
with open(yaml_path, 'r', encoding='utf-8') as f:
    content = f.read()

replacements = [
    (
        "  max_safe_oil_temp_k:\n    value: 383.15\n    unit: KELVIN\n    classification: ESTIMATED\n    source: USER_PROVIDED_ROTAX_914_ENGINEERING_BASELINE",
        "  max_safe_oil_temp_k:\n    value: 403.15\n    unit: KELVIN\n    classification: VERIFIED\n    source: USER_PROVIDED_ROTAX_914_SPECIFICATION"
    ),
    (
        "  engine_to_propeller_speed_ratio:\n    value: 0.4115226337448559\n    unit: RATIO\n    classification: DERIVED\n    source: USER_PROVIDED_ROTAX_914_SPECIFICATION",
        "  engine_to_propeller_speed_ratio:\n    value: 0.41175986\n    unit: RATIO\n    classification: VERIFIED\n    source: USER_PROVIDED_ROTAX_914_SPECIFICATION"
    ),
    (
        "  lower_heating_value_j_kg:\n    value: 44000000.0\n    unit: J_PER_KG\n    classification: ASSUMED\n    source: STANDARD_GASOLINE_FUEL_DATA",
        "  lower_heating_value_j_kg:\n    value: 43400000.0\n    unit: J_PER_KG\n    classification: ESTIMATED\n    source: ROTAX_914_ENGINEERING_BASELINE"
    ),
    (
        "  lower_heating_value_lhv_j_kg:\n    value: 44000000.0\n    unit: J_PER_KG\n    classification: ASSUMED\n    source: STANDARD_GASOLINE_FUEL_DATA",
        "  lower_heating_value_lhv_j_kg:\n    value: 43400000.0\n    unit: J_PER_KG\n    classification: ESTIMATED\n    source: ROTAX_914_ENGINEERING_BASELINE"
    ),
    (
        "  idle_fuel_flow_kg_h:\n    value: 1.8\n    unit: KG_PER_HOUR\n    classification: ESTIMATED\n    source: ROTAX_914_REDUCED_ORDER_MODEL",
        "  idle_fuel_flow_kg_h:\n    value: 1.3\n    unit: KG_PER_HOUR\n    classification: ESTIMATED\n    source: ROTAX_914_ENGINEERING_BASELINE"
    ),
    (
        "  max_fuel_flow_kg_h:\n    value: 18.5\n    unit: KG_PER_HOUR\n    classification: ESTIMATED\n    source: ROTAX_914_115HP_ENERGY_CALIBRATION",
        "  max_fuel_flow_kg_h:\n    value: 23.4\n    unit: KG_PER_HOUR\n    classification: ESTIMATED\n    source: ROTAX_914_ENGINEERING_BASELINE"
    ),
    (
        "  max_compressor_pressure_ratio:\n    value: 1.55\n    unit: RATIO\n    classification: ESTIMATED\n    source: ANALOGOUS_TURBO_MAP",
        "  max_compressor_pressure_ratio:\n    value: 2.15\n    unit: RATIO\n    classification: DERIVED\n    source: ROTAX_914_ENGINEERING_BASELINE"
    ),
    (
        "  indicated_efficiency_peak:\n    value: 0.42\n    unit: RATIO\n    classification: ESTIMATED\n    source: ROTAX_914_REDUCED_ORDER_MODEL",
        "  indicated_efficiency_peak:\n    value: 0.30\n    unit: RATIO\n    classification: ESTIMATED\n    source: ROTAX_914_ENGINEERING_BASELINE"
    ),
    (
        "  compressor_efficiency_peak: &id003\n    value: 0.76\n    unit: RATIO\n    classification: ESTIMATED\n    source: ANALOGOUS_TURBO_MAP",
        "  compressor_efficiency_peak: &id003\n    value: 0.75\n    unit: RATIO\n    classification: ESTIMATED\n    source: ANALOGOUS_TURBO_MAP"
    ),
    (
        "  lag_tau_s: &id006\n    value: 0.8\n    unit: SECOND\n    classification: ESTIMATED\n    source: USER_PROVIDED_ROTAX_914_ENGINEERING_BASELINE",
        "  lag_tau_s: &id006\n    value: 0.5\n    unit: SECOND\n    classification: ESTIMATED\n    source: USER_PROVIDED_ROTAX_914_ENGINEERING_BASELINE"
    ),
    (
        "  rotational_inertia_kg_m2:\n    value: 0.12\n    unit: KG_M2\n    classification: ESTIMATED\n    source: ROTAX_914_REDUCED_ORDER_MODEL",
        "  rotational_inertia_kg_m2:\n    value: 0.15\n    unit: KG_M2\n    classification: ESTIMATED\n    source: ROTAX_914_REDUCED_ORDER_MODEL"
    ),
    (
        "  gearbox_efficiency:\n    value: 0.98\n    unit: RATIO\n    classification: ESTIMATED\n    source: ROTAX_914_REDUCED_ORDER_MODEL",
        "  gearbox_efficiency:\n    value: 0.97\n    unit: RATIO\n    classification: ESTIMATED\n    source: ROTAX_914_REDUCED_ORDER_MODEL"
    ),
    (
        "  diameter_m:\n    value: 1.9\n    unit: METER\n    classification: ASSUMED\n    source: EXISTING_AIRFRAME_PROPULSION_GEOMETRY",
        "  diameter_m:\n    value: 1.7\n    unit: METER\n    classification: SYNTHETIC\n    source: ROTAX_914_PROPULSION_CALIBRATION"
    ),
    (
        "  torque_coefficient_cq:\n    value: 0.0065\n    unit: COEFFICIENT\n    classification: ESTIMATED\n    source: ROTAX_914_PROPULSION_CALIBRATION",
        "  torque_coefficient_cq:\n    value: 0.0125\n    unit: COEFFICIENT\n    classification: SYNTHETIC\n    source: ROTAX_914_PROPULSION_CALIBRATION"
    ),
    (
        "  thrust_coefficient_ct:\n    value: 0.085\n    unit: COEFFICIENT\n    classification: ESTIMATED\n    source: ROTAX_914_PROPULSION_CALIBRATION",
        "  thrust_coefficient_ct:\n    value: 0.075\n    unit: COEFFICIENT\n    classification: SYNTHETIC\n    source: ROTAX_914_PROPULSION_CALIBRATION"
    )
]

new_content = content
for old_s, new_s in replacements:
    if old_s not in new_content:
        print(f"Warning: Chunk not found:\n{old_s}\n")
    new_content = new_content.replace(old_s, new_s)

with open(yaml_path, 'w', encoding='utf-8') as f:
    f.write(new_content)

print("Done replacing.")
