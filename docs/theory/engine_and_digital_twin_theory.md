# Engine and digital-twin theory

A four-stroke piston engine draws charge, compresses it, releases fuel energy through combustion, and expels exhaust. Indicated work produces crankshaft torque; friction, accessories, and the propeller consume it. Power is torque times angular speed. A reduction gearbox trades engine speed for higher propeller torque, so a propeller inertia reflected to the engine shaft scales with the square of `omega_prop / omega_engine`.

The Rotax 914 context adds a turbocharger: exhaust expansion powers a turbine coupled to a compressor, increasing intake manifold pressure. Throttle and manifold pressure set charge density; volumetric efficiency and speed determine air mass flow. Mixture strength controls fuel flow and combustion efficiency. The propeller converts shaft power into thrust, with load varying with RPM, density, and advance ratio. Temperatures evolve more slowly than combustion because metal and oil store heat.

A digital twin is a model that evolves alongside an asset. Physics-based reduced-order models emphasize causal structure, transparent assumptions, and feasible computation. They are appropriate here because no validated operational dataset is yet in scope. Future hybrid physics/data-driven work may calibrate or compare this foundation, but that work is not implemented in this phase.
