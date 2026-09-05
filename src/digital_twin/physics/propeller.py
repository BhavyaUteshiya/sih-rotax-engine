"""
Phase 1F: Propeller Physics & Aerodynamic Coupling Model
SIH26054 — Digital Twin Core

Calculates the aerodynamic thrust, torque, power, and efficiency of the propeller
based on nondimensional standard formulas and advance ratio (J). 
The resulting aerodynamic torque opposes the engine rotation and will be coupled
into Phase 1E (Torque Balance) during system integration.
"""

import math
from dataclasses import dataclass

@dataclass
class PropellerInput:
    """Inputs to the Propeller Model."""
    propeller_rpm: float
    airspeed_m_s: float
    ambient_density_kg_m3: float
    propeller_diameter_m: float

@dataclass
class PropellerState:
    """Calculated output state of the Propeller Model."""
    advance_ratio: float
    thrust_coefficient: float
    torque_coefficient: float
    thrust_n: float
    aerodynamic_torque_nm: float
    absorbed_power_w: float
    efficiency: float

class PropellerModel:
    """
    Phase 1F: Mathematical model for propeller aerodynamic physics.
    """
    
    # ---------------------------------------------------------
    # Propeller Coefficient Surrogate Parameters
    # ---------------------------------------------------------
    # Reduced-order linear approximations for a typical fixed-pitch UAV propeller.
    # Static coefficients sourced from canonical project engine data
    # (ROTAX_914_ENGINE_DATA.txt, Synthetic/Calibration classification).
    # These are NOT proprietary Rotax maps.
    CT_STATIC = 0.075             # Thrust coefficient at J = 0.0. CALIBRATION (from engine data).
    CT_J_COEFF = -0.035           # Linear decay of thrust coefficient with J. CALIBRATION.
    CT_MIN = 0.0                  # Minimum thrust coefficient (no reverse thrust modeled here)
    
    CQ_STATIC = 0.0125            # Torque coefficient at J = 0.0. CALIBRATION (from engine data).
    CQ_J_COEFF = -0.008           # Linear decay of torque coefficient with J. CALIBRATION.
    CQ_MIN = 0.002                # Minimum aerodynamic drag torque coefficient. CALIBRATION.
    
    # Mathematical regularization threshold
    MIN_RPM_THRESHOLD = 0.1       # Minimum RPM below which propeller physics return static 0
    
    @classmethod
    def _calculate_thrust_coefficient(cls, advance_ratio: float) -> float:
        """
        PROP-02: Surrogate Thrust Coefficient (C_T).
        Decreases as advance ratio increases.
        """
        c_t = cls.CT_STATIC + (cls.CT_J_COEFF * advance_ratio)
        return max(cls.CT_MIN, c_t)
        
    @classmethod
    def _calculate_torque_coefficient(cls, advance_ratio: float) -> float:
        """
        PROP-03: Surrogate Torque Coefficient (C_Q).
        Decreases slightly as advance ratio increases.
        """
        c_q = cls.CQ_STATIC + (cls.CQ_J_COEFF * advance_ratio)
        return max(cls.CQ_MIN, c_q)

    @classmethod
    def calculate(cls, env: PropellerInput) -> PropellerState:
        """
        Calculates the aerodynamic properties of the propeller for a given operating point.
        """
        # Enforce physical bounds on inputs
        prop_rpm = max(0.0, env.propeller_rpm)
        v_air = max(0.0, env.airspeed_m_s)
        rho = max(0.0, env.ambient_density_kg_m3)
        diameter = max(0.001, env.propeller_diameter_m)  # Prevent div-by-zero on diameter
        
        # RPM to rev/s (Hz)
        n_prop = prop_rpm / 60.0
        
        # Zero/Near-zero RPM Handling
        if prop_rpm < cls.MIN_RPM_THRESHOLD:
            return PropellerState(
                advance_ratio=0.0,
                thrust_coefficient=cls.CT_STATIC,
                torque_coefficient=cls.CQ_STATIC,
                thrust_n=0.0,
                aerodynamic_torque_nm=0.0,
                absorbed_power_w=0.0,
                efficiency=0.0
            )
            
        # PROP-01: Advance Ratio
        # J = V / (n * D)
        j_p = v_air / (n_prop * diameter)
        
        # Calculate Nondimensional Coefficients
        c_t = cls._calculate_thrust_coefficient(j_p)
        c_q = cls._calculate_torque_coefficient(j_p)
        
        # PROP-04: Thrust (N)
        # T = C_T * rho * n^2 * D^4
        thrust = c_t * rho * (n_prop ** 2) * (diameter ** 4)
        
        # PROP-05: Aerodynamic Torque (Nm)
        # Q = C_Q * rho * n^2 * D^5
        torque = c_q * rho * (n_prop ** 2) * (diameter ** 5)
        
        # PROP-06: Absorbed Power (W)
        # P = 2 * pi * n * Q
        power = 2.0 * math.pi * n_prop * torque
        
        # PROP-07: Efficiency
        # eta = (T * V) / P
        if power > 0.0 and v_air > 0.0:
            efficiency = (thrust * v_air) / power
            # Clamp efficiency to valid physical bounds to catch surrogate extrapolation errors
            efficiency = max(0.0, min(1.0, efficiency))
        else:
            efficiency = 0.0
            
        return PropellerState(
            advance_ratio=j_p,
            thrust_coefficient=c_t,
            torque_coefficient=c_q,
            thrust_n=thrust,
            aerodynamic_torque_nm=torque,
            absorbed_power_w=power,
            efficiency=efficiency
        )
