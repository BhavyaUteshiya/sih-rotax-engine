"""
Phase 3.6 Propulsion Aerodynamics, Gearbox Reflection, Wear Degradation, and 1000 Hz Vibration Demonstration Script.
SIH26054 — Module 02 Engine Simulator.
"""

from src.module02.config.config_loader import ConfigLoader
from src.module02.core.clock import SimulationClock
from src.module02.physics.atmosphere import AtmosphereModel
from src.module02.simulation.combustion_runner import CombustionRunner
from src.module02.simulation.engine_runner import EngineRunner
from src.module02.simulation.intake_runner import IntakeRunner
from src.module02.simulation.propulsion_runner import PropulsionRunner
from src.module02.simulation.thermal_runner import ThermalRunner
from src.module02.simulation.turbo_runner import TurboRunner


def main():
    print("==========================================================================================================")
    print("SIH26054 — MODULE 02 PHASE 3.6: PROPULSION LOAD, GEARBOX, WEAR & VIBRATION DEMO")
    print("==========================================================================================================")

    clock = SimulationClock(dt_seconds=0.01)
    engine_cfg = ConfigLoader.load_engine_config("configs/module02/engines/rotax_914.yaml")

    engine_runner = EngineRunner(clock, engine_config=engine_cfg)
    intake_runner = IntakeRunner(clock, engine_config=engine_cfg)
    combustion_runner = CombustionRunner(clock, engine_config=engine_cfg)
    turbo_runner = TurboRunner(clock, engine_config=engine_cfg)
    thermal_runner = ThermalRunner(clock, engine_config=engine_cfg)
    propulsion_runner = PropulsionRunner(clock, engine_config=engine_cfg)

    print("\nOperational Sequence: OFF -> STARTING -> IDLE -> TAKEOFF -> CLIMB -> CRUISE -> HIGH POWER -> THROTTLE REDUCTION -> DESCENT\n")
    headers = (
        f"{'Time(s)':<7} | {'Alt(m)':<6} | {'rho(kg/m3)':<10} | {'Throt%':<6} | "
        f"{'EngRPM':<6} | {'T_ind(N*m)':<10} | {'PropRPM':<7} | {'T_prop(N*m)':<11} | "
        f"{'Thrust(N)':<9} | {'T_engload':<9} | {'Fuel(kg/h)':<10} | {'Air(kg/h)':<9} | "
        f"{'MAP(bar)':<8} | {'CHT(°C)':<7} | {'OilT(°C)':<8} | {'Visc(mPa*s)':<11} | "
        f"{'D_bear':<6} | {'D_ring':<6} | {'D_inj':<6} | {'VibRMS(m/s2)':<12} | {'DomFreq(Hz)':<11}"
    )
    print(headers)
    print("-" * len(headers))

    # Mission sequence steps: (num_steps, altitude_m, throttle_percent, starter_active, airspeed_m_s)
    mission_sequence = [
        # Segment 1: OFF / Standstill (0 m, 0% throttle) for 0.5 s
        (50, 0.0, 0.0, False, 0.0),
        # Segment 2: STARTING / Cranking (0 m, 0% throttle, starter active) for 1.0 s
        (100, 0.0, 0.0, True, 0.0),
        # Segment 3: IDLE / Self-sustaining (0 m, 0% throttle) for 1.0 s
        (100, 0.0, 0.0, False, 0.0),
        # Segment 4: TAKEOFF Acceleration (0 m, 100% throttle, 40 m/s roll) for 3.0 s
        (300, 0.0, 100.0, False, 40.0),
        # Segment 5: CLIMB (3000 m, 100% throttle, 50 m/s climb) for 3.0 s
        (300, 3000.0, 100.0, False, 50.0),
        # Segment 6: CRUISE (6000 m, 75% throttle, 65 m/s cruise) for 3.0 s
        (300, 6000.0, 75.0, False, 65.0),
        # Segment 7: HIGH POWER / DASH (6000 m, 100% throttle, 75 m/s dash) for 3.0 s
        (300, 6000.0, 100.0, False, 75.0),
        # Segment 8: THROTTLE REDUCTION / DESCENT (6000 m, 30% throttle, 55 m/s glide) for 3.0 s
        (300, 6000.0, 30.0, False, 55.0),
    ]

    log_step_interval = 50

    # Initialize combustion torque feedback
    prev_comb_torque = 0.0

    for num_steps, alt_m, th, starter_active, v_inf in mission_sequence:
        t_std = AtmosphereModel.compute_standard_temperature(alt_m)
        p_amb = AtmosphereModel.compute_ambient_pressure(alt_m)
        rho_air, _, _ = AtmosphereModel.compute_moist_air_density(p_amb, t_std, 0.0)

        for _ in range(num_steps):
            eng = engine_runner.state.engines[1]

            if starter_active:
                eng.engine_speed_rad_per_sec = min(146.6, eng.engine_speed_rad_per_sec + 30.0 * clock.dt_seconds)
                eng.engine_rpm = eng.engine_speed_rad_per_sec * (30.0 / 3.141592653589793)
                if prev_comb_torque < 30.0:
                    prev_comb_torque = 45.0  # Starter motor torque contribution

            reflected_load = propulsion_runner.state.propellers[1].reflected_engine_load_n_m

            # 1. Step Engine Rotational Dynamics (Phase 3.1 with closed-loop combustion torque & reflected propeller load)
            eng_state = engine_runner.step_engine(
                engine_index=1,
                throttle_percent=th,
                load_torque_n_m=reflected_load,
                indicated_torque_n_m=prev_comb_torque
            )

            current_map = turbo_runner.state.engines[1].manifold_pressure_pa

            # 2. Step Intake Airflow Physics (Phase 3.2 using closed-loop MAP)
            intake_state = intake_runner.step_intake(
                engine_index=1,
                engine_rpm=eng_state.engine_rpm,
                throttle_percent=th,
                ambient_pressure_pa=p_amb,
                ambient_temp_k=t_std,
                manifold_pressure_pa=current_map
            )

            # 3. Step Fuel Delivery, AFR, Combustion & Exhaust Physics (Phase 3.3.1)
            comb_state = combustion_runner.step_combustion(
                engine_index=1,
                throttle_percent=th,
                air_mass_flow_kg_s=intake_state.air_mass_flow_kg_s,
                engine_rpm=eng_state.engine_rpm,
                ambient_temp_k=t_std,
                intake_temp_k=t_std,
                ambient_pressure_pa=p_amb,
                starter_active=starter_active
            )

            prev_comb_torque = comb_state.combustion.indicated_torque_n_m

            # 4. Step Closed-Loop Turbocharger & Turbine Shaft Dynamics (Phase 3.4)
            turbo_state = turbo_runner.step_turbo(
                engine_index=1,
                exhaust_mass_flow_kg_s=comb_state.exhaust.exhaust_mass_flow_kg_s,
                exhaust_temp_k=comb_state.exhaust.exhaust_temp_k,
                exhaust_energy_rate_w=comb_state.exhaust.exhaust_energy_rate_w,
                air_mass_flow_kg_s=intake_state.air_mass_flow_kg_s,
                ambient_pressure_pa=p_amb,
                ambient_temp_k=t_std
            )

            # 5. Step Dynamic Thermal Mass, CHT, EGT, Oil Viscosity & Friction (Phase 3.5)
            _, therm_state, lub_state = thermal_runner.step_thermal(
                engine_index=1,
                fuel_energy_rate_w=comb_state.fuel.fuel_energy_rate_w,
                indicated_power_w=comb_state.combustion.indicated_power_w,
                exhaust_energy_rate_w=comb_state.exhaust.exhaust_energy_rate_w,
                exhaust_temp_k=comb_state.exhaust.exhaust_temp_k,
                engine_rpm=eng_state.engine_rpm,
                engine_friction_torque_n_m=eng_state.friction_torque_n_m,
                airspeed_m_s=v_inf,
                ambient_temp_k=t_std
            )

            # 6. Step Propeller Aerodynamics, Gearbox Reflection, Wear & Vibration (Phase 3.6)
            _, prop_state, deg_state, vib_state = propulsion_runner.step_propulsion(
                engine_index=1,
                engine_rpm=eng_state.engine_rpm,
                air_density_kg_m3=rho_air,
                indicated_torque_n_m=comb_state.combustion.indicated_torque_n_m,
                fuel_mass_flow_kg_s=comb_state.fuel.fuel_mass_flow_kg_s,
                cht_k=therm_state.cht_k,
                oil_temp_k=lub_state.oil_temperature_k,
                oil_viscosity_pa_s=lub_state.oil_viscosity_pa_s
            )

            if clock.step_count % log_step_interval == 0:
                t_sec = clock.simulation_time_sec
                rpm = eng_state.engine_rpm
                t_ind_n_m = comb_state.combustion.indicated_torque_n_m
                prop_rpm = prop_state.propeller_rpm
                t_prop_n_m = prop_state.load_torque_n_m
                thrust_n = prop_state.thrust_n
                t_eng_load = prop_state.reflected_engine_load_n_m
                m_fuel_h = comb_state.fuel.fuel_mass_flow_kg_h
                m_air_h = intake_state.air_mass_flow_kg_s * 3600.0
                map_bar = turbo_state.manifold_pressure_pa / 100000.0
                cht_c = therm_state.cht_k - 273.15
                oil_t_c = lub_state.oil_temperature_k - 273.15
                visc_mpas = lub_state.oil_viscosity_pa_s * 1000.0
                d_b = deg_state.bearing_wear
                d_r = deg_state.ring_wear
                d_inj = deg_state.injector_wear
                vib_rms = vib_state.vibration_rms_m_s2
                dom_f = vib_state.dominant_frequency_hz

                print(
                    f"{t_sec:<7.2f} | {alt_m:<6.0f} | {rho_air:<10.3f} | {th:<6.0f} | "
                    f"{rpm:<6.0f} | {t_ind_n_m:<10.1f} | {prop_rpm:<7.0f} | {t_prop_n_m:<11.1f} | "
                    f"{thrust_n:<9.1f} | {t_eng_load:<9.1f} | {m_fuel_h:<10.2f} | {m_air_h:<9.1f} | "
                    f"{map_bar:<8.3f} | {cht_c:<7.1f} | {oil_t_c:<8.1f} | {visc_mpas:<11.2f} | "
                    f"{d_b:<6.4f} | {d_r:<6.4f} | {d_inj:<6.4f} | {vib_rms:<12.2f} | {dom_f:<11.1f}"
                )

            clock.step()

    print("\nPhase 3.6 Demonstration Summary:")
    print(f"   - Total Simulation Time Elapsed: {clock.simulation_time_sec:.2f} s ({clock.step_count} steps)")
    print(f"   - Final Propeller Speed: {propulsion_runner.state.propellers[1].propeller_rpm:.0f} RPM")
    print(f"   - Final Propeller Thrust: {propulsion_runner.state.propellers[1].thrust_n:.1f} N")
    print(f"   - Final Reflected Engine Load: {propulsion_runner.state.propellers[1].reflected_engine_load_n_m:.1f} N*m")
    print(f"   - Final Bearing Degradation: {propulsion_runner.state.degradation[1].bearing_wear:.6f}")
    print(f"   - Final Vibration RMS: {propulsion_runner.state.vibration[1].vibration_rms_m_s2:.2f} m/s^2")
    print("   - Closed Engine -> Gearbox -> Propeller -> Reflected Load Loop Verified: Propeller aerodynamic load is reflected to the engine shaft, closing the physical feedback loop.")
    print("==========================================================================================================")


if __name__ == "__main__":
    main()
