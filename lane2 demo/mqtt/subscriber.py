"""
MQTT subscriber for Lane 2 Bridge
Receives MQTT messages, normalizes them, and writes to SQLite buffer
"""
import json
import logging
import paho.mqtt.client as mqtt
from typing import Callable, Optional, Union
from buffer.sqlite_buffer import enqueue_record

logger = logging.getLogger(__name__)


class MQTTSubscriber:
    """Subscribes to MQTT topics and buffers normalized data"""
    
    def __init__(self, broker: str = "localhost", port: int = 1883, 
                 topics: Optional[list[str]] = None, client_id: Optional[str] = None):
        """
        Initialize MQTT subscriber and connect (following mqtt_demo pattern)
        
        Args:
            broker: MQTT broker hostname
            port: MQTT broker port
            topics: Optional list of topics to subscribe to (can be set later)
            client_id: Optional client ID (auto-generated if None)
        """
        self.broker = broker
        self.port = port
        self.topics_to_subscribe = topics or []
        self.client = mqtt.Client(client_id=client_id)
        self.client.on_connect = self._on_connect
        self.client.on_message = self._on_mqtt_message
        self.connected = False
        self.last_message_time: Optional[float] = None
        
        # Connect immediately (following mqtt_demo pattern)
        logger.info(f"MQTT subscriber connecting to {broker}:{port}")
        try:
            self.client.connect(broker, port, 60)
            self.client.loop_start()
        except Exception as e:
            logger.error(f"Failed to connect MQTT subscriber: {e}")
            raise
    
    def _on_connect(self, client, userdata, flags, rc):
        """Internal callback for MQTT connection (following mqtt_demo pattern)"""
        if rc == 0:
            self.connected = True
            logger.info(f"MQTT subscriber connected to {self.broker}:{self.port}")
            # Subscribe to topics in on_connect (following mqtt_demo pattern)
            for topic in self.topics_to_subscribe:
                client.subscribe(topic, qos=1)
                logger.info(f"Subscribed to {topic}")
        else:
            logger.error(f"MQTT subscriber connection failed with code {rc}")
            self.connected = False
    
    def _on_mqtt_message(self, client, userdata, msg):
        """Internal callback for MQTT messages - converts to our format"""
        try:
            logger.debug(f"Received MQTT message on topic: {msg.topic}")
            self.on_message(msg.topic, msg.payload)
        except Exception as e:
            logger.error(f"Error processing MQTT message from {msg.topic}: {e}", exc_info=True)
    
    async def connect(self, broker: Optional[str] = None, port: Optional[int] = None):
        """
        Reconnect to MQTT broker (for async compatibility)
        
        Args:
            broker: Optional broker override (uses instance default if None)
            port: Optional port override (uses instance default if None)
        """
        # Already connected in __init__, but allow reconnection
        if broker:
            self.broker = broker
        if port:
            self.port = port
        
        if not self.connected:
            try:
                logger.info(f"MQTT subscriber reconnecting to {self.broker}:{self.port}")
                self.client.connect(self.broker, self.port, 60)
                self.client.loop_start()
            except Exception as e:
                logger.error(f"Failed to reconnect MQTT subscriber: {e}")
                raise
    
    async def subscribe(self, topics: list[str], callback: Optional[Callable] = None):
        """
        Add topics to subscription list (will subscribe on next connect)
        
        Args:
            topics: List of topic strings to subscribe to
            callback: Optional callback function for message handling (not used, we use on_message)
        """
        for topic in topics:
            if topic not in self.topics_to_subscribe:
                self.topics_to_subscribe.append(topic)
                # If already connected, subscribe immediately
                if self.connected:
                    result = self.client.subscribe(topic, qos=1)
                    if result[0] == mqtt.MQTT_ERR_SUCCESS:
                        logger.info(f"Subscribed to {topic}")
                    else:
                        logger.error(f"Failed to subscribe to {topic}: {result[0]}")
    
    def on_message(self, topic: str, payload: Union[bytes, str]):
        """
        Handle incoming MQTT message
        Normalizes payload and writes to SQLite buffer
        
        Args:
            topic: MQTT topic string
            payload: Message payload (bytes or string)
        """
        import time
        self.last_message_time = time.time()
        
        # Convert bytes to string if needed
        if isinstance(payload, bytes):
            payload_str = payload.decode('utf-8', errors='ignore')
        else:
            payload_str = str(payload)
        
        # Try to parse as JSON
        try:
            payload_dict = json.loads(payload_str)
            logger.debug(f"Parsed JSON payload from {topic}")
        except json.JSONDecodeError as e:
            # If parsing fails, wrap in a dict
            logger.warning(f"Failed to parse JSON from {topic}, wrapping as text: {e}")
            payload_dict = {"value": payload_str, "parse_error": True}
        
        # Normalize into dict structure
        normalized = {
            "topic": topic,
            "data": payload_dict,
            "received_at": int(time.time())
        }
        
        # Insert into SQLite buffer
        source = f"mqtt:{topic}"
        try:
            enqueue_record(source=source, payload=normalized)
            logger.info(f"✓ Buffered MQTT message from {topic} (payload length: {len(payload_str)}, keys: {list(payload_dict.keys())})")
        except Exception as e:
            logger.error(f"Failed to enqueue message from {topic}: {e}", exc_info=True)
    
    async def disconnect(self):
        """Disconnect from MQTT broker"""
        if self.connected:
            self.client.loop_stop()
            self.client.disconnect()
            self.connected = False
            self.subscribed_topics = []
            logger.info("MQTT subscriber disconnected")

