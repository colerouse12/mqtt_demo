"""
Smart Hub Substation that manages power distribution between generators and devices.
"""
import json
import time
import sys
import os
# Add parent directory to path for imports when running directly
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import paho.mqtt.client as mqtt
from config import topics


class SmartSubstation:
    """
    Smart Hub Substation that:
    - Receives power from generators
    - Tracks total available power
    - Manages power distribution to devices (lightbulbs, etc.)
    - Reports power status and availability
    """
    def __init__(self, substation_id="substation1", broker="localhost"):
        self.substation_id = substation_id
        self.broker = broker
        
        # Power tracking
        self.generator_outputs = {}  # {plc_id: kw_output}
        self.total_generated_power = 0.0
        
        # Device consumption tracking
        self.device_consumption = {}  # {device_id: power_kw}
        self.total_consumption = 0.0
        
        # Power availability
        self.available_power = 0.0
        
        self.client = mqtt.Client()
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message
        
        print(f"[{substation_id}] Connecting to MQTT broker {broker}:1883")
        self.client.connect(broker, 1883, 60)
        self.client.loop_start()
        
        self.last_pub = 0
    
    def on_connect(self, client, userdata, flags, rc):
        # Subscribe to generator telemetry
        client.subscribe("plc/telemetry/#")
        print(f"[{self.substation_id}] Subscribed to plc/telemetry/#")
        
        # Subscribe to device status (lightbulbs, etc.)
        client.subscribe("lightbulb/status/#")
        print(f"[{self.substation_id}] Subscribed to lightbulb/status/#")
        
        # Subscribe to power requests
        client.subscribe("substation/power_request/#")
        print(f"[{self.substation_id}] Subscribed to substation/power_request/#")
    
    def on_message(self, client, userdata, msg):
        topic = msg.topic
        payload = msg.payload.decode()
        
        # Update generator outputs
        if topic.startswith("plc/telemetry/"):
            try:
                parts = topic.split("/")
                if len(parts) >= 3:
                    plc_id = parts[-1]
                    data = json.loads(payload)
                    kw_output = data.get("kw", 0.0)
                    self.generator_outputs[plc_id] = kw_output
                    self.update_power_status()
            except:
                pass
        
        # Update device consumption
        elif topic.startswith("lightbulb/status/"):
            try:
                parts = topic.split("/")
                if len(parts) >= 3:
                    device_id = parts[-1]
                    data = json.loads(payload)
                    if data.get("state") == "ON":
                        self.device_consumption[device_id] = data.get("power_kw", 0.0)
                    else:
                        self.device_consumption.pop(device_id, None)
                    self.update_power_status()
            except:
                pass
        
        # Handle power requests
        elif topic.startswith("substation/power_request/"):
            try:
                parts = topic.split("/")
                if len(parts) >= 3:
                    device_id = parts[-1]
                    data = json.loads(payload)
                    requested_power = float(data.get("power_kw", 0.0))
                    self.handle_power_request(device_id, requested_power)
            except:
                pass
    
    def update_power_status(self):
        """Update total power calculations."""
        self.total_generated_power = sum(self.generator_outputs.values())
        self.total_consumption = sum(self.device_consumption.values())
        self.available_power = max(0.0, self.total_generated_power - self.total_consumption)
    
    def handle_power_request(self, device_id, requested_power):
        """Handle power request from a device."""
        if self.available_power >= requested_power:
            # Grant power
            response = {
                "granted": True,
                "available_power": round(self.available_power, 2),
                "requested_power": requested_power
            }
            topic = topics.SUBSTATION_POWER_RESPONSE.format(device=device_id)
            self.client.publish(topic, json.dumps(response))
            print(f"[{self.substation_id}] Granted {requested_power} kW to {device_id} (available: {self.available_power:.2f} kW)")
        else:
            # Deny power
            response = {
                "granted": False,
                "available_power": round(self.available_power, 2),
                "requested_power": requested_power,
                "reason": "Insufficient power"
            }
            topic = topics.SUBSTATION_POWER_RESPONSE.format(device=device_id)
            self.client.publish(topic, json.dumps(response))
            print(f"[{self.substation_id}] Denied {requested_power} kW to {device_id} (available: {self.available_power:.2f} kW)")
    
    def get_status(self):
        """Get current substation status."""
        return {
            "substation_id": self.substation_id,
            "total_generated_power": round(self.total_generated_power, 2),
            "total_consumption": round(self.total_consumption, 2),
            "available_power": round(self.available_power, 2),
            "generator_count": len(self.generator_outputs),
            "device_count": len(self.device_consumption),
            "utilization_percent": round((self.total_consumption / self.total_generated_power * 100) if self.total_generated_power > 0 else 0, 1)
        }
    
    def run(self):
        """Main loop - publish status periodically."""
        print(f"[{self.substation_id}] Starting substation loop...")
        while True:
            now = time.time()
            if now - self.last_pub > 2:
                status = self.get_status()
                self.client.publish(
                    topics.SUBSTATION_STATUS.format(substation=self.substation_id),
                    json.dumps(status)
                )
                self.last_pub = now
            time.sleep(0.1)


if __name__ == "__main__":
    substation = SmartSubstation()
    substation.run()

