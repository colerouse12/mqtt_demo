"""
Simulated lightbulb that consumes power and can be controlled via MQTT.
Only turns on if there's enough power available from generators.
"""
import json
import time
import sys
import os
# Add parent directory to path for imports when running directly
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import paho.mqtt.client as mqtt
from config import topics


class Lightbulb:
    """
    Simulated lightbulb that:
    - Can be turned ON/OFF via MQTT
    - Consumes power when ON
    - Subscribes to generator outputs to check available power
    - Only turns on if sufficient power is available
    - Reports status and power consumption
    """
    def __init__(self, bulb_id, power_consumption=0.1, broker="localhost"):
        self.bulb_id = bulb_id
        self.power_consumption = power_consumption  # kW when ON
        self.state = "OFF"
        self.broker = broker
        
        # Power from substation
        self.available_power_from_substation = 0.0
        self.power_granted = False
        
        self.client = mqtt.Client()
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message
        
        print(f"[{bulb_id}] Connecting to MQTT broker {broker}:1883")
        self.client.connect(broker, 1883, 60)
        self.client.loop_start()
        
        self.last_pub = 0
        self.last_power_check = time.time()
    
    def on_connect(self, client, userdata, flags, rc):
        control_topic = topics.LIGHTBULB_CONTROL.format(bulb=self.bulb_id)
        client.subscribe(control_topic)
        print(f"[{self.bulb_id}] Subscribed to {control_topic}")
        
        # Subscribe to substation power response
        response_topic = topics.SUBSTATION_POWER_RESPONSE.format(device=self.bulb_id)
        client.subscribe(response_topic)
        print(f"[{self.bulb_id}] Subscribed to {response_topic}")
        
        # Subscribe to substation status for available power info
        client.subscribe("substation/status/#")
        print(f"[{self.bulb_id}] Subscribed to substation/status/#")
    
    def on_message(self, client, userdata, msg):
        topic = msg.topic
        payload = msg.payload.decode()
        
        if topic == topics.LIGHTBULB_CONTROL.format(bulb=self.bulb_id):
            if payload == "ON":
                # Request power from substation
                self.request_power_from_substation()
            elif payload == "OFF":
                self.state = "OFF"
                self.power_granted = False
                print(f"[{self.bulb_id}] Turned OFF")
            else:
                print(f"[{self.bulb_id}] Unknown command: {payload}")
        
        # Handle power response from substation
        elif topic == topics.SUBSTATION_POWER_RESPONSE.format(device=self.bulb_id):
            try:
                data = json.loads(payload)
                if data.get("granted", False):
                    self.power_granted = True
                    self.available_power_from_substation = data.get("available_power", 0.0)
                    if self.state != "ON":
                        self.state = "ON"
                        print(f"[{self.bulb_id}] Turned ON - power granted by substation (available: {self.available_power_from_substation:.2f} kW)")
                else:
                    self.power_granted = False
                    self.available_power_from_substation = data.get("available_power", 0.0)
                    if self.state == "ON":
                        self.state = "OFF"
                        print(f"[{self.bulb_id}] Auto-turned OFF - power denied by substation (available: {self.available_power_from_substation:.2f} kW, needed: {self.power_consumption:.2f} kW)")
                    else:
                        print(f"[{self.bulb_id}] Cannot turn ON - insufficient power at substation (available: {self.available_power_from_substation:.2f} kW, needed: {self.power_consumption:.2f} kW)")
            except:
                pass
        
        # Update available power from substation status
        elif topic.startswith("substation/status/"):
            try:
                data = json.loads(payload)
                self.available_power_from_substation = data.get("available_power", 0.0)
                
                # Check if we need to turn off due to insufficient power
                if self.state == "ON" and not self.power_granted:
                    # Re-request power
                    self.request_power_from_substation()
            except:
                pass
    
    def request_power_from_substation(self):
        """Request power from substation."""
        request = {
            "power_kw": self.power_consumption,
            "device_id": self.bulb_id
        }
        topic = topics.SUBSTATION_POWER_REQUEST.format(device=self.bulb_id)
        self.client.publish(topic, json.dumps(request))
        print(f"[{self.bulb_id}] Requested {self.power_consumption} kW from substation")
    
    def get_available_power(self):
        """Get available power from substation."""
        return self.available_power_from_substation
    
    def has_enough_power(self):
        """Check if there's enough power to turn on."""
        return self.available_power_from_substation >= self.power_consumption
    
    def get_power_consumption(self):
        """Get current power consumption in kW."""
        return self.power_consumption if self.state == "ON" else 0.0
    
    def get_status(self):
        """Get current status and power consumption."""
        return {
            "state": self.state,
            "power_kw": self.get_power_consumption(),
            "bulb_id": self.bulb_id
        }
    
    def run(self):
        """Main loop - publish status periodically and check power."""
        print(f"[{self.bulb_id}] Starting lightbulb loop...")
        while True:
            now = time.time()
            
            # Periodically re-request power if we're ON but not granted
            if now - self.last_power_check > 5:
                self.last_power_check = now
                
                # If we're ON but power wasn't granted, re-request
                if self.state == "ON" and not self.power_granted:
                    self.request_power_from_substation()
            
            if now - self.last_pub > 2:
                status = self.get_status()
                # Include power availability info from substation
                status["available_power"] = round(self.get_available_power(), 2)
                status["power_granted"] = self.power_granted
                self.client.publish(
                    topics.LIGHTBULB_STATUS.format(bulb=self.bulb_id),
                    json.dumps(status)
                )
                self.last_pub = now
            time.sleep(0.1)


if __name__ == "__main__":
    bulb = Lightbulb("bulb1", power_consumption=0.1)
    bulb.run()

