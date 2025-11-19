import paho.mqtt.client as mqtt
from config import topics


class CentralController:
    """
    Central controller that acts as a bridge between HMI and PLCs.
    - Subscribes to PLC messages and forwards to HMI
    - Subscribes to HMI commands and forwards to PLCs
    - All communication goes through MQTT
    """
    def __init__(self, broker="localhost"):
        self.client = mqtt.Client()
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message
        
        print("[CENTRAL] Connecting to broker...")
        self.client.connect(broker, 1883, 60)
        self.client.loop_start()


    def on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            # Subscribe to PLC messages (to forward to HMI)
            self.client.subscribe("plc/#")
            print("[CENTRAL] Subscribed to plc/#")
            
            # Subscribe to HMI commands (to forward to PLCs)
            self.client.subscribe("hmi/command/#")
            print("[CENTRAL] Subscribed to hmi/command/#")
            
            # Subscribe to lightbulb messages (to forward to HMI)
            self.client.subscribe("lightbulb/status/#")
            print("[CENTRAL] Subscribed to lightbulb/status/#")
            
            # Subscribe to HMI lightbulb commands (to forward to lightbulbs)
            self.client.subscribe("hmi/lightbulb/control/#")
            print("[CENTRAL] Subscribed to hmi/lightbulb/control/#")
            
            # Subscribe to substation messages (to forward to HMI)
            self.client.subscribe("substation/status/#")
            print("[CENTRAL] Subscribed to substation/status/#")
            
            # Subscribe to power requests/responses (pass through)
            self.client.subscribe("substation/power_request/#")
            self.client.subscribe("substation/power_response/#")
            print("[CENTRAL] Subscribed to substation/power_request/# and power_response/#")
        else:
            print(f"[CENTRAL] Failed to connect. Return code: {rc}")


    def on_message(self, client, userdata, msg):
        topic = msg.topic
        payload = msg.payload.decode()
        
        # Handle messages from PLCs - forward to HMI
        if topic.startswith("plc/"):
            parts = topic.split("/")
            if len(parts) >= 3:
                plc_id = parts[-1]
                msg_type = parts[-2]
                
                # Forward to HMI topics
                if msg_type == "status":
                    hmi_topic = topics.HMI_STATUS.format(plc=plc_id)
                    self.client.publish(hmi_topic, payload)
                    print(f"[CENTRAL] Forwarded PLC status: {topic} → {hmi_topic}")
                elif msg_type == "telemetry":
                    hmi_topic = topics.HMI_TELEMETRY.format(plc=plc_id)
                    self.client.publish(hmi_topic, payload)
                    print(f"[CENTRAL] Forwarded PLC telemetry: {topic} → {hmi_topic}")
                elif msg_type == "heartbeat":
                    hmi_topic = topics.HMI_HEARTBEAT.format(plc=plc_id)
                    self.client.publish(hmi_topic, payload)
                    print(f"[CENTRAL] Forwarded PLC heartbeat: {topic} → {hmi_topic}")
        
        # Handle messages from lightbulbs - forward to HMI
        elif topic.startswith("lightbulb/status/"):
            parts = topic.split("/")
            if len(parts) >= 3:
                bulb_id = parts[-1]
                # Forward to HMI topic
                hmi_topic = topics.HMI_LIGHTBULB_STATUS.format(bulb=bulb_id)
                self.client.publish(hmi_topic, payload)
                print(f"[CENTRAL] Forwarded lightbulb status: {topic} → {hmi_topic}")
        
        # Handle messages from HMI - forward to PLCs
        elif topic.startswith("hmi/command/"):
            parts = topic.split("/")
            if len(parts) >= 3:
                plc_id = parts[-1]
                # Forward command to PLC
                plc_topic = topics.CONTROL.format(plc=plc_id)
                self.client.publish(plc_topic, payload)
                print(f"[CENTRAL] Forwarded HMI command: {topic} → {plc_topic} ({payload})")
        
        # Handle messages from HMI - forward to lightbulbs
        elif topic.startswith("hmi/lightbulb/control/"):
            parts = topic.split("/")
            if len(parts) >= 4:
                bulb_id = parts[-1]
                # Forward command to lightbulb
                bulb_topic = topics.LIGHTBULB_CONTROL.format(bulb=bulb_id)
                self.client.publish(bulb_topic, payload)
                print(f"[CENTRAL] Forwarded HMI lightbulb command: {topic} → {bulb_topic} ({payload})")
        
        # Handle messages from substation - forward to HMI
        elif topic.startswith("substation/status/"):
            parts = topic.split("/")
            if len(parts) >= 3:
                substation_id = parts[-1]
                # Forward to HMI topic
                hmi_topic = topics.HMI_SUBSTATION_STATUS.format(substation=substation_id)
                self.client.publish(hmi_topic, payload)
                print(f"[CENTRAL] Forwarded substation status: {topic} → {hmi_topic} (payload: {payload[:100]})")
        
        # Pass through power requests and responses (devices communicate directly with substation)
        elif topic.startswith("substation/power_request/") or topic.startswith("substation/power_response/"):
            # These are passed through as-is (no forwarding needed, devices subscribe directly)
            pass


    def send(self, plc, command):
        """Legacy method for direct sending (for backwards compatibility)."""
        topic = topics.CONTROL.format(plc=plc)
        print(f"[CENTRAL] Sending {command} to {topic}")
        self.client.publish(topic, command)





if __name__ == "__main__":
    central = CentralController()
    central.send("plc1", "START")

