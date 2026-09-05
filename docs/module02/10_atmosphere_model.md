# Module 02 — 10. Standard ISA Atmosphere & Moist Air Physics Model

## 1. Mathematical Equations

### Troposphere Standard Temperature Model ($h \le 11,000\text{ m}$)
$$T_{\text{standard}}(h) = T_{0,\text{sea}} - L \cdot h$$
where:
- $T_{0,\text{sea}} = 288.15\text{ K}$ ($15^\circ\text{C}$)
- $L = 0.0065\text{ K/m}$ (Troposphere temperature lapse rate)

### Actual Ambient Temperature ($T_{\text{actual}}$)
$$T_{\text{actual}}(h) = T_{\text{standard}}(h) + \Delta T_{\text{offset}}$$

### Barometric Ambient Static Pressure ($p_{\text{amb}}$)
$$p_{\text{amb}}(h) = p_{0,\text{sea}} \cdot \left(1 - \frac{L \cdot h}{T_{0,\text{sea}}}\right)^{\frac{g}{R_d L}}$$
where:
- $p_{0,\text{sea}} = 101325.0\text{ Pa}$
- $g = 9.80665\text{ m/s}^2$
- $R_d = 287.058\text{ J/(kg K)}$ (Dry air gas constant)

### Saturation Vapor Pressure ($p_{\text{sat}}$) & Vapor Pressure ($p_v$)
Using the Magnus-Tetens empirical equation for water vapor saturation:
$$p_{\text{sat}}(T) = 610.78 \cdot \exp\left(\frac{17.27 \cdot (T - 273.15)}{(T - 273.15) + 237.3}\right)$$
$$p_v = \frac{\text{RH}}{100} \cdot p_{\text{sat}}(T)$$

### Moist Air Mass Density ($\rho_{\text{moist}}$)
$$\rho_{\text{moist}} = \frac{p_d}{R_d \cdot T_{\text{actual}}} + \frac{p_v}{R_v \cdot T_{\text{actual}}}$$
where $p_d = p_{\text{amb}} - p_v$ and $R_v = 461.495\text{ J/(kg K)}$.

### Speed of Sound ($a$)
$$a = \sqrt{\gamma \cdot R_d \cdot T_{\text{actual}}}$$
where $\gamma = 1.4$.

---

## 2. Numerical Safety Boundaries
- Temperature Floor: $T \ge 150.0\text{ K}$
- Pressure Floor: $p \ge 100.0\text{ Pa}$
- Density Floor: $\rho \ge 0.001\text{ kg/m}^3$
- Altitude Limits: $-1000\text{ m} \le h \le 20,000\text{ m}$
- Relative Humidity Limits: $0.0\% \le \text{RH} \le 100.0\%$
- Rejects NaN, Inf, and invalid bounds with `AtmospherePhysicsError`.
