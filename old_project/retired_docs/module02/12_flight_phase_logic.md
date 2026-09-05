# Module 02 — 12. Deterministic Flight Phase State Machine Logic

## 1. Overview
The flight phase of the simulation is determined deterministically from altitude $h$, True Airspeed $V_{\text{TAS}}$, and vertical speed $V_z$.

---

## 2. Transition Decision Tree

```
                      [Aircraft State]
                             |
                   Is Altitude h <= 0.5m?
                  /                      \
               [YES]                    [NO]
                /                          \
         Speed V_TAS <= 2m/s?          Is Altitude h <= 10m?
         /                 \             /                \
      [YES]               [NO]        [YES]              [NO]
        |                   |           |                  |
    (GROUND)         V_TAS <= 15m/s?  V_z < -0.5m/s?     V_z >= +0.5m/s? -> (CLIMB)
                      /          \     /          \     V_z <= -0.5m/s? -> (DESCENT)
                   [YES]        [NO] [YES]        [NO]  |V_z| < 0.5m/s  -> (CRUISE)
                    |            |     |            |
                 (TAXI)      (TAKEOFF) (LANDING) (TAKEOFF)
```

---

## 3. Flight Phase Definitions

| Flight Phase | Altitude Range | Airspeed Range | Vertical Speed ($V_z$) | Description |
| :--- | :--- | :--- | :--- | :--- |
| `GROUND` | $h \le 0.5\text{ m}$ | $V_{\text{TAS}} \le 2.0\text{ m/s}$ | $|V_z| \le 0.1\text{ m/s}$ | Stationary on ground / apron |
| `START` | $h \le 0.5\text{ m}$ | $V_{\text{TAS}} \le 2.0\text{ m/s}$ | $0.0\text{ m/s}$ | Engine cranking / start boundary state |
| `TAXI` | $h \le 0.5\text{ m}$ | $2.0 < V_{\text{TAS}} \le 15.0\text{ m/s}$ | $|V_z| \le 0.1\text{ m/s}$ | Low-speed ground taxiing |
| `TAKEOFF` | $h \le 10.0\text{ m}$ | $V_{\text{TAS}} > 15.0\text{ m/s}$ | $V_z \ge 0.0\text{ m/s}$ | Runway roll & initial departure climb |
| `CLIMB` | $h > 10.0\text{ m}$ | $V_{\text{TAS}} > 20.0\text{ m/s}$ | $V_z \ge +0.5\text{ m/s}$ | Sustained climb to cruise ceiling |
| `CRUISE` | $h \ge 100.0\text{ m}$ | $V_{\text{TAS}} > 30.0\text{ m/s}$ | $|V_z| < 0.5\text{ m/s}$ | Steady-state altitude & airspeed cruise |
| `DESCENT` | $h > 10.0\text{ m}$ | $V_{\text{TAS}} > 20.0\text{ m/s}$ | $V_z \le -0.5\text{ m/s}$ | Controlled descent from altitude |
| `LANDING` | $h \le 10.0\text{ m}$ | $15.0 < V_{\text{TAS}} \le 40.0\text{ m/s}$ | $V_z < -0.5\text{ m/s}$ | Final approach & touchdown flare |
