"""
Phase 1G: Engine Thermal Physics Model
SIH26054 — Digital Twin Core

Implements a reduced-order two-node lumped thermal network for the Rotax 914 engine:
  Node 1: Cylinder Head Temperature (CHT) — engine metal thermal mass
  Node 2: Oil Temperature — engine oil thermal mass

Energy input is the heat-loss residual from Phase 1D combustion (heat_loss_power_w).
This module does NOT re-derive combustion energy. Phase 1D owns all combustion accounting.
Phase 1G owns only the thermal-state evolution and heat rejection to the environment.

The model is a reduced-order dynamic thermal network intended for Digital Twin prototyping.
It does NOT represent detailed cylinder geometry, 3D heat conduction, CFD, detailed cooling
fins, detailed oil galleries, oil pump hydraulics, cylinder-by-cylinder thermal maps,
detailed combustion wall heat-transfer correlations, radiation geometry, or detailed
material temperature fields.
"""

import math
from dataclasses import dataclass


@dataclass
class ThermalInput:
    """Inputs to the Thermal Model."""
    cht_temperature_k: float           # Current CHT state (K)
    oil_temperature_k: float           # Current oil temperature state (K)
    heat_loss_power_w: float           # From Phase 1D combustion output (W)
    ambient_temperature_k: float       # From Phase 1A atmosphere (K)
    ambient_density_kg_m3: float       # From Phase 1A atmosphere (kg/m^3)
    airspeed_m_s: float                # Aircraft/mission airspeed (m/s)
    engine_rpm: float                  # From Phase 1E dynamics (RPM)
    timestep_s: float                  # Integration timestep (s)


@dataclass
class ThermalState:
    """Calculated output state of the Thermal Model."""
    cht_temperature_k: float           # Updated CHT (K)
    oil_temperature_k: float           # Updated oil temperature (K)
    cht_temperature_c: float           # Updated CHT (°C)
    oil_temperature_c: float           # Updated oil temperature (°C)
    cht_heat_input_w: float            # Q_CHT_in: heat assigned to CHT node (W)
    heat_cht_to_oil_w: float           # Q_CHT_oil: heat flowing CHT → oil (W)
    cht_cooling_w: float               # Q_CHT_cooling: heat rejected CHT → ambient (W)
    oil_cooling_w: float               # Q_oil_cooling: heat rejected oil → ambient (W)
    dcht_dt_k_s: float                 # CHT rate of change (K/s)
    doil_dt_k_s: float                 # Oil rate of change (K/s)


