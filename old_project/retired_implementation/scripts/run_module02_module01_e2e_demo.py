#!/usr/bin/env python3
"""
Module 02 Simulator -> Telemetry Transport -> Module 01 Ingestion -> Dataset Exporter End-to-End Demonstration Script.
SIH26054 — Module 02 Engine Simulator.
"""

from src.module02.integration.integration_runner import MasterIntegrationRunner


def main() -> None:
    print("=========================================================================================================")
    print("SIH26054 — SIMULATOR -> MODULE 01 END-TO-END DEMONSTRATION")
    print("=========================================================================================================")
    print("MODULE 02: TAPAS-BH-201 Simulator -> Telemetry Generator -> CAN Transport -> MODULE 01: Data Ingestion")
    print("Raw Store -> Decode / SI Normalize / Validate -> Normalized Store -> Dataset Export")
    print("=========================================================================================================")

    runner = MasterIntegrationRunner(clock_dt=0.01)

    mission_stages = [
        ("GROUND", 2.0, 0.0, False, 0.0),
        ("ENGINE START", 2.0, 0.0, True, 0.0),
        ("CRANKING", 2.0, 5.0, True, 0.0),
        ("LIGHT-OFF", 2.0, 10.0, False, 0.0),
        ("IDLE", 3.0, 5.0, False, 0.0),
        ("TAXI", 3.0, 15.0, False, 0.0),
        ("TAKEOFF", 5.0, 100.0, False, 0.15),
        ("CLIMB", 5.0, 85.0, False, 0.08),
        ("CRUISE", 5.0, 65.0, False, 0.0),
        ("HIGH POWER", 5.0, 95.0, False, 0.02),
        ("THROTTLE REDUCTION", 3.0, 40.0, False, -0.05),
        ("DESCENT", 4.0, 15.0, False, -0.10),
        ("LANDING", 3.0, 5.0, False, 0.0),
        ("SHUTDOWN", 3.0, 0.0, False, 0.0),
    ]

    header = (
        f"{'Stage':<19} | {'SimTime':<7} | {'Alt(m)':<6} | {'Throt%':<6} | {'Eng1 RPM':<8} | {'Eng2 RPM':<8} | "
        f"{'MAP(bar)':<8} | {'m_fuel':<6} | {'AFR':<5} | {'EGT(C)':<6} | {'CHT(C)':<6} | {'Oil(C)':<6} | {'SOC%':<5} | {'Mass(kg)':<8} | {'SeqNum':<6}"
    )
    print(header)
    print("-" * len(header))

    for stage_name, duration_sec, th_percent, starter_on, gamma_rad in mission_stages:
        # Run stage continuous integration
        metrics = runner.run_simulation(
            duration_sec=duration_sec,
            throttles={1: th_percent, 2: th_percent},
            starter_commands={1: starter_on, 2: starter_on},
            flight_path_angle_rad=gamma_rad,
            scenario_id=stage_name
        )

        st = runner.simulator.state
        eng1 = st.engines[1]
        eng2 = st.engines[2]
        thermo1 = st.thermodynamics[1]
        ac = st.aircraft

        t_sim = runner.clock.simulation_time_sec
        alt_m = ac.altitude_m
        rpm1 = eng1.engine_rpm
        rpm2 = eng2.engine_rpm
        map_bar = eng1.turbocharger.max_manifold_absolute_pressure_pa / 100000.0
        m_fuel = thermo1.fuel_mass_flow_kg_h
        afr = thermo1.air_fuel_ratio
        egt_c = thermo1.egt_k - 273.15
        cht_c = thermo1.cht_k - 273.15
        oil_c = thermo1.oil_temp_k - 273.15
        soc_pct = st.battery.battery_soc * 100.0
        ac_mass = ac.gross_mass_kg
        seq_num = runner.scheduler.sequence_numbers.get("can0_eng1", 0)

        print(
            f"{stage_name:<19} | {t_sim:7.1f} | {alt_m:6.1f} | {th_percent:6.1f} | {rpm1:8.0f} | {rpm2:8.0f} | "
            f"{map_bar:8.3f} | {m_fuel:6.2f} | {afr:5.1f} | {egt_c:6.1f} | {cht_c:6.1f} | {oil_c:6.1f} | {soc_pct:5.1f} | {ac_mass:8.2f} | {seq_num:6d}"
        )

    print("=" * len(header))
    print("END-TO-END METRICS SUMMARY:")
    metrics = runner.get_metrics()
    print(f"  Records Generated : {metrics['records_generated']}")
    print(f"  Records Published : {metrics['records_published']}")
    print(f"  Records Received  : {metrics['records_received']}")
    print(f"  Records Ingested  : {metrics['records_ingested']}")
    print(f"  Records Failed    : {metrics['records_failed']}")
    print(f"  Records Dropped   : {metrics['records_dropped']}")
    print(f"  Records Persisted : {metrics['records_persisted']}")
    print("-" * len(header))

    # Export datasets
    csv_path, jsonl_path = runner.export_datasets()
    print(f"DATASET EXPORTS CREATED:")
    print(f"  CSV   : {csv_path}")
    print(f"  JSONL : {jsonl_path}")

    # Display Raw Packet & Normalized Telemetry Examples
    print("-" * len(header))
    print("RAW PACKET SAMPLE:")
    pkt_ids = list(runner.bridge.pipeline.raw_store._written_packet_ids)
    raw_packet = runner.bridge.pipeline.raw_store.get_by_packet_id(pkt_ids[0]) if pkt_ids else None
    if raw_packet:
        print(f"  packet_id              : {raw_packet.packet_id}")
        print(f"  payload_sha256         : {raw_packet.payload_sha256}")
        print(f"  stream_id              : {raw_packet.stream_id}")
        print(f"  sequence_number        : {raw_packet.sequence_number}")
        print(f"  physical_origin        : {raw_packet.physical_origin.value}")
        print(f"  raw_bytes_hex          : {raw_packet.raw_bytes.hex()}")

    print("-" * len(header))
    print("NORMALIZED TELEMETRY SAMPLE:")
    if runner.recorded_dataset_records:
        rec = runner.recorded_dataset_records[0]
        print(f"  parameter_id           : {rec.parameter_id}")
        print(f"  display_value          : {rec.display_value} {rec.display_unit}")
        print(f"  canonical_value        : {rec.canonical_value} {rec.canonical_unit}")
        print(f"  validity               : {rec.validity}")
        print(f"  physical_origin        : {rec.physical_origin}")
        print(f"  state_category         : {rec.state_category}")

    print("=" * len(header))
    print("SIMULATOR TO MODULE 01 END-TO-END DEMONSTRATION COMPLETE.")


if __name__ == "__main__":
    main()
