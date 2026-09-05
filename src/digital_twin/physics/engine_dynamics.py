"""
Phase 1E: Engine Torque & RPM Dynamics Model
SIH26054 — Digital Twin Core

Converts indicated power from Phase 1D into rotational dynamics, enforcing strict torque balance 
(indicated torque, friction torque, starter torque, propeller load torque) and performing numerical
time integration to yield the emergent engine RPM and propeller RPM.
"""

import math
from dataclasses import dataclass

@dataclass
class EngineDynamicsInput:
    """Inputs to the Engine Dynamics model."""
    engine_angular_speed_rad_s: float
    indicated_power_w: float
    starter_engaged: bool
    timestep_s: float
    propeller_load_torque_nm: float

@dataclass
class EngineDynamicsState:
    """Calculated output state of the rotational dynamics model."""
    engine_angular_speed_rad_s: float
    engine_rpm: float
    indicated_torque_nm: float
    friction_torque_nm: float
    starter_torque_nm: float
    propeller_load_torque_nm: float
    net_torque_nm: float
    angular_acceleration_rad_s2: float
    shaft_power_w: float
    propeller_rpm: float

class EngineDynamicsModel:
    """
    Phase 1E: Mathematical model for Engine Torque Balance and Rotational Dynamics.
    """
    # ---------------------------------------------------------
    # Engine Structural Parameters
    # ---------------------------------------------------------
    J_ENGINE = 0.05               # Estimated engine rotational inertia (kg m^2). CALIBRATION.
    J_PROP = 0.59                 # Estimated propeller rotational inertia (kg m^2). CALIBRATION.
    
    # Convention: propeller speed / engine speed. Source verification is tracked
    # in the parameter record; do not read the numeric value as certification.
    GEARBOX_RATIO = 0.41176
    GEARBOX_EFFICIENCY = 0.98     # Estimated gearbox mechanical efficiency. CALIBRATION.
    
    # Equivalent inertia at the engine shaft: J_eq = J_engine + J_prop * (r_g)^2
    # Both inertia terms are prototype calibration values.
    J_EQ = J_ENGINE + J_PROP * (GEARBOX_RATIO ** 2)
    
    # Starter parameters
    T_STARTER_NM = 50.0           # Nominal torque provided by the electric starter (Nm). CALIBRATION.
    
    # ---------------------------------------------------------
    # Friction Surrogate Model: T_f = C0 + C1*omega + C2*omega^2
    # ---------------------------------------------------------
    # CALIBRATION paramaters to yield reasonable idle friction.
    FRICTION_C0 = 8.0             # Static/boundary friction component (Nm)
    FRICTION_C1 = 0.02            # Viscous friction coefficient (Nm / (rad/s))
    FRICTION_C2 = 0.00001         # Aerodynamic/pumping friction coefficient (Nm / (rad/s)^2)
    


    @classmethod
    def _calculate_friction_torque(cls, omega: float) -> float:
        """
        FRIC-01: Smooth, bounded reduced-order mechanical loss model.
        Returns friction torque in Nm. Non-negative.
        """
        w = max(0.0, omega)
        t_fric = cls.FRICTION_C0 + (cls.FRICTION_C1 * w) + (cls.FRICTION_C2 * w * w)
        return t_fric

    @classmethod
    def calculate(cls, env: EngineDynamicsInput) -> EngineDynamicsState:
        """
        Advances the engine rotational dynamics by one timestep based on torque balance.
        """
        # Ensure non-negative inputs
        omega_curr = max(0.0, env.engine_angular_speed_rad_s)
        dt = max(0.0, env.timestep_s)
        
        # 1. Gearbox Speed Conversion (GEAR-01, DYN-01)
        omega_prop = omega_curr * cls.GEARBOX_RATIO
        
        # 2. Propeller Torque Coupling (GEAR-02)
        # Convert aerodynamic propeller torque (from 1F) to engine-side load torque
        if omega_curr > 0.0:
            # Power balance: P_prop = P_eng_load * eta_gear
            # T_prop * w_prop = T_load_eng * w_eng * eta_gear
            # T_load_eng = T_prop * (w_prop / w_eng) / eta_gear
            t_load_eng = max(0.0, env.propeller_load_torque_nm) * (cls.GEARBOX_RATIO / cls.GEARBOX_EFFICIENCY)
        else:
            t_load_eng = 0.0

        # 3. Indicated Torque (DYN-02)
        # Numerical protection at zero / near-zero RPM to avoid division by zero.
        if omega_curr < 1.0:
            t_indicated = 0.0
        else:
            t_indicated = max(0.0, env.indicated_power_w) / omega_curr
            
        # 4. Friction and Starter Torque (FRIC-01, START-01)
        t_friction = cls._calculate_friction_torque(omega_curr)
        
        if env.starter_engaged:
            t_starter = cls.T_STARTER_NM
        else:
            t_starter = 0.0
            
        # 5. Static Friction Handling at Zero RPM
        # If the engine is completely stopped, friction acts as a static holding torque.
        # It perfectly opposes any driving torque (up to its limit) to keep the engine from moving,
        # but cannot itself accelerate the engine backwards.
        driving_torque = t_indicated + t_starter - t_load_eng
        if omega_curr < 1e-3 and driving_torque <= t_friction:
            # The driving forces aren't strong enough to overcome static friction break-away.
            t_net = 0.0
            t_friction = max(0.0, driving_torque)  # Friction exactly matches driving torque to hold it at 0
        else:
            # 6. Dynamic Torque Balance (DYN-03)
            t_net = t_indicated + t_starter - t_friction - t_load_eng
            
        # 7. Angular Acceleration and Time Integration (DYN-04, DYN-05)
        alpha = t_net / cls.J_EQ
        omega_next = omega_curr + (alpha * dt)
        
        # Prevent reverse rotation physics
        if omega_next < 0.0:
            omega_next = 0.0
            t_net = 0.0  # Mathematically, the remaining energy was dissipated by friction during the step
            alpha = (omega_next - omega_curr) / dt if dt > 0 else 0.0

        # 8. Shaft Power Output (Derived from the resulting net-mechanical components, excluding prop load)
        shaft_power_w = (t_indicated + t_starter - t_friction) * omega_next
        
        # 9. RPM Conversions
        engine_rpm = omega_next * 60.0 / (2.0 * math.pi)
        prop_rpm = engine_rpm * cls.GEARBOX_RATIO

        return EngineDynamicsState(
            engine_angular_speed_rad_s=omega_next,
            engine_rpm=engine_rpm,
            indicated_torque_nm=t_indicated,
            friction_torque_nm=t_friction,
            starter_torque_nm=t_starter,
            propeller_load_torque_nm=t_load_eng,
            net_torque_nm=t_net,
            angular_acceleration_rad_s2=alpha,
            shaft_power_w=max(0.0, shaft_power_w),
            propeller_rpm=prop_rpm
        )