class ThermalModel:
    """
    Phase 1G: Two-node lumped thermal network for engine thermal dynamics.

    Energy path:
        1D heat_loss_power_w * F_CHT → CHT node
        CHT node → (1/R_CHT_OIL) → Oil node
        CHT node → G_CHT_cool → ambient
        Oil node → G_oil_cool → ambient
    """

    # ---------------------------------------------------------
    # Thermal Mass Parameters (CALIBRATION / ENGINEERING ESTIMATE)
    # ---------------------------------------------------------
    M_CHT = 15.0                # Lumped cylinder-head metal mass (kg). CALIBRATION.
    CP_CHT = 900.0              # Aluminum alloy specific heat (J/(kg·K)). CALIBRATION.

    M_OIL = 2.5                 # Oil mass (kg). From engine data: ~3.0 L ≈ 2.5 kg. CALIBRATION.
    CP_OIL = 2000.0             # Engine oil specific heat (J/(kg·K)). CALIBRATION.

    # Derived thermal capacities (J/K) — THERM-01
    C_CHT = M_CHT * CP_CHT     # = 13500 J/K
    C_OIL = M_OIL * CP_OIL     # = 5000 J/K

    # ---------------------------------------------------------
    # Internal Heat Transfer (CALIBRATION)
    # ---------------------------------------------------------
    R_CHT_OIL = 0.01            # Thermal resistance CHT→oil (K/W). CALIBRATION.

    # ---------------------------------------------------------
    # Cooling Conductance Parameters (CALIBRATION)
    # ---------------------------------------------------------
    G_CHT_BASE = 250.0          # Baseline CHT cooling conductance at reference (W/K). CALIBRATION.
    G_OIL_BASE = 35.0           # Baseline oil cooler conductance at reference (W/K). CALIBRATION.
    G_MIN = 5.0                 # Minimum residual natural convection (W/K). CALIBRATION.

    RHO_REF = 1.225             # Sea-level ISA reference density (kg/m³).
    V_REF = 40.0                # Reference cruise airspeed (m/s).
    COOLING_EXPONENT = 0.6      # Convective cooling scaling exponent. CALIBRATION.

    # ---------------------------------------------------------
    # Energy Partition (CALIBRATION)
    # ---------------------------------------------------------
    F_CHT = 0.35                # Fraction of 1D heat loss assigned to CHT node. CALIBRATION.

    # ---------------------------------------------------------
    # Auxiliary RPM-dependent cooling (CALIBRATION)
    # ---------------------------------------------------------
    RPM_COOL_COEFF = 0.002      # Oil pump circulation cooling contribution (W/(K·RPM)). CALIBRATION.

    @classmethod
    def _calculate_cooling_conductance(cls, base_conductance: float,
                                        density: float, airspeed: float) -> float:
        """
        THERM-07: Cooling conductance surrogate.
        G = max(G_min, G_base * (rho * V / (rho_ref * V_ref))^a)

        Increases with airspeed and density. Uses minimum baseline for
        natural convection when airspeed is near zero.
        """
        rho = max(0.0, density)
        v = max(0.0, airspeed)

        rho_v_product = rho * v
        ref_product = cls.RHO_REF * cls.V_REF

        if ref_product <= 0.0:
            return max(cls.G_MIN, base_conductance)

        ratio = rho_v_product / ref_product

        # Protect against negative ratio (impossible but defensive)
        if ratio <= 0.0:
            return cls.G_MIN

        g = base_conductance * math.pow(ratio, cls.COOLING_EXPONENT)
        return max(cls.G_MIN, g)

    @classmethod
    def calculate(cls, env: ThermalInput) -> ThermalState:
        """
        Advances the thermal state by one timestep using explicit Euler integration.
        """
        # --- Input validation ---
        dt = max(0.0, env.timestep_s)

        t_cht = env.cht_temperature_k
        t_oil = env.oil_temperature_k
        t_amb = env.ambient_temperature_k
        q_heat_loss = max(0.0, env.heat_loss_power_w)
        rpm = max(0.0, env.engine_rpm)

        # Validate physical temperatures (must be > 0 K)
        if t_cht <= 0.0 or t_oil <= 0.0 or t_amb <= 0.0:
            raise ValueError(
                f"Non-physical temperature detected: CHT={t_cht} K, "
                f"Oil={t_oil} K, Ambient={t_amb} K. All must be > 0 K."
            )

        # --- THERM-01: Thermal capacities (class-level constants) ---
        # C_CHT and C_OIL are pre-computed as class attributes.

        # --- Energy input to CHT node ---
        # Q_CHT_in = heat_loss_power_w * F_CHT
        q_cht_in = q_heat_loss * cls.F_CHT

        # --- THERM-03: CHT-to-oil heat transfer ---
        # Q_CHT_oil = (T_CHT - T_oil) / R_CHT_OIL
        q_cht_to_oil = (t_cht - t_oil) / cls.R_CHT_OIL

        # --- THERM-07: Cooling conductances ---
        g_cht_cool = cls._calculate_cooling_conductance(
            cls.G_CHT_BASE, env.ambient_density_kg_m3, env.airspeed_m_s
        )
        g_oil_cool_base = cls._calculate_cooling_conductance(
            cls.G_OIL_BASE, env.ambient_density_kg_m3, env.airspeed_m_s
        )
        # Add auxiliary RPM-proportional oil pump contribution
        g_oil_cool = g_oil_cool_base + cls.RPM_COOL_COEFF * rpm

        # --- THERM-04: CHT cooling to ambient ---
        q_cht_cooling = g_cht_cool * (t_cht - t_amb)

        # --- THERM-06: Oil cooling to ambient ---
        q_oil_cooling = g_oil_cool * (t_oil - t_amb)

        # --- THERM-02: CHT energy balance ---
        # C_CHT * dT_CHT/dt = Q_CHT_in - Q_CHT_oil - Q_CHT_cooling
        dcht_dt = (q_cht_in - q_cht_to_oil - q_cht_cooling) / cls.C_CHT

        # --- THERM-05: Oil energy balance ---
        # C_oil * dT_oil/dt = Q_CHT_oil - Q_oil_cooling
        doil_dt = (q_cht_to_oil - q_oil_cooling) / cls.C_OIL

        # --- THERM-08: Explicit Euler time integration ---
        t_cht_next = t_cht + dcht_dt * dt
        t_oil_next = t_oil + doil_dt * dt

        # Physical floor: temperatures cannot go below 0 K.
        # This is a numerical protection, not a physical clipping.
        # If this triggers, the timestep is likely too large.
        t_cht_next = max(1.0, t_cht_next)
        t_oil_next = max(1.0, t_oil_next)

        return ThermalState(
            cht_temperature_k=t_cht_next,
            oil_temperature_k=t_oil_next,
            cht_temperature_c=t_cht_next - 273.15,
            oil_temperature_c=t_oil_next - 273.15,
            cht_heat_input_w=q_cht_in,
            heat_cht_to_oil_w=q_cht_to_oil,
            cht_cooling_w=q_cht_cooling,
            oil_cooling_w=q_oil_cooling,
            dcht_dt_k_s=dcht_dt,
            doil_dt_k_s=doil_dt,
        )
