"""
Bridge Service - Lane 2 (Simplified POC)
Proof of concept: MQTT → SQLite Buffer → Forwarder → MQTT → GUI
Keeps 30-minute backlog for reinjection.
"""
import time
import logging
from mqtt.publisher import MQTTPublisher
from mqtt.subscriber import MQTTSubscriber
from buffer.forwarder import BufferForwarder
from buffer.sqlite_buffer import init_db

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def main():
    """Main bridge service loop - simplified POC"""
    # Initialize SQLite buffer
    init_db()
    logger.info("✓ SQLite buffer initialized")
    
    # MQTT publisher connects automatically in __init__
    publisher = MQTTPublisher()
    logger.info("✓ MQTT publisher initialized")
    
    # MQTT subscriber connects automatically and subscribes to PLC telemetry
    subscriber = MQTTSubscriber(
        topics=[
            "plc/telemetry/#",  # Subscribe to PLC simulator messages
        ]
    )
    logger.info("✓ MQTT subscriber initialized and subscribed")
    
    # Buffer forwarder with 30-minute retention (1800 seconds)
    RETENTION_SECONDS = 1800  # 30 minutes
    forwarder = BufferForwarder(mqtt_publisher=publisher, retention_seconds=RETENTION_SECONDS)
    logger.info(f"✓ Buffer forwarder initialized (30-minute retention: {RETENTION_SECONDS}s)")
    
    logger.info("=" * 60)
    logger.info("Bridge service running - Proof of Concept")
    logger.info("Flow: PLC → MQTT → Buffer → Forwarder → MQTT → GUI")
    logger.info(f"Buffer retention: {RETENTION_SECONDS}s (30 minutes) for reinjection")
    logger.info("=" * 60)
    
    # Main polling loop
    last_status_log = time.time()
    last_cleanup = time.time()
    status_interval = 5.0  # Log status every 5 seconds
    cleanup_interval = 300.0  # Run cleanup every 5 minutes
    
    try:
        while True:
            current_time = time.time()
            
            # Forward buffered records from SQLite to MQTT (keeps them in buffer)
            forwarder.flush_once(batch_size=100)
            
            # Periodic cleanup - remove rows older than 30 minutes
            if current_time - last_cleanup >= cleanup_interval:
                forwarder.periodic_cleanup()
                last_cleanup = current_time
            
            # Log status periodically
            if current_time - last_status_log >= status_interval:
                from buffer.sqlite_buffer import get_buffer_depth
                depth = get_buffer_depth()
                logger.info(f"Status - Buffer depth: {depth} | MQTT messages received: {subscriber.last_message_time is not None}")
                last_status_log = current_time
            
            time.sleep(0.5)  # Polling interval
            
    except KeyboardInterrupt:
        logger.info("Shutting down...")
    except Exception as e:
        logger.error(f"Bridge error: {e}", exc_info=True)


if __name__ == "__main__":
    main()

