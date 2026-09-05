"""
Module 02 Five-Term Rotational Equation of Motion Tests.
SIH26054 — Module 02 Engine Simulator.

Covers the correction of a documentation-versus-implementation discrepancy:
`docs/module02/01_architecture.md` specifies the five-term crankshaft equation of motion
    J * d(omega)/dt = T_ind - T_load - T_fric - T_pump - T_alt
while the Phase 3.1 implementation solved only the reduced three-term balance, leaving
`EngineState.pumping_loss_torque_n_m` and `EngineState.alternator_load_torque_n_m`
declared but never written by any physics code.
"""

import math

import pytest

from src.module02.physics.rotational_dynamics import (
    RotationalDynamicsError,
    RotationalDynamicsModel,
)


class TestReducedFormBackwardCompatibility:
    """The three-torque call signature must remain exactly equivalent to the reduced balance."""

    def test_three_torque_call_recovers_reduced_balance(self):
        """Omitting the parasitic terms must reproduce T_net = T_ind - T_load - T_fric identically."""
        t_net, alpha = RotationalDynamicsModel.compute_rotational_acceleration(
            t_indicated_n_m=300.0,
            t_load_n_m=120.0,
            t_friction_n_m=55.0,
            inertia_kg_m2=0.55,
        )
        assert t_net == pytest.approx(125.0)
        assert alpha == pytest.approx(125.0 / 0.55)

    def test_positional_call_order_is_preserved(self):
        """The first four positional slots must not have been reordered by the extension."""
        t_net, alpha = RotationalDynamicsModel.compute_rotational_acceleration(
            300.0, 120.0, 55.0, 0.55
        )
        assert t_net == pytest.approx(125.0)
        assert alpha == pytest.approx(125.0 / 0.55)

    def test_explicit_zero_parasitics_match_omitted_parasitics(self):
        """Passing 0.0 explicitly must be indistinguishable from relying on the defaults."""
        omitted = RotationalDynamicsModel.compute_rotational_acceleration(
            300.0, 120.0, 55.0, 0.55
        )
        explicit = RotationalDynamicsModel.compute_rotational_acceleration(
            300.0, 120.0, 55.0, 0.55, t_pumping_n_m=0.0, t_alternator_n_m=0.0
        )
        assert omitted == explicit


class TestFiveTermBalance:
    """The full five-term balance must subtract both parasitic torques."""

    def test_parasitic_terms_reduce_net_torque(self):
        """T_pump and T_alt must both be subtracted, not added or ignored."""
        t_net, alpha = RotationalDynamicsModel.compute_rotational_acceleration(
            t_indicated_n_m=300.0,
            t_load_n_m=120.0,
            t_friction_n_m=55.0,
            inertia_kg_m2=0.55,
            t_pumping_n_m=8.0,
            t_alternator_n_m=4.0,
        )
        assert t_net == pytest.approx(113.0)
        assert alpha == pytest.approx(113.0 / 0.55)

    def test_negative_pumping_torque_increases_net_torque(self):
        """Boosted operation returns gas-exchange work, so a negative T_pump must add torque."""
        baseline, _ = RotationalDynamicsModel.compute_rotational_acceleration(
            300.0, 120.0, 55.0, 0.55
        )
        boosted, _ = RotationalDynamicsModel.compute_rotational_acceleration(
            300.0, 120.0, 55.0, 0.55, t_pumping_n_m=-10.0
        )
        assert boosted > baseline
        assert boosted == pytest.approx(baseline + 10.0)

    @pytest.mark.parametrize("bad_value", [float("nan"), float("inf"), float("-inf")])
    def test_non_finite_parasitic_torques_are_rejected(self, bad_value):
        """Numerical-safety validation must extend to the newly added torque terms."""
        with pytest.raises(RotationalDynamicsError):
            RotationalDynamicsModel.compute_rotational_acceleration(
                300.0, 120.0, 55.0, 0.55, t_pumping_n_m=bad_value
            )
        with pytest.raises(RotationalDynamicsError):
            RotationalDynamicsModel.compute_rotational_acceleration(
                300.0, 120.0, 55.0, 0.55, t_alternator_n_m=bad_value
            )


