"""
Phase 1D: Fuel Flow and Combustion Model
SIH26054 — Digital Twin Core

Calculates fuel mass flow based on mixture surrogates, evaluates fuel pressure constraints,
implements a reduced-order 0-D Wiebe combustion surrogate, and performs strict energy
accounting to partition chemical energy into indicated work, exhaust enthalpy, and heat loss.
"""

import math
from dataclasses import dataclass
from .turbo_intake import TurboIntakeModel

@dataclass
class FuelCombustionInput:
    """Inputs to the Fuel and Combustion model."""
    engine_rpm: float
    throttle_position: float
    manifold_pressure_pa: float
    manifold_temperature_k: float
    air_mass_flow_kg_s: float
    ambient_pressure_pa: float
    # Support either absolute fuel pressure or differential. If differential is non-zero, it takes precedence.
    fuel_pressure_pa: float = 0.0
    fuel_pressure_delta_pa: float = 0.0

@dataclass
class FuelCombustionState:
    """Calculated output state of the combustion model."""
    fuel_mass_flow_kg_s: float
    fuel_volume_flow_l_h: float
    air_fuel_ratio: float
    equivalence_ratio: float
    
    fuel_pressure_delta_pa: float
    fuel_pressure_status: str  # 'LOW', 'NORMAL', 'HIGH'
    
    combustion_efficiency: float
    chemical_energy_power_w: float
    heat_release_power_w: float
    indicated_power_w: float
    unreleased_power_w: float
    exhaust_sensible_power_w: float
    heat_loss_power_w: float
    
    mass_fraction_burned: float
    burn_duration_deg: float
    
    exhaust_mass_flow_kg_s: float
    exhaust_temperature_k: float
    exhaust_pressure_pa: float

