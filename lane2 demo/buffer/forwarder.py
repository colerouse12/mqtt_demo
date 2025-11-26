"""
Reads telemetry from SQLite buffer and forwards to MQTT.
Keeps 30-minute backlog for reinjection if downstream systems go down.
"""
import time
import logging
from buffer.sqlite_buffer import (
    dequeue_batch,
    mark_forwarded,
    prune_older_than,
    get_buffer_depth
)

logger = logging.getLogger(__name__)


class BufferForwarder:
    """Forwards buffer rows to MQTT but keeps them for 30 minutes for reinjection."""
    
    def __init__(self, mqtt_publisher, retention_seconds: int = 1800):
        """
        Initialize buffer forwarder
        
        Args:
            mqtt_publisher: MQTTPublisher instance
            retention_seconds: How long to keep rows in buffer (default: 1800 = 30 minutes)
        """
        self.mqtt = mqtt_publisher
        self.retention_seconds = retention_seconds  # 30 minutes = 1800 seconds
        self.last_forward = None
        self.last_cleanup = None
    
    def flush_once(self, batch_size: int = 100):
        """Pull up to batch_size unforwarded rows and forward them to MQTT (but keep in buffer)."""
        self.last_forward = time.time()
        
        # Only get rows that haven't been forwarded yet
        rows = dequeue_batch(batch_size, only_unforwarded=True)
        if not rows:
            return
        
        successful_ids = []
        forwarded_count = 0
        
        for row in rows:
            try:
                # Forward to MQTT with bridge/ prefix
                # This ensures HMI only receives data that went through the buffer
                topic = f"bridge/{row['source']}"
                payload = row["payload"]
                
                # Publish to MQTT - this is the ONLY way data reaches the HMI
                self.mqtt.publish_json(topic, payload)
                
                logger.info(f"Forwarded buffer row {row['id']} to {topic} (will mark as forwarded)")
                successful_ids.append(row["id"])
                forwarded_count += 1
            except Exception as e:
                logger.error(f"Failed to forward row {row['id']}: {e}")
        
        # Mark as forwarded (but keep in buffer for 30 minutes)
        if successful_ids:
            mark_forwarded(successful_ids)
            logger.info(f"Marked {forwarded_count} rows as forwarded (kept in buffer for {self.retention_seconds}s retention)")
    
    def periodic_cleanup(self):
        """Remove rows older than retention period (30 minutes)."""
        prune_older_than(self.retention_seconds)
        depth = get_buffer_depth()
        self.last_cleanup = time.time()
        logger.info(f"Buffer cleanup: removed rows older than {self.retention_seconds}s, current depth: {depth}")
