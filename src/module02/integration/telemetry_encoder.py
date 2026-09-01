"""
Telemetry Encoder: Encodes Module 02 SimulationState into CAN Payloads & Raw Packets.
SIH26054 — Module 02 Engine Simulator.
"""

import hashlib
import struct
from dataclasses import dataclass
from typing import Dict, List, Tuple

from src.module02.models.states import EngineState, SimulationState


def compute_payload_sha256(raw_bytes: bytes) -> str:
    """Computes lower-case 64-character SHA-256 hash over raw payload bytes."""
    return hashlib.sha256(raw_bytes).hexdigest()


@dataclass(frozen=True)
class EncodedCanFrame:
    """Container for encoded CAN frame data prior to transport."""
    can_id: int
    payload: bytes
    dlc: int
    stream_id: str
    sequence_number: int
    source_timestamp: float
    engine_index: int
    payload_sha256: str


class TelemetryEncoder:
    """
    Encodes full Module 02 simulation state (Environment, Flight, Engine, Intake/Turbo, Fuel,
    Combustion, Exhaust, Thermal, Electrical, Propulsion, Degradation, Vibration) for Engine 1
    and Engine 2 into deterministic CAN frames.
    """

    @classmethod
    def encode_simulation_state(
        cls,
        state: SimulationState,
        sequence_numbers: Dict[str, int],
        source_timestamp: float
    ) -> List[EncodedCanFrame]:
        """
        Encodes complete master SimulationState into deterministic EncodedCanFrame list.
        Supports twin-engine independent CAN message streams.
        """
        frames: List[EncodedCanFrame] = []

        # 1. Encode Engine 1 & Engine 2 Frames
        for eng_idx in [1, 2]:
            eng = state.engines.get(eng_idx)
            thermo = state.thermodynamics.get(eng_idx)
            therm = state.thermals.get(eng_idx)
            lub = state.lubrication.get(eng_idx)
            prop = state.propellers.get(eng_idx) if hasattr(state, "propellers") and state.propellers else None
            if prop is None and hasattr(state, "propulsion") and state.propulsion is not None:
                prop_map = getattr(state.propulsion, "propellers", {})
                prop = prop_map.get(eng_idx)
            deg = state.degradation.get(eng_idx)
            vib = state.vibration.get(eng_idx)

            if eng is None:
                continue

            stream_id = f"can0_eng{eng_idx}"
            seq = sequence_numbers.get(stream_id, 0)
            base_can_id = 0x100 if eng_idx == 1 else 0x200

            # 0x101 / 0x201: ECU_ENGINE_STATUS_1 (RPM, Oil Pressure bar, Fuel Flow kg/h)
            rpm_int = max(0, min(65535, int(round(eng.engine_rpm))))
            p_oil_bar = (eng.engine_rpm / 1000.0) * 1.5 if eng.engine_rpm > 100 else 0.0
            oil_p_int = max(0, min(65535, int(round(p_oil_bar * 100.0))))
            fuel_h = thermo.fuel_mass_flow_kg_h if thermo else 0.0
            fuel_int = max(0, min(65535, int(round(fuel_h * 100.0))))
            p1 = struct.pack("<HHH2x", rpm_int, oil_p_int, fuel_int)
            frames.append(cls._build_frame(base_can_id + 0x01, p1, stream_id, seq, source_timestamp, eng_idx))

            # 0x102 / 0x202: ECU_TEMPERATURES_1 (CHT 1, CHT 2, Oil Temp)
            cht1_c = (thermo.cht_k - 273.15) if thermo else 15.0
            cht2_c = cht1_c + (1.5 if eng_idx == 1 else -1.0)
            oil_t_c = (thermo.oil_temp_k - 273.15) if thermo else 15.0
            cht1_int = max(0, min(65535, int(round((cht1_c + 40.0) * 10.0))))
            cht2_int = max(0, min(65535, int(round((cht2_c + 40.0) * 10.0))))
            oil_t_int = max(0, min(65535, int(round((oil_t_c + 40.0) * 10.0))))
            p2 = struct.pack("<HHH2x", cht1_int, cht2_int, oil_t_int)
            frames.append(cls._build_frame(base_can_id + 0x02, p2, stream_id, seq + 1, source_timestamp, eng_idx))

            # 0x103 / 0x203: ECU_ELECTRICAL_STATUS (Battery Voltage, Alternator Current, Injection Timing)
            v_bat = state.battery.battery_voltage_v
            i_alt = state.electrical.alternator_current_a / 2.0
            inj_timing = thermo.injection_timing_deg_btdc if thermo else 18.0
            v_bat_int = max(0, min(65535, int(round(v_bat * 100.0))))
            i_alt_int = max(0, min(65535, int(round(i_alt * 10.0))))
            inj_int = max(0, min(65535, int(round(inj_timing * 10.0))))
            p3 = struct.pack("<HHH2x", v_bat_int, i_alt_int, inj_int)
            frames.append(cls._build_frame(base_can_id + 0x03, p3, stream_id, seq + 2, source_timestamp, eng_idx))

            # 0x104 / 0x204: ECU_PERFORMANCE (Indicated Torque, MAP, Turbo Speed)
            t_ind = thermo.indicated_torque_n_m if thermo else 0.0
            map_bar = (eng.turbocharger.max_manifold_absolute_pressure_pa / 100000.0) if eng.turbocharger else 1.013
            n_turbo = eng.turbocharger.turbo_speed_rpm if eng.turbocharger else 0.0
            t_ind_int = max(0, min(65535, int(round(t_ind * 10.0))))
            map_int = max(0, min(65535, int(round(map_bar * 1000.0))))
            n_turbo_int = max(0, min(65535, int(round(n_turbo / 10.0))))
            p4 = struct.pack("<HHH2x", t_ind_int, map_int, n_turbo_int)
            frames.append(cls._build_frame(base_can_id + 0x04, p4, stream_id, seq + 3, source_timestamp, eng_idx))

            # 0x105 / 0x205: ECU_COMBUSTION (Airflow kg/s, AFR, Combustion Efficiency %)
            m_air = eng.air_mass_flow_kg_s
            afr = thermo.air_fuel_ratio if thermo else 0.0
            eta_c = thermo.combustion_efficiency if thermo else 0.0
            m_air_int = max(0, min(65535, int(round(m_air * 10000.0))))
            afr_int = max(0, min(65535, int(round(afr * 10.0))))
            eta_c_int = max(0, min(65535, int(round(eta_c * 1000.0))))
            p5 = struct.pack("<HHH2x", m_air_int, afr_int, eta_c_int)
            frames.append(cls._build_frame(base_can_id + 0x05, p5, stream_id, seq + 4, source_timestamp, eng_idx))

            # 0x106 / 0x206: ECU_THERMAL_EXHAUST (EGT, Coolant Temp, Derating Factor %)
            egt_c = (thermo.egt_k - 273.15) if thermo else 15.0
            cool_c = (thermo.coolant_temp_k - 273.15) if thermo else 15.0
            derate = thermo.thermal_derating_factor if thermo else 1.0
            egt_int = max(0, min(65535, int(round((egt_c + 40.0) * 10.0))))
            cool_int = max(0, min(65535, int(round((cool_c + 40.0) * 10.0))))
            derate_int = max(0, min(65535, int(round(derate * 1000.0))))
            p6 = struct.pack("<HHH2x", egt_int, cool_int, derate_int)
            frames.append(cls._build_frame(base_can_id + 0x06, p6, stream_id, seq + 5, source_timestamp, eng_idx))

            # 0x107 / 0x207: PROPULSION_STATUS (Propeller RPM, Propeller Torque, Propeller Thrust)
            prop_rpm = prop.propeller_rpm if prop else 0.0
            prop_t = prop.load_torque_n_m if prop else 0.0
            prop_f = prop.thrust_n if prop else 0.0
            p_rpm_int = max(0, min(65535, int(round(prop_rpm))))
            p_t_int = max(0, min(65535, int(round(prop_t * 10.0))))
            p_f_int = max(0, min(65535, int(round(prop_f * 10.0))))
            p7 = struct.pack("<HHH2x", p_rpm_int, p_t_int, p_f_int)
            frames.append(cls._build_frame(base_can_id + 0x07, p7, stream_id, seq + 6, source_timestamp, eng_idx))

            # 0x108 / 0x208: DEGRADATION_VIBRATION (Bearing Wear, Ring Wear, Injector Wear, Vibration RMS)
            d_b = deg.bearing_wear if deg else 0.0
            d_r = deg.ring_wear if deg else 0.0
            d_inj = deg.injector_wear if deg else 0.0
            vib_rms = vib.vibration_rms_m_s2 if vib else 0.0
            db_int = max(0, min(255, int(round(d_b * 255.0))))
            dr_int = max(0, min(255, int(round(d_r * 255.0))))
            dinj_int = max(0, min(255, int(round(d_inj * 255.0))))
            vib_int = max(0, min(65535, int(round(vib_rms * 100.0))))
            p8 = struct.pack("<BBBHx", db_int, dr_int, dinj_int, vib_int)
            frames.append(cls._build_frame(base_can_id + 0x08, p8, stream_id, seq + 7, source_timestamp, eng_idx))

        # 2. Encode Aircraft & Environment Frames (CAN ID 0x301 and 0x302)
        stream_ac = "can0_aircraft"
        seq_ac = sequence_numbers.get(stream_ac, 0)
        ac = state.aircraft
        env = state.environment

        # 0x301: AIRCRAFT_KINEMATICS (Altitude m, Airspeed m/s, Gross Mass kg)
        alt_int = max(0, min(65535, int(round(ac.altitude_m))))
        v_int = max(0, min(65535, int(round(ac.velocity_m_s * 100.0))))
        m_int = max(0, min(65535, int(round(ac.gross_mass_kg * 10.0))))
        p_ac = struct.pack("<HHH2x", alt_int, v_int, m_int)
        frames.append(cls._build_frame(0x301, p_ac, stream_ac, seq_ac, source_timestamp, 0))

        # 0x302: ENVIRONMENT_ATMOSPHERE (Ambient Temp C, Ambient Pressure Pa, Air Density kg/m3)
        t_amb_c = env.ambient_temp_k - 273.15
        p_amb_bar = env.ambient_pressure_pa / 100000.0
        rho_air = env.air_density_kg_m3
        t_amb_int = max(0, min(65535, int(round((t_amb_c + 40.0) * 10.0))))
        p_amb_int = max(0, min(65535, int(round(p_amb_bar * 1000.0))))
        rho_int = max(0, min(65535, int(round(rho_air * 1000.0))))
        p_env = struct.pack("<HHH2x", t_amb_int, p_amb_int, rho_int)
        frames.append(cls._build_frame(0x302, p_env, stream_ac, seq_ac + 1, source_timestamp, 0))

        return frames

    @staticmethod
    def _build_frame(
        can_id: int,
        payload: bytes,
        stream_id: str,
        sequence_number: int,
        source_timestamp: float,
        engine_index: int
    ) -> EncodedCanFrame:
        sha256_hash = compute_payload_sha256(payload)
        return EncodedCanFrame(
            can_id=can_id,
            payload=payload,
            dlc=len(payload),
            stream_id=stream_id,
            sequence_number=sequence_number,
            source_timestamp=source_timestamp,
            engine_index=engine_index,
            payload_sha256=sha256_hash
        )