class CombustionModel:
    """
    Phase 1D: Reduced-Order Physical Surrogate for the Rotax 914 Fuel and Combustion.
    """
    # ---------------------------------------------------------
    # Fuel Properties (Generic Gasoline / Aviation Fuel)
    # ---------------------------------------------------------
    AFR_STOICH = 14.7             # Stoichiometric air-to-fuel ratio
    LHV_J_KG = 43.5e6             # Lower Heating Value (43.5 MJ/kg)
    FUEL_DENSITY_KG_M3 = 720.0    # Approximate density (kg/m^3)
    
    # Fuel Pressure Constraints (Rotax Specifications)
    FUEL_PRESS_MIN_PA = 15000.0   # 0.15 bar
    FUEL_PRESS_NOM_PA = 25000.0   # 0.25 bar
    FUEL_PRESS_MAX_PA = 35000.0   # 0.35 bar
    
    # ---------------------------------------------------------
    # Mixture / Equivalence Ratio Surrogate (Calibration parameters)
    # ---------------------------------------------------------
    PHI_BASE = 0.95               # Base equivalence ratio (slightly lean/stoich for cruise)
    PHI_MIN = 0.80                # Leanest allowed
    PHI_MAX = 1.30                # Richest allowed (takeoff/WOT)
    P_MAP_NOMINAL_PA = 100000.0   # Normalization factor for load
    RPM_NOMINAL = 5800.0          # Normalization factor for speed
    
    # ---------------------------------------------------------
    # Combustion & Energy Parameters (Calibration parameters)
    # ---------------------------------------------------------
    ETA_COMB_MAX = 0.98           # Max combustion efficiency
    ETA_INDICATED = 0.35          # Prototype indicated thermal efficiency (relative to released energy)
    ETA_EXHAUST_PARTITION = 0.60  # Fraction of remaining released energy going to exhaust
    
    # Wiebe function parameters
    WIEBE_A = 5.0                 # Completeness parameter
    WIEBE_M = 2.0                 # Shape factor
    THETA_0 = -15.0               # Start of combustion (deg aTDC) - assumed static surrogate
    BURN_DURATION_NOMINAL = 50.0  # Crank degrees
    
    # ---------------------------------------------------------
    # Exhaust Parameters
    # ---------------------------------------------------------
    K_EXHAUST = 1500000.0         # Exhaust resistance coefficient: dP = K * m_dot^2

    @classmethod
    def _calculate_equivalence_ratio(cls, rpm: float, p_map: float) -> float:
        """
        FUEL-01: Equivalence ratio surrogate based on engine speed and load (manifold pressure).
        Provides a smooth, bounded mixture response (enrichment at high load/speed).
        """
        load_factor = p_map / cls.P_MAP_NOMINAL_PA
        rpm_factor = rpm / cls.RPM_NOMINAL
        
        # Simple surrogate enrichment logic
        load_enrichment = max(0.0, 0.15 * (load_factor - 0.8))  # Enriches at high load
        rpm_enrichment = 0.05 * (rpm_factor - 0.5)              # Minor speed sensitivity
        
        phi_target = cls.PHI_BASE + load_enrichment + rpm_enrichment
        return max(cls.PHI_MIN, min(cls.PHI_MAX, phi_target))

    @classmethod
    def calculate(cls, env: FuelCombustionInput) -> FuelCombustionState:
        """
        Advances the combustion model based on current airflow and engine state.
        """
        # 1. Fuel Pressure Evaluation (FUEL-02)
        if env.fuel_pressure_delta_pa != 0.0:
            dp_fuel = env.fuel_pressure_delta_pa
        else:
            dp_fuel = env.fuel_pressure_pa - env.manifold_pressure_pa
            
        if dp_fuel < cls.FUEL_PRESS_MIN_PA:
            fp_status = 'LOW'
        elif dp_fuel > cls.FUEL_PRESS_MAX_PA:
            fp_status = 'HIGH'
        else:
            fp_status = 'NORMAL'

        # Protect against non-physical inputs
        if env.air_mass_flow_kg_s < 1e-6 or env.engine_rpm < 1.0:
            return FuelCombustionState(
                fuel_mass_flow_kg_s=0.0,
                fuel_volume_flow_l_h=0.0,
                air_fuel_ratio=float('inf'),
                equivalence_ratio=0.0,
                fuel_pressure_delta_pa=dp_fuel,
                fuel_pressure_status=fp_status,
                combustion_efficiency=0.0,
                chemical_energy_power_w=0.0,
                heat_release_power_w=0.0,
                indicated_power_w=0.0,
                unreleased_power_w=0.0,
                exhaust_sensible_power_w=0.0,
                heat_loss_power_w=0.0,
                mass_fraction_burned=0.0,
                burn_duration_deg=0.0,
                exhaust_mass_flow_kg_s=0.0,
                exhaust_temperature_k=env.manifold_temperature_k,
                exhaust_pressure_pa=env.ambient_pressure_pa
            )

        # 2. Fuel Flow (FUEL-03, FUEL-04)
        phi = cls._calculate_equivalence_ratio(env.engine_rpm, env.manifold_pressure_pa)
        afr = cls.AFR_STOICH / phi
        m_dot_fuel = env.air_mass_flow_kg_s / afr
        
        fuel_vol_l_s = m_dot_fuel / cls.FUEL_DENSITY_KG_M3
        fuel_vol_l_h = fuel_vol_l_s * 3600.0 * 1000.0
        
        # 3. Energy Accounting (ENE-01, ENE-02, ENE-03)
        p_fuel = m_dot_fuel * cls.LHV_J_KG
        
        # Mixture efficiency penalty (lean misfire or extreme rich)
        if phi < cls.PHI_MIN or phi > cls.PHI_MAX + 0.2:
            eta_comb = cls.ETA_COMB_MAX * 0.5
        else:
            eta_comb = cls.ETA_COMB_MAX
            
        p_release = p_fuel * eta_comb
        p_unreleased = p_fuel - p_release
        
        p_indicated = p_release * cls.ETA_INDICATED
        remaining_release = max(0.0, p_release - p_indicated)
        
        p_exhaust = remaining_release * cls.ETA_EXHAUST_PARTITION
        p_heat_loss = remaining_release - p_exhaust
        
        # 4. Combustion Surrogate (Wiebe) (COMB-01)
        # We evaluate burn fraction at end of combustion (theta = theta_0 + duration)
        # This is a constant 1.0 for typical values, but provides the formula structure.
        theta = cls.THETA_0 + cls.BURN_DURATION_NOMINAL
        if theta > cls.THETA_0:
            arg = (theta - cls.THETA_0) / cls.BURN_DURATION_NOMINAL
            # Ensure argument is strictly positive to avoid fractional power issues on negative numbers
            arg = max(0.0, arg)
            xb = 1.0 - math.exp(-cls.WIEBE_A * math.pow(arg, cls.WIEBE_M + 1.0))
        else:
            xb = 0.0

        # 5. Exhaust State (EXH-01, EXH-02, EXH-03)
        m_dot_exhaust = env.air_mass_flow_kg_s + m_dot_fuel
        
        if m_dot_exhaust > 1e-6:
            # T_exh = T_charge + P_exh / (m_dot * Cp)
            dt_exhaust = p_exhaust / (m_dot_exhaust * TurboIntakeModel.CP_EXH)
            t_exhaust = env.manifold_temperature_k + dt_exhaust
        else:
            t_exhaust = env.manifold_temperature_k
            
        dp_exhaust = cls.K_EXHAUST * (m_dot_exhaust ** 2)
        p_exhaust_pa = env.ambient_pressure_pa + dp_exhaust
        
        return FuelCombustionState(
            fuel_mass_flow_kg_s=m_dot_fuel,
            fuel_volume_flow_l_h=fuel_vol_l_h,
            air_fuel_ratio=afr,
            equivalence_ratio=phi,
            fuel_pressure_delta_pa=dp_fuel,
            fuel_pressure_status=fp_status,
            combustion_efficiency=eta_comb,
            chemical_energy_power_w=p_fuel,
            heat_release_power_w=p_release,
            indicated_power_w=p_indicated,
            unreleased_power_w=p_unreleased,
            exhaust_sensible_power_w=p_exhaust,
            heat_loss_power_w=p_heat_loss,
            mass_fraction_burned=xb,
            burn_duration_deg=cls.BURN_DURATION_NOMINAL,
            exhaust_mass_flow_kg_s=m_dot_exhaust,
            exhaust_temperature_k=t_exhaust,
            exhaust_pressure_pa=p_exhaust_pa
        )
