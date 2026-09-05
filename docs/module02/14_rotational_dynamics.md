# Module 02 — 14. Engine Crankshaft Rotational Dynamics & Provenance Analysis

## 1. Physical Equations & Architecture

### Newton's Second Law for Rotational Dynamics
$$J_{\text{eng}} \cdot \frac{d\omega}{dt} = T_{\text{net}} = T_{\text{indicated}} - T_{\text{load}} - T_{\text{friction}} - T_{\text{pumping}} - T_{\text{alternator}}$$
where:
- $J_{\text{eng}}$: Engine rotational inertia ($\text{kg}\cdot\text{m}^2$) loaded directly from configuration (`rotational_inertia_kg_m2`).
- $\omega$: Crankshaft angular velocity ($\text{rad/s}$).
- $T_{\text{indicated}}$: Indicated combustion torque ($\text{N}\cdot\text{m}$), summed over all cylinders from the combustion model.
- $T_{\text{load}}$: External propeller shaft load torque ($\text{N}\cdot\text{m}$), referred through the gearbox.
- $T_{\text{friction}}$: Mechanical shaft friction torque ($\text{N}\cdot\text{m}$).
- $T_{\text{pumping}}$: Gas-exchange (pumping) torque ($\text{N}\cdot\text{m}$).
- $T_{\text{alternator}}$: Electrical accessory drag torque ($\text{N}\cdot\text{m}$).

> [!NOTE]
> **Reduced vs full form.** This document previously specified only the three-term
> balance $T_{\text{ind}} - T_{\text{load}} - T_{\text{fric}}$, which contradicted the
> five-term equation of motion in `01_architecture.md`. The five-term form is
> authoritative and is now implemented. The two parasitic terms default to
> $0.0\ \text{N}\cdot\text{m}$ in `compute_rotational_acceleration()`, so an isolated
> unit test that supplies only the three primary torques still exercises the reduced
> balance exactly. `EngineState` already declared `pumping_loss_torque_n_m` and
> `alternator_load_torque_n_m`; prior to this change both fields were orphaned — declared
> but never written by any physics code.

### Gas-Exchange (Pumping) Torque Model
$$\text{PMEP} = p_{\text{exhaust}} - p_{\text{manifold}} \qquad T_{\text{pumping}} = \frac{\text{PMEP} \cdot V_d}{4\pi}$$
A four-stroke engine completes one cycle per $4\pi$ radians of crankshaft rotation. The
sign is deliberately **not** clamped to non-negative values:
- Throttled / naturally aspirated operation ($p_{\text{manifold}} < p_{\text{exhaust}}$) gives $T_{\text{pumping}} > 0$: a true parasitic loss.
- Boosted operation ($p_{\text{manifold}} > p_{\text{exhaust}}$) gives $T_{\text{pumping}} < 0$: the positive gas-exchange work that turbocharging returns to the crankshaft. Clamping would silently discard genuine boost work.

### Electrical Accessory Drag Torque Model
$$T_{\text{alternator}} = \frac{P_{\text{electrical}}}{\eta_{\text{drive}} \cdot \omega} \quad (\omega > 1.0\ \text{rad/s}),\qquad 0.0 \text{ otherwise}$$
The angular-velocity floor is a numerical-safety guard: a stationary crankshaft
transmits no accessory drag torque, and the quotient would otherwise diverge.

### Directional Mechanical Friction Torque Model
$$T_{\text{friction}}(\omega) = \text{sgn}(\omega) \cdot \left[ T_{\text{static}} \cdot \tanh(3.0 \cdot |\omega|) + c_{\text{viscous}} \cdot |\omega| + c_{\text{hydro}} \cdot \omega^2 \right]$$
Friction direction strictly opposes the direction of rotation:
- $\omega > 0 \implies T_{\text{friction}} > 0$ (opposes positive rotation)
- $\omega < 0 \implies T_{\text{friction}} < 0$ (opposes negative rotation)
- $\omega = 0 \implies T_{\text{friction}} = 0$ (no dynamic friction torque at rest)

---

## 2. Torque Audit & Provenance Clarification

### Derivation from 180 HP Takeoff Power
- Rated Power: $P = 180.0\text{ HP} = 134,226.0\text{ W}$ (`DRDO_PUBLIC_RELEASE`, `OFFICIAL`).
- Rated Rotational Speed: $N = 4200.0\text{ RPM}$ ($439.823\text{ rad/s}$, `REPORTED`).
- Rated Shaft Brake Torque ($T_{\text{brake}}$):
  $$T_{\text{brake}} = \frac{P}{\omega} = \frac{134,226.0}{439.82297} = 305.182 \approx 305.2 \quad [\text{N}\cdot\text{m}]$$

### Indicated Torque Capacity Estimate ($320.0\text{ N}\cdot\text{m}$)
Indicated combustion torque must overcome internal friction torque before delivering net shaft brake torque:
$$T_{\text{indicated}} = T_{\text{brake}} + T_{\text{friction}}$$
At rated $4200\text{ RPM}$ ($\omega \approx 440\text{ rad/s}$), mechanical friction torque is:
$$T_{\text{friction}}(440) = 15.0 + (0.05 \cdot 440) + (0.0001 \cdot 440^2) = 15.0 + 22.0 + 19.36 = 56.36 \quad [\text{N}\cdot\text{m}]$$
Thus, full indicated torque required to deliver $305.2\text{ N}\cdot\text{m}$ brake torque at $4200\text{ RPM}$ is $305.2 + 56.4 = 361.6\text{ N}\cdot\text{m}$.

The configured profile entry `max_indicated_torque_n_m: 320.0 N*m` is documented **ONLY** as a provisional torque-capacity estimate for Phase 3.1 testing. It is **NOT** a validated torque map and **NOT** a value derived directly from rated power. No arbitrary efficiency factor has been fabricated to force $320.0\text{ N}\cdot\text{m}$ to match.

> [!IMPORTANT]
> **PROVENANCE CLASSIFICATION**: `max_indicated_torque_n_m` is strictly classified as `ESTIMATED` with `calibration_required: true`.

---

## 3. End-to-End Configuration Flow

```
[ENGINE YAML CONFIG]
       │ (configs/module02/engines/*.yaml)
       ▼
[ConfigLoader]
       │ (load_engine_config)
       ▼
[Engine Configuration Dict]
       │
       ▼
[EngineRunner]
       │ (Extracts inertia, max_torque, friction coefficients from dict)
       ▼
[RotationalDynamicsModel]
       │ (Solves J * alpha = T_net)
       ▼
[EngineState] (rpm, omega, t_ind, t_fric)
```
