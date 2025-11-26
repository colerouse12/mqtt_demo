"""
Simple PLC Simulator for Buffer POC
Publishes test telemetry messages to MQTT that will be buffered
"""
import json
import time
import random
import paho.mqtt.client as mqtt


class SimplePLCSimulator:
    """Simple PLC simulator that publishes telemetry to MQTT"""
    
    def __init__(self, plc_id="plc1", broker="localhost", port=1883):
        self.plc_id = plc_id
        self.broker = broker
        self.port = port
        
        self.client = mqtt.Client()
        self.client.on_connect = self.on_connect
        
        print(f"[{plc_id}] Connecting to MQTT broker {broker}:{port}")
        self.client.connect(broker, port, 60)
        self.client.loop_start()
        
        self.running = True
        self.counter = 0
    
    def on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            print(f"[{self.plc_id}] ✓ Connected to MQTT broker")
        else:
            print(f"[{self.plc_id}] ✗ Connection failed with code {rc}")
    
    def publish_telemetry(self):
        """Publish a test telemetry message"""
        self.counter += 1
        
        # Create test data
        telemetry = {
            "plc_id": self.plc_id,
            "timestamp": int(time.time()),
            "sequence": self.counter,
            "voltage": round(240 + random.uniform(-5, 5), 2),
            "current": round(10 + random.uniform(-1, 1), 2),
            "power_kw": round(2.4 + random.uniform(-0.2, 0.2), 2),
            "status": "RUNNING" if self.counter % 10 != 0 else "WARNING"
        }
        
        topic = f"plc/telemetry/{self.plc_id}"
        payload = json.dumps(telemetry)
        
        result = self.client.publish(topic, payload, qos=1)
        
        if result.rc == mqtt.MQTT_ERR_SUCCESS:
            print(f"[{self.plc_id}] Published to {topic}: {telemetry['sequence']}")
        else:
            print(f"[{self.plc_id}] Failed to publish: {result.rc}")
    
    def run(self, interval=2.0):
        """Run the simulator, publishing every interval seconds"""
        print(f"[{self.plc_id}] Starting simulator (publishing every {interval}s)")
        print(f"[{self.plc_id}] Press Ctrl+C to stop")
        
        try:
            while self.running:
                self.publish_telemetry()
                time.sleep(interval)
        except KeyboardInterrupt:
            print(f"\n[{self.plc_id}] Stopping simulator...")
            self.client.loop_stop()
            self.client.disconnect()


if __name__ == "__main__":
    simulator = SimplePLCSimulator(plc_id="plc1")
    simulator.run(interval=2.0)  # Publish every 2 seconds

