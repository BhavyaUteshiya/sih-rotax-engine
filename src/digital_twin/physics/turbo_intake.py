import math
from dataclasses import dataclass
from .atmosphere import AtmosphericState, R_D

@dataclass
class ExhaustState:
    """Mock state provided by combustion/exhaust layer (Phase 1C/later)."""
    pressure_pa: float
    temperature_k: float
    mass_flow_kg_s: float

@dataclass
class TurboState:
    """The dynamic state of the Turbocharger and Intake Manifold."""
    turbo_speed_rad_s: float
    manifold_pressure_pa: float
    manifold_temperature_k: float
    wastegate_position: float  # 0.0 (closed) to 1.0 (open)
    
    # PID Integral state for the TCU surrogate
    tcu_error_integral: float

class TurboIntakeModel:
    """
    Phase 1B: Reduced-Order Physical Surrogate for the Rotax 914 Turbocharger.
    Models the causal chain: Exhaust -> Turbine -> Shaft -> Compressor -> Manifold.
    """
    
    # Physical Constants
    GAMMA_AIR = 1.4
    GAMMA_EXH = 1.33
    CP_AIR = 1005.0   # J/(kg*K)
    CP_EXH = 1150.0   # J/(kg*K)
    R_AIR = R_D       # J/(kg*K) Imported from Phase 1A for consistency
    
    # Calibration / Surrogate Parameters (Estimated)
    J_TURBO = 0.0001        # Turbo rotational inertia (kg.m^2)
    V_MAP = 0.005           # Intake manifold / airbox volume (m^3)
    ETA_COMPRESSOR = 0.70   # Isentropic compressor efficiency
    ETA_TURBINE = 0.65      # Isentropic turbine efficiency
    
    # Compressor Surrogate Map Coefficients
    # PR_max(w) = 1 + K_PR * w^2
    K_PR = 6.67e-9
    # m_dot_c = K_FLOW * w * max(0, PR_max - PR_actual)
    K_FLOW = 6.67e-6
    
    # TCU (Wastegate Controller) PI Gains
    KP_TCU = 0.0001
    KI_TCU = 0.0005
    
    # Friction/Loss coefficient for the turbo shaft
    K_LOSS = 1.0e-5
    
    # Minimum turbo speed for torque calculation (prevents division by zero)
    STARTUP_SPEED_REGULARIZATION_RAD_S = 10.0
    
    @classmethod
    def step(cls, 
             dt: float,
             atm: AtmosphericState,
             exh: ExhaustState,
             engine_mass_flow_kg_s: float,
             target_map_pa: float,
             current_state: TurboState) -> TurboState:
        """
        Advances the turbo and manifold physics by one timestep `dt`.
        """
        if cls.ETA_COMPRESSOR <= 0.0 or cls.ETA_COMPRESSOR > 1.0:
            raise ValueError(f"Compressor efficiency must be between 0 and 1, got {cls.ETA_COMPRESSOR}")
            
        if cls.ETA_TURBINE <= 0.0 or cls.ETA_TURBINE > 1.0:
            raise ValueError(f"Turbine efficiency must be between 0 and 1, got {cls.ETA_TURBINE}")
        
        # 1. TCU / Wastegate Surrogate (Controller)
        # Calculates error between Target MAP and Actual MAP
        error = target_map_pa - current_state.manifold_pressure_pa
        
        # We integrate the error (clamping to prevent integral windup)
        new_integral = current_state.tcu_error_integral + (error * dt)
        
        # Anti-windup bounds: Allows integral to go negative to unwind overshoot, 
        # but bounded to +/- the maximum useful control contribution (1.0 / Ki).
        integral_limit = 1.0 / cls.KI_TCU
        new_integral = max(-integral_limit, min(new_integral, integral_limit))
        
        # PI Control law (Negative because closing wastegate increases MAP)
        # 0.0 = fully closed (max boost), 1.0 = fully open (min boost)
        wg_command = 1.0 - (cls.KP_TCU * error + cls.KI_TCU * new_integral)
        wg_pos = max(0.0, min(wg_command, 1.0))
        
        # 2. Turbine Physics
        # Wastegate diverts a fraction of exhaust flow around the turbine
        turbine_mass_flow = exh.mass_flow_kg_s * (1.0 - wg_pos)
        
        # Turbine pressure ratio (Inlet / Outlet). Assume Outlet ~ Atmospheric.
        # Clamp PR >= 1.0 to prevent nonphysical roots.
        pr_turbine = max(1.0, exh.pressure_pa / atm.pressure_pa)
        
        # Turbine power (Isentropic expansion)
        temp_drop_factor = 1.0 - math.pow(1.0 / pr_turbine, (cls.GAMMA_EXH - 1.0) / cls.GAMMA_EXH)
        power_turbine = turbine_mass_flow * cls.CP_EXH * exh.temperature_k * cls.ETA_TURBINE * temp_drop_factor
        
        # 3. Compressor Physics (Surrogate Model)
        pr_actual = max(1.0, current_state.manifold_pressure_pa / atm.pressure_pa)
        
        # Calculate maximum pressure ratio for current turbo speed
        pr_max = 1.0 + cls.K_PR * (current_state.turbo_speed_rad_s ** 2)
        
        # Calculate compressor mass flow using the surrogate mapping
        if pr_max > pr_actual and current_state.turbo_speed_rad_s > 0:
            mass_flow_compressor = cls.K_FLOW * current_state.turbo_speed_rad_s * (pr_max - pr_actual)
        else:
            mass_flow_compressor = 0.0
            
        # Isentropic compressor temperature rise
        temp_rise_factor = math.pow(pr_actual, (cls.GAMMA_AIR - 1.0) / cls.GAMMA_AIR) - 1.0
        compressor_temp_out = atm.temperature_k * (1.0 + (temp_rise_factor / cls.ETA_COMPRESSOR))
        
        # Compressor power consumed
        power_compressor = mass_flow_compressor * cls.CP_AIR * (compressor_temp_out - atm.temperature_k)
        
        # 4. Turbo Shaft Dynamics
        # Mechanical losses (friction)
        power_loss = cls.K_LOSS * (current_state.turbo_speed_rad_s ** 2)
        
        # Net power determines acceleration
        net_power = power_turbine - power_compressor - power_loss
        
        # Avoid division by zero at rest
        if current_state.turbo_speed_rad_s < cls.STARTUP_SPEED_REGULARIZATION_RAD_S:
            # Linearize start-up torque if very slow to prevent division by zero
            torque = net_power / cls.STARTUP_SPEED_REGULARIZATION_RAD_S
        else:
            torque = net_power / current_state.turbo_speed_rad_s
            
        angular_acceleration = torque / cls.J_TURBO
        new_speed = current_state.turbo_speed_rad_s + (angular_acceleration * dt)
        new_speed = max(0.0, new_speed) # Cannot spin backwards
        
        # 5. Intake Manifold Dynamics (Plenum Mass/Energy Balance)
        # Mass balance: flow in from compressor minus flow out to engine
        mass_flow_net = mass_flow_compressor - engine_mass_flow_kg_s
        
        # Ideal gas law derivative: dP/dt = (R * T / V) * dm/dt
        # We assume manifold temperature reacts quickly to compressor out temp for now
        new_manifold_temp = compressor_temp_out
        
        dp_dt = (cls.R_AIR * new_manifold_temp / cls.V_MAP) * mass_flow_net
        new_manifold_pressure = current_state.manifold_pressure_pa + (dp_dt * dt)
        
        # Pressure cannot drop below a small physical minimum (avoid zero/negative)
        new_manifold_pressure = max(1000.0, new_manifold_pressure)
        
        return TurboState(
            turbo_speed_rad_s=new_speed,
            manifold_pressure_pa=new_manifold_pressure,
            manifold_temperature_k=new_manifold_temp,
            wastegate_position=wg_pos,
            tcu_error_integral=new_integral
        )
