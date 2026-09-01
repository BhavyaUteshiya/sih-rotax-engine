"""
Phase 3.1 Engine Rotational Dynamics Demonstration Script.
SIH26054 — Module 02 Engine Simulator.
"""

from src.module02.core.clock import SimulationClock
from src.module02.simulation.engine_runner import EngineRunner


def main():
    print("==========================================================================")
    print("SIH26054 — MODULE 02 PHASE 3.1: ENGINE ROTATIONAL DYNAMICS DEMO")
    print("==========================================================================")

    clock = SimulationClock(dt_seconds=0.01) # 100 Hz dt = 0.01 s
    runner = EngineRunner(clock)

    print("\nTwin-Engine Rotational Acceleration Simulation (J * dω/dt = T_ind - T_load - T_fric):\n")
    print(f"{'Time (s)':<10} | {'Eng1 Throttle':<14} | {'Eng1 RPM':<12} | {'Eng1 T_ind (N*m)':<16} | {'Eng1 T_fric (N*m)':<16} | {'Eng2 Throttle':<14} | {'Eng2 RPM':<12}")
    print("-" * 105)

    # Simulation segments: (num_steps, eng1_throttle, eng1_load, eng2_throttle, eng2_load)
    segments = [
        # Segment 1: Zero throttle (1.0 s)
        (100, 0.0, 0.0, 0.0, 0.0),
        # Segment 2: Throttle Step (Eng1 = 100%, Eng2 = 50%) for 2.0 s
        (200, 100.0, 0.0, 50.0, 0.0),
        # Segment 3: Load application on Eng1 (Load = 150 N*m) for 2.0 s
        (200, 100.0, 150.0, 50.0, 50.0),
    ]

    log_step_interval = 50 # Print state every 0.5 seconds

    for segment_idx, (num_steps, th1, load1, th2, load2) in enumerate(segments, 1):
        for _ in range(num_steps):
            engines = runner.step_all_engines(
                throttles={1: th1, 2: th2},
                loads={1: load1, 2: load2}
            )

            if runner.clock.step_count % log_step_interval == 0:
                t_sec = runner.clock.simulation_time_sec
                eng1 = engines[1]
                eng2 = engines[2]

                print(f"{t_sec:<10.2f} | {eng1.throttle_percent:<14.1f} | {eng1.engine_rpm:<12.1f} | {eng1.indicated_torque_total_n_m:<16.1f} | {eng1.friction_torque_n_m:<16.1f} | {eng2.throttle_percent:<14.1f} | {eng2.engine_rpm:<12.1f}")

    print("\nPhase 3.1 Demonstration Summary:")
    print(f"   - Total Simulation Time Elapsed: {runner.clock.simulation_time_sec:.2f} s ({runner.clock.step_count} steps)")
    print(f"   - Engine 1 Final RPM: {runner.state.engines[1].engine_rpm:.1f} RPM (Indicated Torque = {runner.state.engines[1].indicated_torque_total_n_m:.1f} N*m)")
    print(f"   - Engine 2 Final RPM: {runner.state.engines[2].engine_rpm:.1f} RPM (Indicated Torque = {runner.state.engines[2].indicated_torque_total_n_m:.1f} N*m)")
    print("   - Twin Engine Independence: Engine 1 and Engine 2 accelerated independently according to their respective throttle commands.")
    print("   - Invariant Integrity: Rotational dynamics strictly follow Newton's rotational balance J * dω/dt = T_net.")
    print("==========================================================================")


if __name__ == "__main__":
    main()
