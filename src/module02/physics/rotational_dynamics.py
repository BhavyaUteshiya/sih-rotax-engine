"""
Module 02 Crankshaft Rotational Dynamics Subsystem (Phase 3.1 Hardened Physics Engine).
SIH26054 — Module 02 Engine Simulator.
"""

import math
from typing import Tuple


class RotationalDynamicsError(ValueError):
    """Raised when numerical safety or parameter boundary violations occur in rotational dynamics."""
    pass


class RotationalDynamicsModel:
    """
    Crankshaft Rotational Dynamics & Shaft Torque Balance Subsystem.
    Solves Newton's Second Law for Rotation in the full documented five-term form:

        J_eng * d(omega)/dt = T_indicated - T_load - T_friction - T_pumping - T_alternator

    The two parasitic terms (T_pumping, T_alternator) default to 0.0 N*m so that a caller
    supplying only the three primary torques recovers the reduced Phase 3.1 balance
    exactly. This keeps the reduced form available for isolated unit testing of the
    core integrator while the full form is used by the integrated engine runner.

    All parameters are strictly configuration-driven without hard-coded Python defaults.
    All calculations strictly use Canonical SI Units (rad/s, N*m, kg*m^2, Pa, m^3, seconds).
    """

    FOUR_STROKE_RADIANS_PER_CYCLE: float = 4.0 * math.pi  # Two crankshaft revolutions per cycle

    @classmethod
    def rpm_to_rad_per_sec(cls, rpm: float) -> float:
        """Converts Rotational Speed from RPM (rev/min) to Canonical SI Angular Velocity omega (rad/s)."""
        r = float(rpm)
        if math.isnan(r) or math.isinf(r):
            raise RotationalDynamicsError(f"Invalid RPM: {rpm}. Cannot be NaN or Inf.")
        return r * (math.pi / 30.0)

    @classmethod
    def rad_per_sec_to_rpm(cls, rad_per_sec: float) -> float:
        """Converts Angular Velocity omega (rad/s) to display/derived RPM (rev/min)."""
        w = float(rad_per_sec)
        if math.isnan(w) or math.isinf(w):
            raise RotationalDynamicsError(f"Invalid angular velocity omega: {rad_per_sec}. Cannot be NaN or Inf.")
        return w * (30.0 / math.pi)

    @classmethod
    def validate_throttle_input(cls, throttle_percent: float) -> float:
        """Validates throttle command demand boundary [0.0%, 100.0%]."""
        th = float(throttle_percent)
        if math.isnan(th) or math.isinf(th):
            raise RotationalDynamicsError(f"Invalid throttle input: {throttle_percent}. Cannot be NaN or Inf.")
        if not (0.0 <= th <= 100.0):
            raise RotationalDynamicsError(f"Throttle demand {throttle_percent}% out of valid range [0.0, 100.0].")
        return th

    @classmethod
    def compute_torque_demand_interface(cls, throttle_percent: float, max_torque_n_m: float) -> float:
        """
        Temporary Phase 3.1 Indicated Torque Demand Interface.
        T_indicated = (throttle / 100.0) * max_torque_n_m

        NOTE: This is a clearly isolated temporary demand interface that will later be replaced
        by the full thermodynamic combustion model in Phase 3.3/3.4.
        """
        th = cls.validate_throttle_input(throttle_percent)
        max_t = float(max_torque_n_m)
        if math.isnan(max_t) or math.isinf(max_t) or max_t <= 0:
            raise RotationalDynamicsError(f"Maximum torque capacity must be positive. Got {max_torque_n_m} N*m.")
        return (th / 100.0) * max_t

    @classmethod
    def compute_friction_torque(
        cls,
        omega_rad_per_sec: float,
        friction_static_n_m: float,
        friction_viscous_n_m_s_rad: float,
        friction_hydrodynamic_n_m_s2_rad2: float
    ) -> float:
        """
        Computes mechanical shaft friction torque T_friction(omega) in N*m.
        Friction direction opposes the direction of rotation:
        - omega > 0 => T_friction > 0 (opposes positive rotation)
        - omega < 0 => T_friction < 0 (opposes negative rotation)
        - omega = 0 => T_friction = 0 (no dynamic friction torque at rest)
        """
        w = float(omega_rad_per_sec)
        if math.isnan(w) or math.isinf(w):
            raise RotationalDynamicsError(f"Invalid angular velocity omega: {omega_rad_per_sec}.")

        f_static = float(friction_static_n_m)
        f_viscous = float(friction_viscous_n_m_s_rad)
        f_hydro = float(friction_hydrodynamic_n_m_s2_rad2)

        if f_static < 0 or f_viscous < 0 or f_hydro < 0:
            raise RotationalDynamicsError("Friction coefficients must be non-negative.")

        if w == 0.0:
            return 0.0

        w_abs = abs(w)
        sign_w = 1.0 if w > 0.0 else -1.0

        # Smooth breakaway transition near zero velocity
        t_mag = f_static * math.tanh(3.0 * w_abs) + f_viscous * w_abs + f_hydro * (w_abs * w_abs)
        return sign_w * t_mag

    @classmethod
    def compute_pumping_loss_torque(
        cls,
        manifold_pressure_pa: float,
        exhaust_backpressure_pa: float,
        displacement_m3: float
    ) -> float:
        """
        PHYSICAL MODEL:
        Computes gas-exchange (pumping) torque T_pumping in N*m from the pumping mean
        effective pressure across the intake and exhaust strokes:

            PMEP    = p_exhaust - p_manifold
            W_cycle = PMEP * V_d                       [J per engine cycle]
            T_pump  = W_cycle / (4 * pi)               [4-stroke: 4*pi rad per cycle]

        Sign convention is physically meaningful and deliberately NOT clamped:
        - Naturally aspirated / throttled operation (p_manifold < p_exhaust) yields
          T_pump > 0, a genuine parasitic loss opposing rotation.
        - Boosted operation (p_manifold > p_exhaust) yields T_pump < 0, correctly
          representing the positive gas-exchange work a turbocharger returns to the
          crankshaft. Clamping this to zero would silently discard real boost work.
        """
        p_man = float(manifold_pressure_pa)
        p_exh = float(exhaust_backpressure_pa)
        v_d = float(displacement_m3)

        if math.isnan(p_man) or math.isinf(p_man) or p_man <= 0:
            raise RotationalDynamicsError(f"Invalid manifold pressure: {manifold_pressure_pa} Pa.")

        if math.isnan(p_exh) or math.isinf(p_exh) or p_exh <= 0:
            raise RotationalDynamicsError(f"Invalid exhaust backpressure: {exhaust_backpressure_pa} Pa.")

        if math.isnan(v_d) or math.isinf(v_d) or v_d <= 0:
            raise RotationalDynamicsError(f"Invalid engine displacement: {displacement_m3} m^3.")

        pmep = p_exh - p_man
        return (pmep * v_d) / cls.FOUR_STROKE_RADIANS_PER_CYCLE

    @classmethod
    def compute_accessory_drag_torque(
        cls,
        electrical_power_w: float,
        omega_rad_per_sec: float,
        drive_efficiency: float
    ) -> float:
        """
        PHYSICAL MODEL:
        Computes the crankshaft torque T_alternator absorbed by the electrical
        generation accessory from the mechanical power it must supply:

            P_mech = P_electrical / eta_drive
            T_alt  = P_mech / omega

        Returns 0.0 below a numerically safe angular velocity floor, because a
        stationary crankshaft transmits no accessory drag torque and the division
        would otherwise diverge.
        """
        p_elec = float(electrical_power_w)
        w = float(omega_rad_per_sec)
        eta = float(drive_efficiency)

        if math.isnan(p_elec) or math.isinf(p_elec) or p_elec < 0:
            raise RotationalDynamicsError(f"Electrical load power must be non-negative. Got {electrical_power_w} W.")

        if math.isnan(w) or math.isinf(w):
            raise RotationalDynamicsError(f"Invalid angular velocity omega: {omega_rad_per_sec}.")

        if math.isnan(eta) or math.isinf(eta) or not (0.0 < eta <= 1.0):
            raise RotationalDynamicsError(f"Accessory drive efficiency must be in (0.0, 1.0]. Got {drive_efficiency}.")

        if w <= 1.0:
            return 0.0

        return (p_elec / eta) / w

    @classmethod
    def compute_rotational_acceleration(
        cls,
        t_indicated_n_m: float,
        t_load_n_m: float,
        t_friction_n_m: float,
        inertia_kg_m2: float,
        t_pumping_n_m: float = 0.0,
        t_alternator_n_m: float = 0.0
    ) -> Tuple[float, float]:
        """
        Solves the full five-term net torque balance and rotational acceleration
        alpha = d(omega)/dt:

            T_net = T_indicated - T_load - T_friction - T_pumping - T_alternator
            alpha = T_net / J_eng

        The parasitic terms default to 0.0 N*m, so a three-torque caller recovers the
        reduced balance T_net = T_indicated - T_load - T_friction identically.
        Returns Tuple of (t_net_n_m, alpha_rad_per_sec2).
        """
        j_eng = float(inertia_kg_m2)
        if math.isnan(j_eng) or math.isinf(j_eng) or j_eng <= 0:
            raise RotationalDynamicsError(f"Rotational inertia J_eng must be positive. Got {inertia_kg_m2} kg*m^2.")

        t_ind = float(t_indicated_n_m)
        t_load = float(t_load_n_m)
        t_fric = float(t_friction_n_m)
        t_pump = float(t_pumping_n_m)
        t_alt = float(t_alternator_n_m)

        for label, value in (
            ("T_indicated", t_ind),
            ("T_load", t_load),
            ("T_friction", t_fric),
            ("T_pumping", t_pump),
            ("T_alternator", t_alt),
        ):
            if math.isnan(value) or math.isinf(value):
                raise RotationalDynamicsError(f"Torque input {label} cannot be NaN or Inf.")

        t_net = t_ind - t_load - t_fric - t_pump - t_alt
        alpha = t_net / j_eng

        return (t_net, alpha)

    @classmethod
    def integrate_angular_velocity(
        cls,
        current_omega_rad_per_sec: float,
        alpha_rad_per_sec2: float,
        dt_seconds: float
    ) -> float:
        """
        Integrates angular velocity omega(t + dt) = max(0.0, omega(t) + alpha * dt).
        Crankshaft rotation is strictly non-negative (omega >= 0).
        """
        dt = float(dt_seconds)
        if math.isnan(dt) or math.isinf(dt) or dt <= 0:
            raise RotationalDynamicsError(f"Timestep dt must be positive. Got {dt_seconds} s.")

        w_curr = float(current_omega_rad_per_sec)
        a = float(alpha_rad_per_sec2)

        if math.isnan(w_curr) or math.isinf(w_curr) or math.isnan(a) or math.isinf(a):
            raise RotationalDynamicsError("Angular velocity or acceleration cannot be NaN or Inf.")

        w_next = w_curr + (a * dt)
        return max(0.0, w_next)
