"""
PySide6 GUI to display messages forwarded from SQLite buffer
Subscribes to bridge/# topics to see forwarded messages
"""
import json
import sys
from datetime import datetime
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QTextEdit, QPushButton, QStatusBar
)
from PySide6.QtCore import Qt, QThread, Signal
import paho.mqtt.client as mqtt


class MQTTThread(QThread):
    """Thread for MQTT operations to avoid blocking GUI"""
    message_received = Signal(str, str)  # topic, payload
    status_changed = Signal(str, bool)  # status message, is_connected
    
    def __init__(self, broker="localhost", port=1883):
        super().__init__()
        self.broker = broker
        self.port = port
        self.client = None
        self.running = True
    
    def run(self):
        """Run MQTT client in background thread"""
        self.client = mqtt.Client()
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message
        
        try:
            self.client.connect(self.broker, self.port, 60)
            self.client.loop_start()
            
            # Keep thread alive
            while self.running:
                self.msleep(100)
        except Exception as e:
            self.status_changed.emit(f"Connection error: {e}", False)
    
    def on_connect(self, client, userdata, flags, rc):
        """Callback when MQTT connects"""
        if rc == 0:
            client.subscribe("bridge/#", qos=1)
            self.status_changed.emit("Connected - Subscribed to bridge/#", True)
        else:
            self.status_changed.emit(f"Connection failed: {rc}", False)
    
    def on_message(self, client, userdata, msg):
        """Callback when MQTT message received"""
        try:
            topic = msg.topic
            payload = msg.payload.decode('utf-8')
            self.message_received.emit(topic, payload)
        except Exception as e:
            self.message_received.emit("ERROR", f"Error processing message: {e}")
    
    def stop(self):
        """Stop MQTT client"""
        self.running = False
        if self.client:
            self.client.loop_stop()
            self.client.disconnect()


class BufferGUI(QMainWindow):
    """Main GUI window for displaying forwarded buffer messages"""
    
    def __init__(self):
        super().__init__()
        self.message_count = 0
        self.mqtt_thread = None
        self.init_ui()
        self.connect_mqtt()
    
    def init_ui(self):
        """Initialize the UI"""
        self.setWindowTitle("SQLite Buffer Monitor - Lane 2 POC")
        self.setGeometry(100, 100, 1000, 700)
        
        # Central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        
        # Header
        header_layout = QHBoxLayout()
        
        self.status_label = QLabel("Connecting...")
        self.status_label.setStyleSheet("font-weight: bold; font-size: 12pt; padding: 5px;")
        header_layout.addWidget(self.status_label)
        
        self.count_label = QLabel("Messages: 0")
        self.count_label.setStyleSheet("font-size: 10pt; padding: 5px;")
        header_layout.addWidget(self.count_label)
        
        header_layout.addStretch()
        
        clear_btn = QPushButton("Clear")
        clear_btn.clicked.connect(self.clear_messages)
        header_layout.addWidget(clear_btn)
        
        layout.addLayout(header_layout)
        
        # Messages display
        messages_label = QLabel("Forwarded Messages from Buffer:")
        messages_label.setStyleSheet("font-weight: bold; font-size: 11pt;")
        layout.addWidget(messages_label)
        
        self.messages_text = QTextEdit()
        self.messages_text.setReadOnly(True)
        self.messages_text.setFontFamily("Consolas")
        self.messages_text.setFontPointSize(9)
        layout.addWidget(self.messages_text)
        
        # Info label
        info_label = QLabel(
            "✓ Subscribed ONLY to bridge/# topics\n"
            "This GUI receives data ONLY from the buffer forwarder, not directly from PLCs"
        )
        info_label.setStyleSheet("color: gray; font-size: 8pt; padding: 5px;")
        layout.addWidget(info_label)
        
        # Status bar
        self.statusBar().showMessage("Ready")
    
    def connect_mqtt(self):
        """Connect to MQTT broker in background thread"""
        self.mqtt_thread = MQTTThread(broker="localhost", port=1883)
        self.mqtt_thread.message_received.connect(self.on_message_received)
        self.mqtt_thread.status_changed.connect(self.on_status_changed)
        self.mqtt_thread.start()
    
    def on_status_changed(self, message, is_connected):
        """Handle status changes from MQTT thread"""
        if is_connected:
            self.status_label.setText(f"✓ {message}")
            self.status_label.setStyleSheet(
                "font-weight: bold; font-size: 12pt; padding: 5px; color: green;"
            )
        else:
            self.status_label.setText(f"✗ {message}")
            self.status_label.setStyleSheet(
                "font-weight: bold; font-size: 12pt; padding: 5px; color: red;"
            )
        self.statusBar().showMessage(message)
    
    def on_message_received(self, topic, payload):
        """Handle incoming MQTT message - ONLY from buffer forwarder"""
        self.message_count += 1
        self.count_label.setText(f"Messages: {self.message_count}")
        
        # Verify this is from the forwarder (should start with "bridge/")
        if not topic.startswith("bridge/"):
            self.messages_text.append(
                f"⚠ WARNING: Received message from non-forwarder topic: {topic}\n"
                f"This should only receive messages from bridge/# topics!\n"
                + "-" * 80 + "\n\n"
            )
            return
        
        # Try to format as JSON
        try:
            payload_dict = json.loads(payload)
            payload_formatted = json.dumps(payload_dict, indent=2)
        except json.JSONDecodeError:
            payload_formatted = payload
        
        # Add to display with clear indication it came from forwarder
        timestamp = datetime.now().strftime("%H:%M:%S")
        message = f"[{timestamp}] ✓ FROM FORWARDER\n"
        message += f"Topic: {topic}\n"
        message += f"Source: {topic.replace('bridge/', '')}\n"
        message += f"Payload:\n{payload_formatted}\n"
        message += "-" * 80 + "\n\n"
        
        self.messages_text.append(message)
        
        # Auto-scroll to bottom
        scrollbar = self.messages_text.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())
        
        # Update status
        self.statusBar().showMessage(f"Received forwarded message #{self.message_count} from buffer")
    
    def clear_messages(self):
        """Clear message display"""
        self.messages_text.clear()
        self.message_count = 0
        self.count_label.setText("Messages: 0")
    
    def closeEvent(self, event):
        """Cleanup on close"""
        if self.mqtt_thread:
            self.mqtt_thread.stop()
            self.mqtt_thread.wait()
        event.accept()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    window = BufferGUI()
    window.show()
    
    print("Buffer GUI started. Waiting for messages from buffer forwarder...")
    print("Make sure the bridge service (main.py) is running!")
    
    sys.exit(app.exec())

