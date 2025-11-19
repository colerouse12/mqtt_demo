import time, json, random
import sys
import os
# Add parent directory to path for imports when running directly
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import paho.mqtt.client as mqtt
from config import topics


class BasePLC:
    """
    Base class for simulated PLCs controlling generators.
    Provides:
    - MQTT connect
    - Handling START/STOP/RESET
    - Publishing heartbeat, status, telemetry
    - Generator simulation with fuel consumption
    - kW setpoint control
    """
    def __init__(self, plc_id, broker="localhost", max_fuel=100.0):
        self.plc_id = plc_id
        self.state = "STOPPED"
        self.fault_active = False
        
        # Generator parameters
        self.max_fuel = max_fuel  # Maximum fuel capacity in liters
        self.fuel_level = max_fuel  # Current fuel level in liters
        self.target_kw = 0.0  # Target kW setpoint
        self.actual_kw = 0.0  # Actual kW output
        self.fuel_consumption_rate = 0.0  # Liters per hour
        
        # Fuel consumption: ~0.3 L/h per kW (approximate for diesel generators)
        self.fuel_efficiency = 0.3  # L/h per kW
        
        self.client = mqtt.Client()
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message
        
        print(f"[{plc_id}] Connecting to MQTT broker {broker}:1883")
        self.client.connect(broker, 1883, 60)
        self.client.loop_start()

        self.last_pub = 0
        self.last_fuel_update = time.time()


    def on_connect(self, client, userdata, flags, rc):
        control_topic = topics.CONTROL.format(plc=self.plc_id)
        client.subscribe(control_topic)
        print(f"[{self.plc_id}] Subscribed to {control_topic}")


    def on_message(self, client, userdata, msg):
        topic = msg.topic
        payload = msg.payload.decode()
        
        if topic == topics.CONTROL.format(plc=self.plc_id):
            cmd = payload.upper()
            print(f"[{self.plc_id}] Command received: {cmd}")

            # Check if it's a setpoint command (format: SETPOINT:150 or KW:150)
            if cmd.startswith("SETPOINT:") or cmd.startswith("KW:"):
                try:
                    # Extract the numeric value
                    value_str = cmd.split(":")[1]
                    self.target_kw = float(value_str)
                    # Clamp to reasonable range (0-500 kW)
                    self.target_kw = max(0.0, min(500.0, self.target_kw))
                    print(f"[{self.plc_id}] Setpoint updated to {self.target_kw} kW via control topic")
                except (ValueError, IndexError):
                    print(f"[{self.plc_id}] Invalid setpoint format: {cmd}")
            
            # Standard control commands
            elif cmd == "START" and not self.fault_active and self.fuel_level > 0:
                self.state = "RUNNING"
            elif cmd == "STOP":
                self.state = "STOPPED"
                self.actual_kw = 0.0
                self.fuel_consumption_rate = 0.0
            elif cmd == "RESET":
                self.fault_active = False
                self.state = "STOPPED"
                self.actual_kw = 0.0
                self.fuel_consumption_rate = 0.0
                self.target_kw = 0.0
                self.fuel_level = self.max_fuel  # Refill fuel tank
                print(f"[{self.plc_id}] Generator reset - fuel refilled to {self.max_fuel}L, setpoint reset to 0")
            else:
                print(f"[{self.plc_id}] Unknown or invalid command.")


    def update_generator(self):
        """Update generator state and fuel consumption."""
        now = time.time()
        dt = now - self.last_fuel_update
        self.last_fuel_update = now
        
        if self.state == "RUNNING" and self.fuel_level > 0:
            # Gradually adjust actual kW towards target (simulate response time)
            if abs(self.actual_kw - self.target_kw) > 1.0:
                if self.actual_kw < self.target_kw:
                    self.actual_kw = min(self.target_kw, self.actual_kw + 10.0 * dt)
                else:
                    self.actual_kw = max(self.target_kw, self.actual_kw - 10.0 * dt)
            else:
                self.actual_kw = self.target_kw
            
            # Calculate fuel consumption (L/h = kW * efficiency)
            self.fuel_consumption_rate = self.actual_kw * self.fuel_efficiency
            
            # Consume fuel (convert L/h to L per second)
            fuel_consumed = (self.fuel_consumption_rate / 3600.0) * dt
            self.fuel_level = max(0.0, self.fuel_level - fuel_consumed)
            
            # Stop generator if out of fuel
            if self.fuel_level <= 0:
                self.state = "STOPPED"
                self.actual_kw = 0.0
                self.fuel_consumption_rate = 0.0
                print(f"[{self.plc_id}] Generator stopped - out of fuel")
        else:
            self.actual_kw = 0.0
            self.fuel_consumption_rate = 0.0


    def generate_telemetry(self):
        """Generate telemetry data for the generator."""
        self.update_generator()
        
        if self.state == "RUNNING":
            return {
                "kw": round(self.actual_kw, 1),
                "target_kw": round(self.target_kw, 1),
                "hz": 60.0,
                "fuel_level": round(self.fuel_level, 2),
                "fuel_max": self.max_fuel,
                "fuel_consumption": round(self.fuel_consumption_rate, 2)
            }
        return {
            "kw": 0.0,
            "target_kw": round(self.target_kw, 1),
            "hz": 60.0,
            "fuel_level": round(self.fuel_level, 2),
            "fuel_max": self.max_fuel,
            "fuel_consumption": 0.0
        }


    def run(self):
        print(f"[{self.plc_id}] Starting PLC loop...")
        while True:
            now = time.time()
            if now - self.last_pub > 2:
                self.client.publish(topics.HEARTBEAT.format(plc=self.plc_id), "OK")
                self.client.publish(topics.STATUS.format(plc=self.plc_id), self.state)
                self.client.publish(
                    topics.TELEMETRY.format(plc=self.plc_id),
                    json.dumps(self.generate_telemetry())
                )
                print(f"[{self.plc_id}] Published state={self.state}, fuel={self.fuel_level:.1f}/{self.max_fuel}L")
                self.last_pub = now
            time.sleep(0.1)