class TestPumpingLossTorque:
    """Gas-exchange torque must follow PMEP * V_d / (4*pi) with a physically signed result."""

    def test_throttled_operation_is_a_parasitic_loss(self):
        """p_manifold < p_exhaust must yield a positive (loss) pumping torque."""
        t_pump = RotationalDynamicsModel.compute_pumping_loss_torque(
            manifold_pressure_pa=60000.0,
            exhaust_backpressure_pa=105000.0,
            displacement_m3=0.0020,
        )
        assert t_pump > 0.0
        expected = (105000.0 - 60000.0) * 0.0020 / (4.0 * math.pi)
        assert t_pump == pytest.approx(expected)

    def test_boosted_operation_returns_positive_gas_exchange_work(self):
        """p_manifold > p_exhaust must yield a negative pumping torque, not a clamped zero."""
        t_pump = RotationalDynamicsModel.compute_pumping_loss_torque(
            manifold_pressure_pa=220000.0,
            exhaust_backpressure_pa=150000.0,
            displacement_m3=0.0020,
        )
        assert t_pump < 0.0, "Boost work must not be silently clamped away."

    def test_pumping_torque_scales_with_displacement(self):
        """Torque is proportional to swept volume."""
        small = RotationalDynamicsModel.compute_pumping_loss_torque(60000.0, 105000.0, 0.0010)
        large = RotationalDynamicsModel.compute_pumping_loss_torque(60000.0, 105000.0, 0.0020)
        assert large == pytest.approx(2.0 * small)

    def test_equal_pressures_yield_zero_pumping_torque(self):
        """No pressure differential across gas exchange means no pumping torque."""
        assert RotationalDynamicsModel.compute_pumping_loss_torque(
            101325.0, 101325.0, 0.0020
        ) == pytest.approx(0.0)

    @pytest.mark.parametrize(
        "p_man,p_exh,v_d",
        [
            (0.0, 105000.0, 0.0020),
            (-1.0, 105000.0, 0.0020),
            (60000.0, 0.0, 0.0020),
            (60000.0, 105000.0, 0.0),
            (60000.0, 105000.0, -0.001),
            (float("nan"), 105000.0, 0.0020),
            (60000.0, float("inf"), 0.0020),
        ],
    )
    def test_invalid_pumping_inputs_are_rejected(self, p_man, p_exh, v_d):
        """Non-physical pressures or displacements must raise rather than propagate."""
        with pytest.raises(RotationalDynamicsError):
            RotationalDynamicsModel.compute_pumping_loss_torque(p_man, p_exh, v_d)


class TestAccessoryDragTorque:
    """Electrical accessory drag must derive from real mechanical power, not a fixed constant."""

    def test_accessory_torque_matches_power_over_speed(self):
        """T_alt = (P_elec / eta) / omega."""
        t_alt = RotationalDynamicsModel.compute_accessory_drag_torque(
            electrical_power_w=700.0,
            omega_rad_per_sec=350.0,
            drive_efficiency=0.55,
        )
        assert t_alt == pytest.approx((700.0 / 0.55) / 350.0)

    def test_zero_electrical_load_yields_zero_torque(self):
        """An unloaded alternator applies no drag torque."""
        assert RotationalDynamicsModel.compute_accessory_drag_torque(0.0, 350.0, 0.55) == pytest.approx(0.0)

    def test_stationary_crankshaft_yields_zero_torque(self):
        """Below the angular-velocity floor the term must be zero, never a division blow-up."""
        result = RotationalDynamicsModel.compute_accessory_drag_torque(700.0, 0.0, 0.55)
        assert result == 0.0
        assert math.isfinite(result)

    def test_accessory_torque_falls_as_speed_rises(self):
        """At constant electrical load, drag torque decreases with crankshaft speed."""
        low = RotationalDynamicsModel.compute_accessory_drag_torque(700.0, 150.0, 0.55)
        high = RotationalDynamicsModel.compute_accessory_drag_torque(700.0, 440.0, 0.55)
        assert high < low

    def test_lower_drive_efficiency_costs_more_torque(self):
        """A less efficient drive must absorb more crankshaft torque for the same output."""
        efficient = RotationalDynamicsModel.compute_accessory_drag_torque(700.0, 350.0, 0.90)
        lossy = RotationalDynamicsModel.compute_accessory_drag_torque(700.0, 350.0, 0.45)
        assert lossy > efficient

    @pytest.mark.parametrize(
        "p_elec,omega,eta",
        [
            (-1.0, 350.0, 0.55),
            (700.0, 350.0, 0.0),
            (700.0, 350.0, -0.2),
            (700.0, 350.0, 1.5),
            (float("nan"), 350.0, 0.55),
            (700.0, float("inf"), 0.55),
        ],
    )
    def test_invalid_accessory_inputs_are_rejected(self, p_elec, omega, eta):
        """Non-physical power, efficiency, or speed must raise rather than propagate."""
        with pytest.raises(RotationalDynamicsError):
            RotationalDynamicsModel.compute_accessory_drag_torque(p_elec, omega, eta)
