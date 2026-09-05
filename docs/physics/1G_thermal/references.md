# Phase 1G: Engine Thermal Physics - References

The thermal model relies primarily on classical heat transfer fundamentals and estimated physical properties.

## References

1. **Rotax Engine Type 914 Series Operators Manual / IPC**
   Provides general bounds for acceptable operating temperatures (CHT and Oil) and fluid capacities (~3.0 L oil) which informed the thermal mass estimates.

2. **Fundamentals of Heat and Mass Transfer (Incropera, DeWitt)**
   Provided the theoretical basis for the lumped-capacitance method (THERM-02, THERM-05) and the standard convective heat transfer scaling laws with density and velocity (THERM-07).

3. **Digital Twin Internal Calibration**
   Specific values for conductances ($G_{\text{base}}$), thermal mass ($C_{\text{th}}$), and heat fraction ($F_{\text{CHT}}$) were calibrated internally to reproduce nominal Rotax limits at steady-state high-power settings. They do not represent proprietary Rotax CAD geometry or exact certified thermal mass values.
