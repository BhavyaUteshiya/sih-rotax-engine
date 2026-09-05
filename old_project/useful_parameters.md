# Curated legacy parameters

- The legacy Phase 1 model used a Rotax reduction-speed convention of `omega_prop / omega_engine = 0.41176`; the active model retains this convention and its inertia reflection is `J_engine + J_prop * ratio²`.
- Legacy use of 110,000 Pa as full-throttle target MAP is retained only as a configurable prototype calibration value. It is not recorded as an official Rotax specification.
- Turbo inertias, efficiencies, manifold volume, friction coefficients, propeller geometry, and thermal capacities in the old code are surrogate/calibration values unless a source is added to the active reference registry.
