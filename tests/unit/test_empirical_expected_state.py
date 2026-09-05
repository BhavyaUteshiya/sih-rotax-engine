import os
import sys

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.digital_twin.services.twin_engine import DigitalTwinEngine
from src.digital_twin.models.observed_state import ObservedState
from src.digital_twin.physics.expected_behavior import ExpectedBehaviorModel

class MockSimState:
    class Engine:
        engine_rpm = 5000.0
        manifold_pressure_pa = 115000.0
        fuel_mass_flow_kg_s = 0.005
        air_mass_flow_kg_s = 0.07
        air_fuel_ratio = 14.0
        indicated_torque_total_n_m = 100.0
        indicated_power_total_w = 52000.0
        class Turbo:
            turbo_speed_rpm = 90000.0
        turbocharger = Turbo()
        
    class Thermodynamics:
        egt_k = 1000.0
        cht_k = 400.0
        oil_temp_k = 360.0
        coolant_temp_k = 350.0
        combustion_efficiency = 0.95
        
    class Environment:
        ambient_temp_k = 288.15
        ambient_pressure_pa = 101325.0
        air_density_kg_m3 = 1.225
        wind_speed_m_s = 0.0
        
    class Aircraft:
        altitude_m = 0.0
        velocity_m_s = 50.0
        
    def __init__(self):
        self.engines = {1: self.Engine()}
        self.thermodynamics = {1: self.Thermodynamics()}
        self.thermals = {1: self.Thermodynamics()}
        self.lubrication = {}
        self.environment = self.Environment()
        self.aircraft = self.Aircraft()


class MockPipeline:
    def __init__(self, sim_state):
        self.sim_state = sim_state

    def get_latest_frame(self):
        class Frame:
            def __init__(self, sim):
                self.sim = sim
            def get_measurement(self, pid):
                class Meas:
                    def __init__(self, val):
                        self.value = val
                
                # We inject a FAULT here in the observed telemetry for MAP
                if "manifold_pressure_pa" in pid:
                    return Meas(50000.0) # Fault: Telemetry shows low MAP (0.5 bar) despite high throttle
                
                if "crankshaft_rpm" in pid or "rpm" in pid and "turbo" not in pid and "gearbox" not in pid:
                    return Meas(self.sim.engines[1].engine_rpm)
                if "turbo_speed" in pid:
                    return Meas(self.sim.engines[1].turbocharger.turbo_speed_rpm)
                if "air_mass_flow" in pid:
                    return Meas(self.sim.engines[1].air_mass_flow_kg_s)
                if "fuel_mass_flow" in pid:
                    return Meas(self.sim.engines[1].fuel_mass_flow_kg_s)
                if "air_fuel_ratio" in pid:
                    return Meas(self.sim.engines[1].air_fuel_ratio)
                if "indicated_torque" in pid or "torque" in pid and "load" not in pid:
                    return Meas(self.sim.engines[1].indicated_torque_total_n_m)
                if "exhaust_gas_temp" in pid or "egt" in pid:
                    return Meas(self.sim.thermodynamics[1].egt_k)
                if "cylinder_head_temp" in pid or "cht" in pid:
                    return Meas(self.sim.thermodynamics[1].cht_k)
                if "coolant_temp" in pid:
                    return Meas(self.sim.thermodynamics[1].coolant_temp_k)
                if "oil_temp" in pid:
                    return Meas(self.sim.thermodynamics[1].oil_temp_k)
                if "oil_pressure" in pid:
                    return Meas(400000.0) # 4 bar
                if "airspeed" in pid:
                    return Meas(self.sim.aircraft.velocity_m_s)
                if "altitude" in pid:
                    return Meas(self.sim.aircraft.altitude_m)
                if "ambient_temp" in pid:
                    return Meas(self.sim.environment.ambient_temp_k)
                if "ambient_pressure" in pid:
                    return Meas(self.sim.environment.ambient_pressure_pa)
                if "ambient_density" in pid:
                    return Meas(self.sim.environment.air_density_kg_m3)
                if "wind" in pid:
                    return Meas(self.sim.environment.wind_speed_m_s)
                return None
        return Frame(self.sim_state)


def main():
    print("Testing Empirical Expected State Generation...")
    
    # 1. Setup mock states
    sim_state = MockSimState()
    pipeline = MockPipeline(sim_state)
    
    # 2. Setup digital twin engine
    dt_engine = DigitalTwinEngine(config_path="configs/digital_twin_config.yaml")
    
    # 3. Process a step with 100% throttle
    operating_context = {"throttle_1": 100.0}
    
    state = dt_engine.process_step(
        sim_state=sim_state,
        pipeline=pipeline,
        engine_index=1,
        timestamp=1.0,
        operating_context=operating_context
    )
    
    # 4. Analyze results
    print(f"\n--- EXPECTED STATE (from Empirical Model with Throttle=100%) ---")
    print(f"MAP: {state.expected_state.map_bar:.2f} bar (Should be ~1.15)")
    print(f"RPM: {state.expected_state.rpm:.0f} (Should be ~5800)")
    
    print(f"\n--- OBSERVED STATE (from Telemetry / Faulted) ---")
    print(f"MAP: {state.observed_state.map_bar:.2f} bar (Faulted to 0.5)")
    print(f"RPM: {state.observed_state.rpm:.0f}")
    
    print(f"\n--- RESIDUALS ---")
    map_res = state.residual_state.residuals.get("map_bar")
    if map_res:
        print(f"MAP Residual: {map_res.residual:.2f} (Warning: {map_res.warning_triggered})")
    
    rpm_res = state.residual_state.residuals.get("rpm")
    if rpm_res:
        print(f"RPM Residual: {rpm_res.residual:.2f} (Warning: {rpm_res.warning_triggered})")

    print(f"\n--- TWIN STATUS ---")
    print(f"Status: {state.status.value}")
    print(f"Confidence: {state.confidence}")
    print(f"Active Warnings: {len(state.warnings)}")

if __name__ == "__main__":
    main()
