# Module 02 — 11. Flight Environment & Aerodynamic Vector Model

## 1. Coordinate System Convention
The flight environment model strictly uses the standard **North-East-Down (NED)** right-handed local Cartesian coordinate frame:
- **North ($X_{\text{NED}}$)**: Positive towards geographic North.
- **East ($Y_{\text{NED}}$)**: Positive towards geographic East.
- **Down ($Z_{\text{NED}}$)**: Positive downwards towards Earth center. Altitude $h = -Z_{\text{NED}}$.

---

## 2. Vector Velocity Relationships

### Aircraft Ground Velocity Vector ($\vec{V}_{\text{ground}}$)
$$\vec{V}_{\text{ground}} = \begin{pmatrix} V_{g,N} \\ V_{g,E} \\ V_{g,D} \end{pmatrix}$$
where vertical speed $V_z = -V_{g,D}$.

### Ambient Wind Vector ($\vec{V}_{\text{wind}}$)
$$\vec{V}_{\text{wind}} = \begin{pmatrix} V_{w,N} \\ V_{w,E} \\ V_{w,D} \end{pmatrix}$$

### Relative Air Velocity Vector ($\vec{V}_{\text{rel}}$)
$$\vec{V}_{\text{rel}} = \vec{V}_{\text{ground}} - \vec{V}_{\text{wind}} = \begin{pmatrix} V_{g,N} - V_{w,N} \\ V_{g,E} - V_{w,E} \\ V_{g,D} - V_{w,D} \end{pmatrix}$$

### True Airspeed (TAS)
$$V_{\text{TAS}} = \|\vec{V}_{\text{rel}}\| = \sqrt{(V_{g,N} - V_{w,N})^2 + (V_{g,E} - V_{w,E})^2 + (V_{g,D} - V_{w,D})^2}$$

---

## 3. Dynamic Pressure ($q$)
$$q = \frac{1}{2} \cdot \rho_{\text{moist}} \cdot V_{\text{TAS}}^2$$
Expressed in Pascals. Serves as the primary aerodynamic dynamic state for future lift, drag, and propeller load coupling.

---

## 4. Altitude Kinematic Progression
$$\frac{dh}{dt} = V_z = -V_{g,D}$$
$$h(t + dt) = h(t) + V_z \cdot dt$$
Integrated deterministically inside `EnvironmentRunner` with timestep $dt = 0.01\text{ s}$.
