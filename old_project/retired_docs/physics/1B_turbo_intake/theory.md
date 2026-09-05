# Phase 1B: Turbo / Intake Theory

This document outlines the physical reasoning behind the reduced-order causal model implemented in the Phase 1B Digital Twin for the Rotax 914.

## Core Causal Chain

Unlike a simple mapped interpolator, this subsystem enforces a physical chain of events:
1. **Target Demand**: The engine requires a specific manifold absolute pressure (MAP), dictated by the throttle/TCU.
2. **Wastegate Actuation**: The TCU surrogate actuates a wastegate to redirect exhaust flow around or through the turbine to meet this demand.
3. **Turbine Energy Extraction**: The mass flow passing through the turbine expands (dropping in pressure and temperature) and performs mechanical work on the turbo shaft.
4. **Shaft Acceleration**: Net power (turbine power minus compressor power minus friction) accelerates or decelerates the turbocharger shaft. This inertia introduces the realistic physical lag of the turbo.
5. **Compressor Pumping**: The spinning compressor pushes air into the intake manifold based on its speed and the opposing pressure ratio.
6. **Manifold Charging**: The manifold (airbox) acts as a plenum. It pressurizes when the compressor supplies more mass flow than the engine consumes.

## The Surrogate Compressor Model

A major challenge in creating a physical twin is the absence of proprietary manufacturer compressor and turbine maps. To solve this, Phase 1B uses a **Calibratable Reduced-Order Surrogate** inspired by the qualitative behaviour identified in high-altitude performance research (Mansouri & Ommi, 2019). Note that the numerical outputs from this surrogate are purely model outputs and are not claimed to be exact measured Rotax values.

### Compressor Pressure Ratio (PR)
Instead of a full 2D map, we model the maximum pressure ratio the compressor can produce at a given shaft speed using a quadratic relation:
$PR_{max}(\omega) = 1 + k_{pr} \omega^2$

### Compressor Mass Flow
The compressor acts similarly to a centrifugal pump. If the actual manifold pressure ratio $PR_{actual} = P_{map} / P_{amb}$ is less than $PR_{max}$, air flows into the manifold:
$\dot{m}_c = k_{flow} \cdot \omega \cdot \max(0, PR_{max} - PR_{actual})$

This satisfies two critical physical realities:
1. **High Altitude Behavior**: At high altitude, $P_{amb}$ is lower. To maintain the same $P_{map}$, $PR_{actual}$ increases. This forces the turbocharger to spin faster ($\omega$ must increase) to keep $PR_{max}$ above $PR_{actual}$ and supply airflow.
2. **Compressor Flow-Limit Boundary**: If the manifold pressure exceeds the compressor's pumping capability ($PR_{actual} \ge PR_{max}$), flow stops. This is a mathematical flow-limit boundary surrogate, NOT an explicit dynamic compressor surge/stall oscillatory model.

## Thermodynamics

- **Compressor Heating**: The isentropic temperature rise formula ensures that compressing air adds heat to the manifold:
  $T_{comp\_out} = T_{amb} \left(1 + \frac{PR^{\frac{\gamma-1}{\gamma}} - 1}{\eta_c}\right)$
  Hotter ambient conditions naturally reduce air density, impacting the compressor mass flow and altering performance exactly as seen in empirical high-altitude tests.

- **Turbine Cooling**: As exhaust gas powers the turbine, its temperature drops due to isentropic expansion.

## TCU Wastegate Surrogate
Since the proprietary Rotax TCU algorithm is closed-source, a physical control proxy (a PI controller) is used. It modulates the wastegate fraction between 0.0 (fully closed to exhaust bypass) and 1.0 (fully open), directly altering $\dot{m}_t$ and enforcing a causal control loop.
The PI controller calculates error as `Target MAP - Actual MAP`. A negative error unwinds the integral state, opening the wastegate to reduce boost. A bounded anti-windup prevents runaway integral states.
