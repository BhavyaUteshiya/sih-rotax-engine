#!/usr/bin/env python3
"""
Phase 3.8 Full Thermodynamic Combustion, Fuel System & Engine Thermal Management Flight Mission Demonstration.
SIH26054 — Module 02 Engine Simulator.
"""

from src.module02.config.config_loader import ConfigLoader
from src.module02.core.clock import SimulationClock
from src.module02.simulation.thermodynamic_engine_runner import ThermodynamicEngineRunner


def main() -> None:
    print("=========================================================================================================")
    print("SIH26054 — MODULE 02: PHASE 3.8 FULL THERMODYNAMIC COMBUSTION & THERMAL MANAGEMENT DEMONSTRATION")
    print("=========================================================================================================")

    clock = SimulationClock(dt_seconds=0.1)
    config = ConfigLoader.load_engine_config("configs/module02/engines/rotax_914.yaml")
    runner = ThermodynamicEngineRunner(clock=clock, engine_config=config)

    # 13 Flight Stages Definition: (Stage Name, Duration Sec, Throttle %, Starter Cmd, Flight Path Angle Rad)
    mission_stages = [
        ("1. OFF", 2.0, 0.0, False, 0.0),
        ("2. STARTING", 2.0, 0.0, True, 0.0),
        ("3. CRANKING", 2.0, 5.0, True, 0.0),
        ("4. LIGHT-OFF", 2.0, 10.0, False, 0.0),
        ("5. IDLE", 3.0, 5.0, False, 0.0),
        ("6. TAKEOFF", 5.0, 100.0, False, 0.15),
        ("7. CLIMB", 5.0, 85.0, False, 0.08),
        ("8. CRUISE", 5.0, 65.0, False, 0.0),
        ("9. HIGH POWER", 5.0, 95.0, False, 0.02),
        ("10. THERMAL LOAD", 5.0, 100.0, False, 0.0),
        ("11. THROTTLE REDUCTION", 3.0, 40.0, False, -0.05),
        ("12. DESCENT", 4.0, 15.0, False, -0.10),
        ("13. SHUTDOWN", 3.0, 0.0, False, 0.0),
    ]

    header = (
        f"{'Stage':<22} | {'Time':<6} | {'Alt(m)':<7} | {'Mass(kg)':<8} | {'Throt%':<6} | {'RPM':<6} | "
        f"{'m_air':<6} | {'m_fuel':<6} | {'AFR':<5} | {'phi':<5} | {'eta_c':<5} | "
        f"{'P_ind':<6} | {'T_ind':<6} | {'N_turbo':<7} | {'MAP(bar)':<8} | {'CHT(C)':<6} | {'Cool(C)':<7} | {'Oil(C)':<6} | {'EGT(C)':<6} | {'Derate':<6}"
    )
    print(header)
    print("-" * len(header))

    for stage_name, duration_sec, th_percent, starter_on, gamma_rad in mission_stages:
        steps = int(duration_sec / clock.dt_seconds)
        for _ in range(steps):
            state = runner.step_thermodynamic_cycle(
                throttles={1: th_percent, 2: th_percent},
                starter_commands={1: starter_on, 2: starter_on},
                flight_path_angle_rad=gamma_rad
            )

        eng1 = state.engines[1]
        thermo1 = state.thermodynamics[1]
        ac = state.aircraft

        t_sim = clock.simulation_time_sec
        alt_m = ac.altitude_m
        ac_mass = ac.gross_mass_kg
        rpm = eng1.engine_rpm
        m_air = eng1.air_mass_flow_kg_s
        m_fuel = thermo1.fuel_mass_flow_kg_h
        afr = thermo1.air_fuel_ratio
        phi = thermo1.equivalence_ratio
        eta_c = thermo1.combustion_efficiency
        p_ind_kw = thermo1.indicated_power_w / 1000.0
        t_ind_nm = thermo1.indicated_torque_n_m
        n_turbo = eng1.turbocharger.turbo_speed_rpm
        map_bar = eng1.turbocharger.max_manifold_absolute_pressure_pa / 100000.0
        cht_c = thermo1.cht_k - 273.15
        cool_c = thermo1.coolant_temp_k - 273.15
        oil_c = thermo1.oil_temp_k - 273.15
        egt_c = thermo1.egt_k - 273.15
        derate = thermo1.thermal_derating_factor

        print(
            f"{stage_name:<22} | {t_sim:6.1f} | {alt_m:7.1f} | {ac_mass:8.2f} | {th_percent:6.1f} | {rpm:6.0f} | "
            f"{m_air:6.3f} | {m_fuel:6.2f} | {afr:5.1f} | {phi:5.2f} | {eta_c:5.2f} | "
            f"{p_ind_kw:6.1f} | {t_ind_nm:6.1f} | {n_turbo:7.0f} | {map_bar:8.3f} | {cht_c:6.1f} | {cool_c:7.1f} | {oil_c:6.1f} | {egt_c:6.1f} | {derate:6.2f}"
        )

    print("=" * len(header))
    print("PHASE 3.8 FULL THERMODYNAMIC COMBUSTION & THERMAL MISSION DEMONSTRATION COMPLETE.")


if __name__ == "__main__":
    main()
