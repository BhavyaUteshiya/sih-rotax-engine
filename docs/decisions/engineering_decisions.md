# Engineering decisions

| Decision | Rationale |
|---|---|
| One active package: `src/digital_twin` | Eliminates competing legacy implementations. |
| Retire telemetry/dashboard/residual runtime | These are later phases outside current scope. |
| Keep legacy material reference-only | Preserves useful context without runtime ambiguity. |
| Use `omega_prop / omega_engine` gearbox convention | Matches active code and gives `J_eq = J_engine + J_prop × r²`. |
| Expose target MAP and propeller diameter at the simulation boundary | Prevents prototype values from masquerading as official specifications. |
| Retain reduced-order physics | Transparent, testable foundation before data-driven extensions. |
