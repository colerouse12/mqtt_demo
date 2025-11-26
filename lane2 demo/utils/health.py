"""
Bridge health tracking and monitoring
Tracks uptime, last message times, buffer stats, and publishes health status
"""
import time
import logging
from typing import Dict, Any, Optional
from buffer.sqlite_buffer import get_buffer_depth

logger = logging.getLogger(__name__)


class HealthTracker:
    """Tracks bridge health metrics and publishes status"""
    
    def __init__(self):
        self.start_time = time.time()
        self.last_modbus_time: Optional[float] = None
        self.last_mqtt_time: Optional[float] = None
        self.last_sql_forward_time: Optional[float] = None
        self.modbus_ok = False
        self.mqtt_ok = False
        self.sql_ok = False
    
    def update_modbus_status(self, last_message_time: Optional[float]):
        """Update Modbus health status"""
        self.last_modbus_time = last_message_time
        if last_message_time:
            # Consider Modbus healthy if we received a message in the last 60 seconds
            self.modbus_ok = (time.time() - last_message_time) < 60.0
        else:
            self.modbus_ok = False
    
    def update_mqtt_status(self, last_message_time: Optional[float]):
        """Update MQTT health status"""
        self.last_mqtt_time = last_message_time
        if last_message_time:
            # Consider MQTT healthy if we received a message in the last 60 seconds
            self.mqtt_ok = (time.time() - last_message_time) < 60.0
        else:
            self.mqtt_ok = False
    
    def update_sql_forward_status(self, last_forward_time: Optional[float]):
        """Update SQL forwarding health status"""
        self.last_sql_forward_time = last_forward_time
        if last_forward_time:
            # Consider SQL forwarding healthy if we attempted forwarding in the last 60 seconds
            self.sql_ok = (time.time() - last_forward_time) < 60.0
        else:
            self.sql_ok = False
    
    def get_health_status(self) -> Dict[str, Any]:
        """
        Get current health status as a dict
        
        Returns:
            Dict with health metrics: ts, modbus_ok, mqtt_ok, sql_ok, buffer_rows, uptime_s
        """
        uptime_s = int(time.time() - self.start_time)
        
        # Get buffer depth
        buffer_rows = get_buffer_depth()
        
        return {
            "ts": int(time.time()),
            "modbus_ok": self.modbus_ok,
            "mqtt_ok": self.mqtt_ok,
            "sql_ok": self.sql_ok,
            "buffer_rows": buffer_rows,
            "uptime_s": uptime_s,
            "last_modbus_ts": int(self.last_modbus_time) if self.last_modbus_time else None,
            "last_mqtt_ts": int(self.last_mqtt_time) if self.last_mqtt_time else None,
            "last_sql_forward_ts": int(self.last_sql_forward_time) if self.last_sql_forward_time else None
        }
    
    async def publish_health(self, mqtt_publisher, plant: str = "default"):
        """
        Publish health status to MQTT
        
        Args:
            mqtt_publisher: MQTTPublisher instance
            plant: Plant identifier for topic construction
        """
        try:
            health_status = self.get_health_status()
            topic = f"site/{plant}/bridge/health"
            
            # Publish health status to specific topic
            await mqtt_publisher.publish_bundle(health_status, topic=topic)
            
            logger.debug(f"Published health status to {topic}: {health_status}")
            
        except Exception as e:
            logger.error(f"Error publishing health status: {e}", exc_info=True)

