# Phase 1F: Propeller Physics & Aerodynamic Coupling Theory

## 1. Overview
The final physical subsystem in the Phase 1 pipeline is the propeller model. It converts the rotational energy produced by the engine (delivered via the gearbox) into aerodynamic thrust and torque.

The model strictly adheres to standard reduced-order non-dimensional propeller theory, isolating aerodynamic effects from engine effects. The output torque magnitude produced here will serve as the opposing load in the torque balance of Phase 1E during system integration.

## 2. Theoretical Approach
The model assumes a fixed-pitch propeller, which matches the predominant configuration for standard UAV systems using a Rotax 914 UL-F without advanced constant-speed units.

### Non-dimensionalization
Propeller aerodynamics are dictated by the advance ratio ($J$), defined as:
$$J = \frac{V}{n \cdot D}$$
where $V$ is the free-stream airspeed, $n$ is the rotational frequency (rev/s), and $D$ is the propeller diameter.

The non-dimensional thrust ($C_T$) and torque ($C_Q$) coefficients are modeled as generic functions of $J$. Since proprietary maps for the exact Rotax-coupled propeller were not provided, this model employs a physically representative linear/parabolic surrogate model that decays predictably as advance ratio increases.

### Core Aerodynamic Outputs
Thrust and Torque are computed using standard aerodynamic scaling:
- **Thrust**: $T = C_T \cdot \rho \cdot n^2 \cdot D^4$
- **Torque**: $Q = C_Q \cdot \rho \cdot n^2 \cdot D^5$

The resulting absorbed power is strictly defined as $P = 2\pi n Q$, guaranteeing thermodynamic consistency within the aerodynamic subsystem.

## 3. Interfaces
- **Inputs**: Airspeed (Mission/Aircraft state), Ambient Density (Phase 1A), Propeller RPM (derived from Phase 1E through Gearbox).
- **Outputs**: Thrust (N), Aerodynamic Torque (Nm).
- **Coupling**: The Aerodynamic Torque ($Q$) represents the actual load opposing the engine rotation, completing the power cycle of the Digital Twin.
