"""
Publishes JSON bundles to MQTT topics
"""
import json
import logging
import paho.mqtt.client as mqtt
from typing import Dict, Any, Optional, Union

logger = logging.getLogger(__name__)


class MQTTPublisher:
    """Publishes telemetry data to MQTT broker"""
    
    def __init__(self, broker: str = "localhost", port: int = 1883, client_id: Optional[str] = None):
        """
        Initialize MQTT publisher and connect (following mqtt_demo pattern)
        
        Args:
            broker: MQTT broker hostname
            port: MQTT broker port
            client_id: Optional client ID (auto-generated if None)
        """
        self.broker = broker
        self.port = port
        self.client = mqtt.Client(client_id=client_id)
        self.connected = False
        
        # Connect immediately (following mqtt_demo pattern)
        logger.info(f"MQTT publisher connecting to {broker}:{port}")
        try:
            self.client.connect(broker, port, 60)
            self.client.loop_start()
            self.connected = True
            logger.info(f"MQTT publisher connected to {broker}:{port}")
        except Exception as e:
            logger.error(f"Failed to connect MQTT publisher: {e}")
            self.connected = False
            # Don't raise - allow retry later
    
    def connect(self):
        """Reconnect to MQTT broker (for compatibility)"""
        if not self.connected:
            try:
                self.client.connect(self.broker, self.port, 60)
                self.client.loop_start()
                self.connected = True
                logger.info(f"MQTT publisher connected to {self.broker}:{self.port}")
            except Exception as e:
                logger.error(f"Failed to connect MQTT publisher: {e}")
                self.connected = False
                raise
    
    def disconnect(self):
        """Disconnect from MQTT broker"""
        if self.connected:
            self.client.loop_stop()
            self.client.disconnect()
            self.connected = False
            logger.info("MQTT publisher disconnected")
    
    async def publish_bundle(self, data: Dict[str, Any], topic: Optional[str] = None):
        """
        Publish data bundle to appropriate MQTT topics
        
        Args:
            data: Data dict to publish
            topic: Optional specific topic to publish to. If None, constructs topic from data.
        """
        if not self.connected:
            logger.warning("MQTT publisher not connected, attempting to connect...")
            self.connect()
        
        if topic is None:
            # Construct topic from data structure
            # Default topic for Modbus data
            if "device" in data and data.get("device") == "modbus":
                topic = "bridge/modbus/telemetry"
            else:
                topic = "bridge/telemetry"
        
        self.publish_json(topic, data)
    
    def publish_json(self, topic: str, payload: Dict[str, Any]):
        """
        Synchronous publish of JSON payload to MQTT topic
        
        Args:
            topic: MQTT topic string
            payload: Data dict to publish as JSON
        """
        if not self.connected:
            logger.warning("MQTT publisher not connected")
            return
        
        try:
            payload_str = json.dumps(payload)
            result = self.client.publish(topic, payload_str, qos=1)
            
            if result.rc != mqtt.MQTT_ERR_SUCCESS:
                logger.error(f"Failed to publish to {topic}: {result.rc}")
            else:
                logger.debug(f"Published to {topic}: {len(payload_str)} bytes")
        except Exception as e:
            logger.error(f"Error publishing to {topic}: {e}", exc_info=True)

