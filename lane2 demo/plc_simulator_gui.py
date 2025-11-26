"""
PySide6 Simple PLC Simulator GUI
Allows manual input of test strings to send to MQTT
"""
import json
import sys
import time
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QPushButton, QTextEdit, QGroupBox, QStatusBar
)
from PySide6.QtCore import Qt
import paho.mqtt.client as mqtt


class PLCSimulatorGUI(QMainWindow):
    """Simple GUI for simulating PLC messages"""
    
    def __init__(self):
        super().__init__()
        self.plc_id = "plc1"
        self.broker = "localhost"
        self.port = 1883
        self.client = None
        self.message_count = 0
        self.init_ui()
        self.connect_mqtt()
    
    def init_ui(self):
        """Initialize the UI"""
        self.setWindowTitle("PLC Simulator - Lane 2 POC")
        self.setGeometry(200, 200, 600, 500)
        
        # Central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        
        # Connection status
        self.status_label = QLabel("Connecting...")
        self.status_label.setStyleSheet("font-weight: bold; font-size: 11pt; padding: 5px;")
        layout.addWidget(self.status_label)
        
        # Input group
        input_group = QGroupBox("Send Test Message")
        input_layout = QVBoxLayout()
        
        # PLC ID input
        plc_layout = QHBoxLayout()
        plc_layout.addWidget(QLabel("PLC ID:"))
        self.plc_id_input = QLineEdit(self.plc_id)
        plc_layout.addWidget(self.plc_id_input)
        input_layout.addLayout(plc_layout)
        
        # Message input
        input_layout.addWidget(QLabel("Message (JSON or plain text - both work!):"))
        self.message_input = QTextEdit()
        self.message_input.setPlaceholderText(
            'You can type:\n'
            '  - JSON: {"voltage": 240, "current": 10.5}\n'
            '  - Plain text: test message\n'
            'Both will be sent as JSON automatically'
        )
        self.message_input.setMaximumHeight(100)
        input_layout.addWidget(self.message_input)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        send_json_btn = QPushButton("Send as JSON")
        send_json_btn.clicked.connect(self.send_as_json)
        button_layout.addWidget(send_json_btn)
        
        send_text_btn = QPushButton("Send as Text")
        send_text_btn.clicked.connect(self.send_as_text)
        button_layout.addWidget(send_text_btn)
        
        send_auto_btn = QPushButton("Auto Send (2s)")
        send_auto_btn.clicked.connect(self.toggle_auto_send)
        self.auto_send_active = False
        self.auto_send_btn = send_auto_btn
        button_layout.addWidget(send_auto_btn)
        
        input_layout.addLayout(button_layout)
        input_group.setLayout(input_layout)
        layout.addWidget(input_group)
        
        # Sent messages log
        log_label = QLabel("Sent Messages:")
        log_label.setStyleSheet("font-weight: bold; font-size: 11pt;")
        layout.addWidget(log_label)
        
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setFontFamily("Consolas")
        self.log_text.setFontPointSize(9)
        self.log_text.setMaximumHeight(200)
        layout.addWidget(self.log_text)
        
        # Clear button
        clear_btn = QPushButton("Clear Log")
        clear_btn.clicked.connect(self.clear_log)
        layout.addWidget(clear_btn)
        
        # Status bar
        self.statusBar().showMessage("Ready")
    
    def connect_mqtt(self):
        """Connect to MQTT broker"""
        self.client = mqtt.Client()
        self.client.on_connect = self.on_connect
        
        try:
            self.client.connect(self.broker, self.port, 60)
            self.client.loop_start()
        except Exception as e:
            self.status_label.setText(f"✗ Connection error: {e}")
            self.status_label.setStyleSheet(
                "font-weight: bold; font-size: 11pt; padding: 5px; color: red;"
            )
    
    def on_connect(self, client, userdata, flags, rc):
        """Callback when MQTT connects"""
        if rc == 0:
            self.status_label.setText(f"✓ Connected to {self.broker}:{self.port}")
            self.status_label.setStyleSheet(
                "font-weight: bold; font-size: 11pt; padding: 5px; color: green;"
            )
            self.statusBar().showMessage("Connected to MQTT broker")
        else:
            self.status_label.setText(f"✗ Connection failed: {rc}")
            self.status_label.setStyleSheet(
                "font-weight: bold; font-size: 11pt; padding: 5px; color: red;"
            )
    
    def get_plc_id(self):
        """Get current PLC ID from input"""
        return self.plc_id_input.text().strip() or self.plc_id
    
    def send_message(self, payload_str, is_json=False):
        """Send message to MQTT"""
        if not self.client:
            self.log_text.append("ERROR: Not connected to MQTT broker\n")
            return
        
        plc_id = self.get_plc_id()
        topic = f"plc/telemetry/{plc_id}"
        
        try:
            # Wait for publish to complete
            result = self.client.publish(topic, payload_str, qos=1)
            
            # Wait for the publish to complete (important for qos=1)
            result.wait_for_publish(timeout=2.0)
            
            if result.rc == mqtt.MQTT_ERR_SUCCESS:
                self.message_count += 1
                msg_type = "JSON" if is_json else "TEXT"
                timestamp = time.strftime("%H:%M:%S")
                self.log_text.append(
                    f"[{timestamp}] #{self.message_count} - {msg_type} to {topic}\n"
                    f"Payload: {payload_str[:100]}{'...' if len(payload_str) > 100 else ''}\n"
                    + "-" * 60 + "\n"
                )
                
                # Auto-scroll
                scrollbar = self.log_text.verticalScrollBar()
                scrollbar.setValue(scrollbar.maximum())
                
                self.statusBar().showMessage(f"Sent message #{self.message_count} to {topic}")
                print(f"[PLC Simulator] Published to {topic}: {payload_str[:50]}...")  # Debug output
            else:
                error_msg = f"ERROR: Failed to publish (code: {result.rc})\n"
                self.log_text.append(error_msg)
                print(f"[PLC Simulator] {error_msg}")
        except Exception as e:
            error_msg = f"ERROR: {e}\n"
            self.log_text.append(error_msg)
            print(f"[PLC Simulator] {error_msg}")
            import traceback
            traceback.print_exc()
    
    def send_as_json(self):
        """Send message as JSON"""
        text = self.message_input.toPlainText().strip()
        if not text:
            self.log_text.append("ERROR: Message is empty\n")
            return
        
        # Try to parse as JSON first
        try:
            # If it's already valid JSON, use it
            json.loads(text)
            payload = text
            is_json = True
        except json.JSONDecodeError:
            # If not, wrap it in a JSON object
            payload = json.dumps({"message": text, "timestamp": int(time.time())})
            is_json = True
        
        self.send_message(payload, is_json=True)
    
    def send_as_text(self):
        """Send message as plain text (wrapped in JSON for consistency)"""
        text = self.message_input.toPlainText().strip()
        if not text:
            self.log_text.append("ERROR: Message is empty\n")
            return
        
        # Wrap plain text in JSON for consistency with auto-send
        # This ensures the subscriber receives it in the same format
        payload = json.dumps({"message": text, "timestamp": int(time.time()), "type": "text"})
        self.send_message(payload, is_json=True)
    
    def toggle_auto_send(self):
        """Toggle automatic sending every 2 seconds"""
        if not self.auto_send_active:
            # Start auto-send
            self.auto_send_active = True
            self.auto_send_btn.setText("Stop Auto Send")
            self.auto_send_btn.setStyleSheet("background-color: #f44336; color: white;")
            self.start_auto_send()
        else:
            # Stop auto-send
            self.auto_send_active = False
            self.auto_send_btn.setText("Auto Send (2s)")
            self.auto_send_btn.setStyleSheet("")
    
    def start_auto_send(self):
        """Start automatic sending"""
        if self.auto_send_active:
            # Create a simple auto-incrementing message
            import random
            auto_message = json.dumps({
                "plc_id": self.get_plc_id(),
                "sequence": self.message_count + 1,
                "timestamp": int(time.time()),
                "voltage": round(240 + random.uniform(-5, 5), 2),
                "current": round(10 + random.uniform(-1, 1), 2),
                "auto": True
            })
            self.message_input.setPlainText(auto_message)
            self.send_as_json()
            
            # Schedule next send
            from PySide6.QtCore import QTimer
            QTimer.singleShot(2000, self.start_auto_send)
    
    def clear_log(self):
        """Clear the log"""
        self.log_text.clear()
        self.message_count = 0
    
    def closeEvent(self, event):
        """Cleanup on close"""
        if self.client:
            self.client.loop_stop()
            self.client.disconnect()
        event.accept()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    window = PLCSimulatorGUI()
    window.show()
    
    print("PLC Simulator GUI started.")
    print("Enter a message and click 'Send as JSON' or 'Send as Text'")
    print("Or use 'Auto Send' to automatically send test messages every 2 seconds")
    
    sys.exit(app.exec())

