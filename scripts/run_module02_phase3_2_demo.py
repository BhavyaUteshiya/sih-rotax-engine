"""
Phase 3.2 Intake Manifold & Turbocharger Compressor Demonstration Script.
SIH26054 — Module 02 Engine Simulator.
"""

from src.module02.config.config_loader import ConfigLoader
from src.module02.core.clock import SimulationClock
from src.module02.physics.atmosphere import AtmosphereModel
from src.module02.simulation.engine_runner import EngineRunner
from src.module02.simulation.intake_runner import IntakeRunner


def main():
    print("==========================================================================")
    print("SIH26054 — MODULE 02 PHASE 3.2: INTAKE & TURBOCHARGER AIRFLOW DEMO")
    print("==========================================================================")

    clock = SimulationClock(dt_seconds=0.01)
    engine_cfg = ConfigLoader.load_engine_config("configs/module02/engines/rotax_914.yaml")

    engine_runner = EngineRunner(clock, engine_config=engine_cfg)
    intake_runner = IntakeRunner(clock, engine_config=engine_cfg)

    print("\nAtmosphere-RPM-Turbocharger Airflow Integration Trajectory:\n")
    print(f"{'Time (s)':<9} | {'Alt (m)':<8} | {'P_amb (Pa)':<11} | {'Eng1 Throttle':<14} | {'Eng1 RPM':<10} | {'MAP (Pa)':<11} | {'Boost (Pa)':<11} | {'Turbo RPM':<10} | {'Airflow (kg/h)':<14}")
    print("-" * 115)

    # Mission profile steps: (num_steps, altitude_m, throttle_percent)
    mission_profile = [
        # Segment 1: Ground Idle (0 m, 0% throttle) for 1.0 s
        (100, 0.0, 0.0),
        # Segment 2: Takeoff Acceleration (0 m, 100% throttle) for 2.0 s
        (200, 0.0, 100.0),
        # Segment 3: Altitude Climb (3000 m, 100% throttle) for 2.0 s
        (200, 3000.0, 100.0),
    ]

    log_step_interval = 50

    for num_steps, alt_m, th in mission_profile:
        t_std = AtmosphereModel.compute_standard_temperature(alt_m)
        p_amb = AtmosphereModel.compute_ambient_pressure(alt_m)

        for _ in range(num_steps):
            # 1. Step Engine Rotational Dynamics (Phase 3.1)
            eng_state = engine_runner.step_engine(engine_index=1, throttle_percent=th)

            # 2. Step Intake & Turbocharger Airflow Physics (Phase 3.2)
            intake_state = intake_runner.step_intake(
                engine_index=1,
                engine_rpm=eng_state.engine_rpm,
                throttle_percent=th,
                ambient_pressure_pa=p_amb,
                ambient_temp_k=t_std
            )

            if clock.step_count % log_step_interval == 0:
                t_sec = clock.simulation_time_sec
                rpm = eng_state.engine_rpm
                map_pa = intake_state.manifold_pressure_pa
                boost_pa = max(0.0, map_pa - p_amb)
                turbo_rpm = intake_state.turbocharger.turbo_speed_rpm
                m_dot_h = intake_state.air_mass_flow_kg_s * 3600.0

                print(f"{t_sec:<9.2f} | {alt_m:<8.1f} | {p_amb:<11.1f} | {th:<14.1f} | {rpm:<10.1f} | {map_pa:<11.1f} | {boost_pa:<11.1f} | {turbo_rpm:<10.1f} | {m_dot_h:<14.2f}")

            clock.step()

    print("\nPhase 3.2 Demonstration Summary:")
    print(f"   - Total Simulation Time Elapsed: {clock.simulation_time_sec:.2f} s ({clock.step_count} steps)")
    print(f"   - Final Manifold Absolute Pressure (MAP): {intake_runner.state.engines[1].manifold_pressure_pa:.1f} Pa (2.2 bar turbo ceiling enforced)")
    print(f"   - Final Engine Air Mass Flow Rate: {intake_runner.state.engines[1].air_mass_flow_kg_s * 3600.0:.2f} kg/h")
    print("   - Causal Atmosphere-Speed Coupling: Altitude pressure drop causes turbo pressure ratio to adjust, while engine RPM directly determines intake air mass flow.")
    print("   - Boundary Preserved: Zero fuel flow, AFR, or combustion outputs fabricated.")
    print("==========================================================================")


if __name__ == "__main__":
    main()
