"""
Phase 1C: Airflow / Engine Breathing Model
SIH26054 — Digital Twin Core

Implements a reduced-order mean-value engine model for the Rotax 914.
This calculates actual engine mass flow using a speed-density formulation
and a compressible restriction (throttle/carburetor), replacing the 
temporary static placeholder in Phase 1B.
"""

import math
from dataclasses import dataclass
from .atmosphere import AtmosphericState, R_D

@dataclass
class AirflowInput:
    """Physical inputs to the engine breathing model."""
    manifold_pressure_pa: float      # Upstream of throttle (Airbox / Turbo output)
    manifold_temperature_k: float    # Upstream of throttle (Airbox / Turbo output)
    engine_rpm: float                # Engine rotational speed
    throttle_position: float         # 0.0 (closed) to 1.0 (WOT)

@dataclass
class AirflowState:
    """Calculated output state of the engine breathing model."""
    air_mass_flow_kg_s: float
    charge_density_kg_m3: float
    volumetric_efficiency: float
    effective_throttle_area_m2: float
    intake_restriction_mass_flow_kg_s: float
    cylinder_filling_mass_flow_kg_s: float
    charge_pressure_pa: float
    charge_temperature_k: float

class AirflowModel:
    """
    Calculates engine airflow based on upstream conditions and engine state.
    """
    
    # ---------------------------------------------------------
    # Physical Constants & Geometry (Rotax 914 / EASA E.122)
    # ---------------------------------------------------------
    N_CYL = 4
    BORE_M = 79.5e-3
    STROKE_M = 61.0e-3
    
    # AIR-01: Cylinder swept volume
    # AIR-02: Total engine displacement (~1.211 Liters)
    V_D = (math.pi / 4.0) * (BORE_M ** 2) * STROKE_M * N_CYL
    
    R_AIR = R_D       # J/(kg K) Imported from Phase 1A for consistency
    GAMMA = 1.4       # Heat capacity ratio for air
    
    # ---------------------------------------------------------
    # Throttle / Carburetor Surrogate (Estimated/Calibration)
    # ---------------------------------------------------------
    C_D = 0.8                   # Discharge coefficient
    A_MAX = 0.002               # Max effective area (m^2)
    A_IDLE = 0.0001             # Idle/Closed effective area (m^2)
    
    # ---------------------------------------------------------
    # Volumetric Efficiency Surrogate (Estimated/Calibration)
    # ---------------------------------------------------------
    ETA_V_BASE = 0.75
    ETA_V_MIN = 0.1
    ETA_V_MAX = 0.95
    RPM_OPT = 5800.0            # Takeoff RPM peak
    C_RPM = 0.15                # Parabolic RPM sensitivity
    C_P = 0.05                  # Pressure sensitivity
    P_REF = 101325.0            # Reference pressure for scaling
    
    @classmethod
    def _calculate_eta_v(cls, rpm: float, p_charge: float) -> float:
        """
        AIR-09: Volumetric efficiency surrogate equation.
        A smooth, bounded function depending on RPM and charge pressure.
        """
        # Normalized RPM distance from optimum
        rpm_factor = 1.0 - ((rpm - cls.RPM_OPT) / cls.RPM_OPT) ** 2
        rpm_shape = cls.C_RPM * rpm_factor
        
        # Pressure sensitivity (better filling at higher charge pressure)
        pressure_shape = cls.C_P * (p_charge / cls.P_REF)
        
        eta_v = cls.ETA_V_BASE + rpm_shape + pressure_shape
        
        # Enforce physical bounds
        return max(cls.ETA_V_MIN, min(cls.ETA_V_MAX, eta_v))

    @classmethod
    def _throttle_effective_area(cls, throttle_position: float) -> float:
        """
        AIR-06: Throttle effective-area relationship.
        Quadratic surrogate to model nonlinear butterfly valve area opening.
        """
        return cls.A_IDLE + (throttle_position ** 2) * (cls.A_MAX - cls.A_IDLE)

    @classmethod
    def _throttle_mass_flow(cls, p_up: float, p_down: float, t_up: float, a_eff: float) -> float:
        """
        AIR-07: Compressible restriction mass-flow relation.
        AIR-08: Choked-flow criterion.
        Models air flowing through the carburetor restriction.
        """
        # Ensure PR doesn't exceed 1.0 physically (no reverse flow modeled here)
        pr = max(1e-6, min(p_down / p_up, 1.0))
        
        choked_pr = (2.0 / (cls.GAMMA + 1.0)) ** (cls.GAMMA / (cls.GAMMA - 1.0))
        
        if pr <= choked_pr:
            # Choked flow
            phi = math.sqrt(cls.GAMMA * (2.0 / (cls.GAMMA + 1.0)) ** ((cls.GAMMA + 1.0) / (cls.GAMMA - 1.0)))
        else:
            # Unchoked flow
            base = max(0.0, pr ** (2.0 / cls.GAMMA) - pr ** ((cls.GAMMA + 1.0) / cls.GAMMA))
            phi = math.sqrt((2.0 * cls.GAMMA / (cls.GAMMA - 1.0)) * base)
            
        return cls.C_D * a_eff * (p_up / math.sqrt(cls.R_AIR * t_up)) * phi

    @classmethod
    def _cylinder_mass_flow(cls, p_charge: float, t_charge: float, rpm: float, eta_v: float) -> float:
        """
        AIR-03: Charge-air density.
        AIR-04: Speed-density cylinder filling / engine airflow.
        AIR-05: RPM conversion.
        """
        rho_charge = p_charge / (cls.R_AIR * t_charge)
        # N = RPM / 60. For 4-stroke, intake strokes per second = N / 2 = RPM / 120.
        return eta_v * rho_charge * cls.V_D * (rpm / 120.0)

    @classmethod
    def calculate(cls, env: AirflowInput) -> AirflowState:
        """
        Advances the engine breathing model based on upstream conditions and engine state.
        Solves for the equilibrium downstream charge pressure where 
        throttle flow == cylinder filling.
        """
        # 1. Input Validation
        if env.engine_rpm < 0.0:
            raise ValueError(f"RPM cannot be negative. Got {env.engine_rpm}")
        if not (0.0 <= env.throttle_position <= 1.0):
            raise ValueError(f"Throttle must be between 0.0 and 1.0. Got {env.throttle_position}")
        if env.manifold_pressure_pa <= 0.0:
            raise ValueError(f"Manifold pressure must be > 0. Got {env.manifold_pressure_pa}")
        if env.manifold_temperature_k <= 0.0:
            raise ValueError(f"Manifold temperature must be > 0. Got {env.manifold_temperature_k}")

        # Upstream conditions (Airbox/Turbo output)
        p_airbox = env.manifold_pressure_pa
        t_airbox = env.manifold_temperature_k
        
        # Effective throttle area
        a_eff = cls._throttle_effective_area(env.throttle_position)
        
        # 2. Downstream Pressure Numerical Solve (AIR-10)
        # Find p_charge such that m_throttle == m_cyl using Bisection
        # Bounds for downstream pressure: (small offset) to (upstream pressure)
        p_low = 10.0
        p_high = p_airbox
        
        # Assuming no significant temperature drop across throttle for this surrogate
        t_charge = t_airbox
        
        tol = 0.5  # Pa tolerance
        max_iters = 50
        
        # Handle zero RPM edge case (engine stopped, no cylinder flow)
        if env.engine_rpm == 0.0:
            p_charge = p_airbox
            m_dot_final = 0.0
            eta_v_final = cls._calculate_eta_v(env.engine_rpm, p_charge)
            m_throttle_final = 0.0
        else:
            for _ in range(max_iters):
                p_mid = 0.5 * (p_low + p_high)
                
                eta_v_mid = cls._calculate_eta_v(env.engine_rpm, p_mid)
                
                m_throttle = cls._throttle_mass_flow(p_airbox, p_mid, t_airbox, a_eff)
                m_cyl = cls._cylinder_mass_flow(p_mid, t_charge, env.engine_rpm, eta_v_mid)
                
                # If throttle flow capacity is greater than cylinder demand, 
                # the manifold pressure will rise (moving towards p_airbox).
                if m_throttle > m_cyl:
                    p_low = p_mid
                else:
                    p_high = p_mid
                    
                if (p_high - p_low) < tol:
                    break
                    
            p_charge = 0.5 * (p_low + p_high)
            
            # Final evaluation at converged state
            eta_v_final = cls._calculate_eta_v(env.engine_rpm, p_charge)
            m_dot_final = cls._cylinder_mass_flow(p_charge, t_charge, env.engine_rpm, eta_v_final)
            m_throttle_final = cls._throttle_mass_flow(p_airbox, p_charge, t_airbox, a_eff)
            
        rho_charge = p_charge / (cls.R_AIR * t_charge)
        
        return AirflowState(
            air_mass_flow_kg_s=m_dot_final,
            charge_density_kg_m3=rho_charge,
            volumetric_efficiency=eta_v_final,
            effective_throttle_area_m2=a_eff,
            intake_restriction_mass_flow_kg_s=m_throttle_final,
            cylinder_filling_mass_flow_kg_s=m_dot_final,
            charge_pressure_pa=p_charge,
            charge_temperature_k=t_charge
        )
