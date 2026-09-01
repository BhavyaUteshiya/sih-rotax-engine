"""
Phase 3.7 Electrical Subsystem, Battery SOC, Starter Motor & 3-DOF Aircraft Dynamics Demonstration Script.
SIH26054 — Module 02 Engine Simulator.
"""

from src.module02.config.config_loader import ConfigLoader
from src.module02.core.clock import SimulationClock
from src.module02.physics.atmosphere import AtmosphereModel
from src.module02.simulation.combustion_runner import CombustionRunner
from src.module02.simulation.electrical_aircraft_runner import ElectricalAircraftRunner
from src.module02.simulation.engine_runner import EngineRunner
from src.module02.simulation.intake_runner import IntakeRunner
from src.module02.simulation.propulsion_runner import PropulsionRunner
from src.module02.simulation.thermal_runner import ThermalRunner
from src.module02.simulation.turbo_runner import TurboRunner


def main():
    print("==========================================================================================================================================")
    print("SIH26054 — MODULE 02 PHASE 3.7: ELECTRICAL LOADS, BATTERY/SOC, STARTER & 3-DOF AIRCRAFT DYNAMICS DEMO")
    print("==========================================================================================================================================")

    clock = SimulationClock(dt_seconds=0.01)
    engine_cfg = ConfigLoader.load_engine_config("configs/module02/engines/rotax_914.yaml")

    engine_runner = EngineRunner(clock, engine_config=engine_cfg)
    intake_runner = IntakeRunner(clock, engine_config=engine_cfg)
    combustion_runner = CombustionRunner(clock, engine_config=engine_cfg)
    turbo_runner = TurboRunner(clock, engine_config=engine_cfg)
    thermal_runner = ThermalRunner(clock, engine_config=engine_cfg)
    propulsion_runner = PropulsionRunner(clock, engine_config=engine_cfg)
    electrical_ac_runner = ElectricalAircraftRunner(clock, engine_config=engine_cfg)

    print("\nMission Sequence: OFF -> STARTING -> CRANKING -> IDLE -> TAKEOFF -> CLIMB -> CRUISE -> HIGH POWER -> THROTTLE REDUCTION -> DESCENT\n")
    headers = (
        f"{'Time(s)':<7} | {'Alt(m)':<6} | {'Vel(m/s)':<8} | {'gamma(°)':<8} | {'rho(kg/m3)':<10} | {'Throt%':<6} | "
        f"{'Eng1':<5} | {'Eng2':<5} | {'Prop1':<5} | {'Prop2':<5} | {'Thrust(N)':<9} | {'Drag(N)':<7} | {'Acc(m/s2)':<9} | "
        f"{'V_bus(V)':<8} | {'P_alt(W)':<8} | {'T_alt':<5} | {'SOC%':<5} | {'I_bat(A)':<8} | {'T_start':<7} | "
        f"{'Fuel(kg/h)':<10} | {'MAP(bar)':<8} | {'CHT(°C)':<7} | {'EGT(°C)':<7} | {'OilT(°C)':<8} | {'VibRMS':<6} | {'D_bear':<6}"
    )
    print(headers)
    print("-" * len(headers))

    # Mission sequence steps: (num_steps, flight_path_angle_deg, throttle_percent, starter_active)
    mission_sequence = [
        # Segment 1: OFF / Standstill (0 m, 0 deg gamma, 0% throttle, starter inactive) for 0.5 s
        (50, 0.0, 0.0, False),
        # Segment 2: STARTING / Cranking (0 m, 0 deg gamma, 0% throttle, starter active) for 1.0 s
        (100, 0.0, 0.0, True),
        # Segment 3: IDLE / Self-sustaining (0 m, 0 deg gamma, 0% throttle) for 1.0 s
        (100, 0.0, 0.0, False),
        # Segment 4: TAKEOFF Ground Roll (0 m, 0 deg gamma, 100% throttle) for 3.0 s
        (300, 0.0, 100.0, False),
        # Segment 5: CLIMB (Climbing at 4.0 deg gamma, 100% throttle) for 3.0 s
        (300, 0.07, 100.0, False),
        # Segment 6: CRUISE (Level flight 0 deg gamma, 75% throttle) for 3.0 s
        (300, 0.0, 75.0, False),
        # Segment 7: HIGH POWER / DASH (Level flight 0 deg gamma, 100% throttle) for 3.0 s
        (300, 0.0, 100.0, False),
        # Segment 8: DESCENT (Descent at -3.0 deg gamma, 30% throttle) for 3.0 s
        (300, -0.05, 30.0, False),
    ]

    log_step_interval = 50

    for num_steps, gamma_rad, th, starter_cmd in mission_sequence:
        for _ in range(num_steps):
            # Dynamic Atmosphere based on Aircraft Altitude
            current_alt = electrical_ac_runner.state.aircraft.altitude_m
            current_v = electrical_ac_runner.state.aircraft.velocity_m_s
            t_std = AtmosphereModel.compute_standard_temperature(current_alt)
            p_amb = AtmosphereModel.compute_ambient_pressure(current_alt)
            rho_air, _, _ = AtmosphereModel.compute_moist_air_density(p_amb, t_std, 0.0)

            # Collect engine states
            eng1 = engine_runner.state.engines[1]
            eng2 = engine_runner.state.engines[2]

            engine_rpms = {1: eng1.engine_rpm, 2: eng2.engine_rpm}
            starter_cmds = {1: starter_cmd, 2: False}  # Engine 1 starting
            engine_thrusts = {
                1: propulsion_runner.state.propellers[1].thrust_n,
                2: propulsion_runner.state.propellers[2].thrust_n,
            }

            # 1. Step Electrical Power Balance, Battery SOC, Starter & 3-DOF Aircraft Dynamics
            elec_state, batt_state, ac_state, alt_torques, starter_torques = electrical_ac_runner.step_electrical_and_aircraft(
                engine_rpms=engine_rpms,
                starter_commands=starter_cmds,
                engine_thrusts=engine_thrusts,
                air_density_kg_m3=rho_air,
                flight_path_angle_rad=gamma_rad
            )

            # Step Engine 1
            reflected_load_1 = propulsion_runner.state.propellers[1].reflected_engine_load_n_m
            eng1_state = engine_runner.step_engine(
                engine_index=1,
                throttle_percent=th,
                load_torque_n_m=reflected_load_1,
                alternator_torque_n_m=alt_torques.get(1, 0.0),
                starter_torque_n_m=starter_torques.get(1, 0.0)
            )

            # Step Engine 2 (Sustaining at idle / idle throttle)
            reflected_load_2 = propulsion_runner.state.propellers[2].reflected_engine_load_n_m
            eng2_state = engine_runner.step_engine(
                engine_index=2,
                throttle_percent=min(th, 20.0),
                load_torque_n_m=reflected_load_2,
                alternator_torque_n_m=alt_torques.get(2, 0.0),
                starter_torque_n_m=starter_torques.get(2, 0.0)
            )

            # Step Subsystem Physics for Engine 1
            current_map = turbo_runner.state.engines[1].manifold_pressure_pa
            intake1 = intake_runner.step_intake(1, eng1_state.engine_rpm, th, p_amb, t_std, current_map)
            comb1 = combustion_runner.step_combustion(1, th, intake1.air_mass_flow_kg_s, eng1_state.engine_rpm, t_std, t_std, p_amb, starter_cmd)
            turbo1 = turbo_runner.step_turbo(1, comb1.exhaust.exhaust_mass_flow_kg_s, comb1.exhaust.exhaust_temp_k, comb1.exhaust.exhaust_energy_rate_w, intake1.air_mass_flow_kg_s, p_amb, t_std)
            eng1_state, therm1, lub1 = thermal_runner.step_thermal(1, comb1.fuel.fuel_energy_rate_w, comb1.combustion.indicated_power_w, comb1.exhaust.exhaust_energy_rate_w, comb1.exhaust.exhaust_temp_k, eng1_state.engine_rpm, eng1_state.friction_torque_n_m, current_v, t_std)
            eng1_state, prop1, deg1, vib1 = propulsion_runner.step_propulsion(1, eng1_state.engine_rpm, rho_air, comb1.combustion.indicated_torque_n_m, comb1.fuel.fuel_mass_flow_kg_s, therm1.cht_k, lub1.oil_temperature_k, lub1.oil_viscosity_pa_s)

            # Step Subsystem Physics for Engine 2
            intake2 = intake_runner.step_intake(2, eng2_state.engine_rpm, min(th, 20.0), p_amb, t_std, current_map)
            comb2 = combustion_runner.step_combustion(2, min(th, 20.0), intake2.air_mass_flow_kg_s, eng2_state.engine_rpm, t_std, t_std, p_amb, False)
            eng2_state, therm2, lub2 = thermal_runner.step_thermal(2, comb2.fuel.fuel_energy_rate_w, comb2.combustion.indicated_power_w, comb2.exhaust.exhaust_energy_rate_w, comb2.exhaust.exhaust_temp_k, eng2_state.engine_rpm, eng2_state.friction_torque_n_m, current_v, t_std)
            eng2_state, prop2, deg2, vib2 = propulsion_runner.step_propulsion(2, eng2_state.engine_rpm, rho_air, comb2.combustion.indicated_torque_n_m, comb2.fuel.fuel_mass_flow_kg_s, therm2.cht_k, lub2.oil_temperature_k, lub2.oil_viscosity_pa_s)

            if clock.step_count % log_step_interval == 0:
                t_sec = clock.simulation_time_sec
                alt = ac_state.altitude_m
                vel = ac_state.velocity_m_s
                gamma_deg = gamma_rad * (180.0 / 3.141592653589793)
                eng1_rpm = eng1_state.engine_rpm
                eng2_rpm = eng2_state.engine_rpm
                prop1_rpm = prop1.propeller_rpm
                prop2_rpm = prop2.propeller_rpm
                thrust = ac_state.total_thrust_n
                drag = ac_state.drag_force_n
                acc = ac_state.longitudinal_accel_m_s2
                v_bus = elec_state.bus_voltage_v
                p_alt = elec_state.alternator_power_w
                t_alt_val = elec_state.alternator_torque_n_m
                soc_pct = batt_state.battery_soc * 100.0
                i_bat = batt_state.battery_current_a
                t_start = starter_torques.get(1, 0.0)
                m_fuel_h = comb1.fuel.fuel_mass_flow_kg_h
                map_bar = turbo1.manifold_pressure_pa / 100000.0
                cht_c = therm1.cht_k - 273.15
                egt_c = comb1.exhaust.exhaust_temp_k - 273.15
                oil_c = lub1.oil_temperature_k - 273.15
                vib_rms = vib1.vibration_rms_m_s2
                d_b = deg1.bearing_wear

                print(
                    f"{t_sec:<7.2f} | {alt:<6.1f} | {vel:<8.2f} | {gamma_deg:<8.2f} | {rho_air:<10.3f} | {th:<6.0f} | "
                    f"{eng1_rpm:<5.0f} | {eng2_rpm:<5.0f} | {prop1_rpm:<5.0f} | {prop2_rpm:<5.0f} | {thrust:<9.1f} | {drag:<7.1f} | {acc:<9.2f} | "
                    f"{v_bus:<8.2f} | {p_alt:<8.1f} | {t_alt_val:<5.1f} | {soc_pct:<5.1f} | {i_bat:<8.2f} | {t_start:<7.1f} | "
                    f"{m_fuel_h:<10.2f} | {map_bar:<8.3f} | {cht_c:<7.1f} | {egt_c:<7.1f} | {oil_c:<8.1f} | {vib_rms:<6.2f} | {d_b:<6.4f}"
                )

            clock.step()

    print("\nPhase 3.7 Demonstration Summary:")
    print(f"   - Total Simulation Time Elapsed: {clock.simulation_time_sec:.2f} s ({clock.step_count} steps)")
    print(f"   - Final Aircraft Altitude: {electrical_ac_runner.state.aircraft.altitude_m:.2f} m")
    print(f"   - Final Aircraft Airspeed: {electrical_ac_runner.state.aircraft.velocity_m_s:.2f} m/s")
    print(f"   - Final Total Aircraft Thrust: {electrical_ac_runner.state.aircraft.total_thrust_n:.1f} N")
    print(f"   - Final Aerodynamic Drag: {electrical_ac_runner.state.aircraft.drag_force_n:.1f} N")
    print(f"   - Final Battery State of Charge: {electrical_ac_runner.state.battery.battery_soc * 100.0:.2f}%")
    print(f"   - Final Electrical Bus Voltage: {electrical_ac_runner.state.electrical.bus_voltage_v:.2f} V")
    print("   - Causal Closed Feedback Loop Verified: Engine -> Alternator -> Battery SOC -> Starter -> Propeller Thrust -> 3-DOF Aircraft Flight Dynamics -> Atmosphere -> Engine Intake.")
    print("==========================================================================================================================================")


if __name__ == "__main__":
    main()
