"""
Simple HMI GUI using PySide6 for monitoring and controlling PLCs via MQTT.
"""
import json
import sys
from datetime import datetime
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QTextEdit, QGroupBox, QGridLayout, QSlider,
    QTabWidget, QDockWidget
)
from PySide6.QtCore import Qt, QTimer, QObject, Signal
from PySide6.QtGui import QFont, QPainter, QColor, QPen, QBrush
import paho.mqtt.client as mqtt
from config import topics


class MQTTMessageHandler(QObject):
    """Helper class to safely handle MQTT messages in Qt main thread."""
    message_received = Signal(str, str, str)  # device_id, msg_type, payload
    lightbulb_message = Signal(str, str)  # bulb_id, payload
    
    def __init__(self):
        super().__init__()
        self.plc_panels = {}
        self.lightbulb_states = {}
    
    def handle_message(self, device_id, msg_type, payload):
        """Handle message in main thread."""
        if device_id in self.plc_panels:
            panel = self.plc_panels[device_id]
            if msg_type == "status":
                panel.update_status(payload)
            elif msg_type == "heartbeat":
                panel.update_heartbeat(payload)
            elif msg_type == "telemetry":
                panel.update_telemetry(payload)


class PLCPanel(QGroupBox):
    """Panel for displaying and controlling a single PLC."""
    def __init__(self, plc_id, mqtt_client):
        super().__init__(f"PLC: {plc_id.upper()}")
        self.plc_id = plc_id
        self.mqtt_client = mqtt_client
        
        # Data storage
        self.status = "UNKNOWN"
        self.heartbeat = "No heartbeat"
        self.telemetry = {}
        self.current_kw_setpoint = 0.0
        
        # Layout
        layout = QVBoxLayout()
        
        # Status display
        self.status_label = QLabel("Status: UNKNOWN")
        self.status_label.setStyleSheet("font-size: 14px; font-weight: bold; padding: 5px;")
        layout.addWidget(self.status_label)
        
        # Fuel level display
        self.fuel_label = QLabel("Fuel: --/-- L")
        self.fuel_label.setStyleSheet("font-size: 13px; font-weight: bold; padding: 5px; background-color: #E3F2FD;")
        layout.addWidget(self.fuel_label)
        
        # kW Output display
        self.kw_label = QLabel("Output: 0.0 kW")
        self.kw_label.setStyleSheet("font-size: 13px; font-weight: bold; padding: 5px;")
        layout.addWidget(self.kw_label)
        
        # kW Setpoint slider
        slider_layout = QVBoxLayout()
        slider_label = QLabel("kW Setpoint:")
        slider_label.setStyleSheet("font-size: 12px; font-weight: bold;")
        slider_layout.addWidget(slider_label)
        
        slider_hbox = QHBoxLayout()
        self.kw_slider = QSlider(Qt.Horizontal)
        self.kw_slider.setMinimum(0)
        self.kw_slider.setMaximum(500)
        self.kw_slider.setValue(0)
        self.kw_slider.setTickPosition(QSlider.TicksBelow)
        self.kw_slider.setTickInterval(50)
        self.kw_slider.valueChanged.connect(self.on_slider_changed)
        slider_hbox.addWidget(self.kw_slider)
        
        self.kw_value_label = QLabel("0")
        self.kw_value_label.setMinimumWidth(40)
        self.kw_value_label.setStyleSheet("font-weight: bold; font-size: 12px;")
        slider_hbox.addWidget(self.kw_value_label)
        slider_layout.addLayout(slider_hbox)
        layout.addLayout(slider_layout)
        
        # Heartbeat display
        self.heartbeat_label = QLabel("Heartbeat: No heartbeat")
        self.heartbeat_label.setStyleSheet("font-size: 12px; padding: 3px;")
        layout.addWidget(self.heartbeat_label)
        
        # Telemetry display (for other data)
        self.telemetry_label = QLabel("Other: No data")
        self.telemetry_label.setStyleSheet("font-size: 11px; padding: 3px;")
        self.telemetry_label.setWordWrap(True)
        layout.addWidget(self.telemetry_label)
        
        # Toggle ON/OFF button
        self.toggle_btn = QPushButton("TURN ON")
        self.toggle_btn.setStyleSheet("background-color: #4CAF50; color: white; font-weight: bold; padding: 10px; font-size: 14px;")
        self.toggle_btn.clicked.connect(self.toggle_plc)
        layout.addWidget(self.toggle_btn)
        
        # Control buttons
        button_layout = QHBoxLayout()
        
        self.start_btn = QPushButton("START")
        self.start_btn.setStyleSheet("background-color: #4CAF50; color: white; font-weight: bold; padding: 8px;")
        self.start_btn.clicked.connect(lambda: self.send_command("START"))
        button_layout.addWidget(self.start_btn)
        
        self.stop_btn = QPushButton("STOP")
        self.stop_btn.setStyleSheet("background-color: #f44336; color: white; font-weight: bold; padding: 8px;")
        self.stop_btn.clicked.connect(lambda: self.send_command("STOP"))
        button_layout.addWidget(self.stop_btn)
        
        self.reset_btn = QPushButton("RESET")
        self.reset_btn.setStyleSheet("background-color: #FF9800; color: white; font-weight: bold; padding: 8px;")
        self.reset_btn.clicked.connect(lambda: self.send_command("RESET"))
        button_layout.addWidget(self.reset_btn)
        
        layout.addLayout(button_layout)
        self.setLayout(layout)
        
        self.update_display()
    
    def send_command(self, command):
        """Send command to PLC via Central Controller (MQTT)."""
        topic = topics.HMI_COMMAND.format(plc=self.plc_id)
        self.mqtt_client.publish(topic, command)
        print(f"[HMI] Sent {command} to central controller via {topic}")
        
        # If RESET command, also reset the slider
        if command == "RESET":
            self.kw_slider.blockSignals(True)
            self.kw_slider.setValue(0)
            self.kw_value_label.setText("0")
            self.current_kw_setpoint = 0.0
            self.kw_slider.blockSignals(False)
    
    def toggle_plc(self):
        """Toggle PLC ON/OFF state."""
        if self.status == "RUNNING":
            self.send_command("STOP")
        else:
            self.send_command("START")
    
    def on_slider_changed(self, value):
        """Handle kW slider value change."""
        self.current_kw_setpoint = float(value)
        self.kw_value_label.setText(str(value))
        # Send setpoint command via central controller
        topic = topics.HMI_COMMAND.format(plc=self.plc_id)
        command = f"SETPOINT:{value}"
        self.mqtt_client.publish(topic, command)
        print(f"[HMI] Sent setpoint {value} kW to central controller via {topic}")
    
    def update_status(self, status):
        """Update PLC status."""
        self.status = status
        self.update_display()
    
    def update_heartbeat(self, heartbeat):
        """Update heartbeat timestamp."""
        self.heartbeat = datetime.now().strftime("%H:%M:%S")
        self.update_display()
    
    def update_telemetry(self, telemetry_data):
        """Update telemetry data."""
        try:
            if isinstance(telemetry_data, str):
                self.telemetry = json.loads(telemetry_data)
            else:
                self.telemetry = telemetry_data
        except:
            self.telemetry = {}
        self.update_display()
    
    def update_display(self):
        """Update all display elements."""
        # Status with color coding
        status_color = "#4CAF50" if self.status == "RUNNING" else "#f44336" if self.status == "STOPPED" else "#757575"
        self.status_label.setText(f"Status: <span style='color: {status_color};'>{self.status}</span>")
        
        # Update toggle button based on status
        if self.status == "RUNNING":
            self.toggle_btn.setText("TURN OFF")
            self.toggle_btn.setStyleSheet("background-color: #f44336; color: white; font-weight: bold; padding: 10px; font-size: 14px;")
        else:
            self.toggle_btn.setText("TURN ON")
            self.toggle_btn.setStyleSheet("background-color: #4CAF50; color: white; font-weight: bold; padding: 10px; font-size: 14px;")
        
        # Fuel level display
        fuel_level = self.telemetry.get("fuel_level", 0)
        fuel_max = self.telemetry.get("fuel_max", 100)
        fuel_percent = (fuel_level / fuel_max * 100) if fuel_max > 0 else 0
        
        # Color code fuel level (green >50%, yellow >20%, red <=20%)
        if fuel_percent > 50:
            fuel_color = "#4CAF50"
        elif fuel_percent > 20:
            fuel_color = "#FF9800"
        else:
            fuel_color = "#f44336"
        
        self.fuel_label.setText(f"Fuel: <span style='color: {fuel_color}; font-weight: bold;'>{fuel_level:.1f}/{fuel_max:.0f} L</span> ({fuel_percent:.0f}%)")
        
        # kW Output display
        kw_output = self.telemetry.get("kw", 0.0)
        target_kw = self.telemetry.get("target_kw", 0.0)
        self.kw_label.setText(f"Output: <span style='font-weight: bold;'>{kw_output:.1f} kW</span> (Target: {target_kw:.1f} kW)")
        
        # Update slider to match target_kw if it changed externally
        if "target_kw" in self.telemetry:
            target = int(self.telemetry["target_kw"])
            if self.kw_slider.value() != target:
                self.kw_slider.blockSignals(True)
                self.kw_slider.setValue(target)
                self.kw_value_label.setText(str(target))
                self.kw_slider.blockSignals(False)
        
        # Heartbeat
        self.heartbeat_label.setText(f"Heartbeat: {self.heartbeat}")
        
        # Other telemetry (fuel consumption, etc.)
        other_data = {}
        for k, v in self.telemetry.items():
            if k not in ["kw", "target_kw", "fuel_level", "fuel_max", "hz"]:
                other_data[k] = v
        
        if other_data:
            other_str = ", ".join([f"{k}: {v}" for k, v in other_data.items()])
            self.telemetry_label.setText(f"Other: {other_str}")
        else:
            self.telemetry_label.setText("Other: No data")


class SiteDiagramWidget(QWidget):
    """Widget showing a site diagram with generators, substation, and lightbulbs."""
    def __init__(self, mqtt_client, generator_data, lightbulb_data, substation_data):
        super().__init__()
        self.mqtt_client = mqtt_client
        self.generator_data = generator_data  # {plc_id: {status, kw, fuel, ...}}
        self.lightbulb_data = lightbulb_data  # {bulb_id: {state, power_kw}}
        self.substation_data = substation_data  # {substation_id: {total_generated, total_consumption, available, ...}}
        self.setMinimumSize(800, 600)
        self.setStyleSheet("background-color: #F5F5F5;")
    
    def paintEvent(self, event):
        """Draw the site diagram."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        width = self.width()
        height = self.height()
        
        # Draw title
        painter.setFont(QFont("Arial", 16, QFont.Bold))
        painter.drawText(width // 2 - 100, 30, "Site Diagram")
        
        # Draw generators (left side)
        gen_y = 100
        gen_spacing = 150
        for i, (plc_id, data) in enumerate(self.generator_data.items()):
            x = 100
            y = gen_y + i * gen_spacing
            
            # Generator box
            status = data.get("status", "UNKNOWN")
            kw = data.get("kw", 0.0)
            fuel = data.get("fuel_level", 0.0)
            fuel_max = data.get("fuel_max", 100.0)
            
            # Color based on status
            if status == "RUNNING":
                color = QColor(76, 175, 80)  # Green
            elif status == "STOPPED":
                color = QColor(244, 67, 54)  # Red
            else:
                color = QColor(158, 158, 158)  # Gray
            
            painter.setBrush(QBrush(color))
            painter.setPen(QPen(Qt.black, 2))
            painter.drawRect(x, y, 120, 100)
            
            # Generator label
            painter.setPen(QPen(Qt.black))
            painter.setFont(QFont("Arial", 10, QFont.Bold))
            painter.drawText(x + 10, y + 20, f"Generator {plc_id.upper()}")
            
            # Status
            painter.setFont(QFont("Arial", 9))
            painter.drawText(x + 10, y + 40, f"Status: {status}")
            painter.drawText(x + 10, y + 55, f"Output: {kw:.1f} kW")
            painter.drawText(x + 10, y + 70, f"Fuel: {fuel:.1f}/{fuel_max:.0f}L")
        
        # Draw lightbulbs (right side)
        bulb_y = 100
        bulb_spacing = 100
        for i, (bulb_id, data) in enumerate(self.lightbulb_data.items()):
            x = width - 200
            y = bulb_y + i * bulb_spacing
            
            # Lightbulb circle
            state = data.get("state", "OFF")
            power = data.get("power_kw", 0.0)
            
            if state == "ON":
                color = QColor(255, 235, 59)  # Yellow
                pen_color = QColor(255, 193, 7)  # Darker yellow
            else:
                color = QColor(200, 200, 200)  # Gray
                pen_color = QColor(150, 150, 150)
            
            painter.setBrush(QBrush(color))
            painter.setPen(QPen(pen_color, 2))
            painter.drawEllipse(x, y, 60, 60)
            
            # Bulb label
            painter.setPen(QPen(Qt.black))
            painter.setFont(QFont("Arial", 9, QFont.Bold))
            painter.drawText(x - 20, y + 30, f"{bulb_id.upper()}")
            painter.setFont(QFont("Arial", 8))
            painter.drawText(x - 20, y + 45, f"{state} - {power:.2f}kW")
        
        # Draw substation (center)
        substation_x = width // 2 - 80
        substation_y = height // 2 - 60
        
        # Substation box (hexagon-like shape, drawn as rounded rectangle)
        # Get substation data - prefer substation1, otherwise use first available
        substation_data = {}
        if "substation1" in self.substation_data:
            substation_data = self.substation_data["substation1"]
        elif self.substation_data:
            substation_data = list(self.substation_data.values())[0]
        
        available_power = substation_data.get("available_power", 0.0)
        total_generated = substation_data.get("total_generated_power", 0.0)
        utilization = substation_data.get("utilization_percent", 0.0)
        
        # Debug print during paint
        if hasattr(self, '_paint_count'):
            self._paint_count += 1
        else:
            self._paint_count = 1
        if self._paint_count % 10 == 0:  # Print every 10th paint
            print(f"[SiteDiagram] paintEvent - available_power={available_power}, total_generated={total_generated}, utilization={utilization}")
        
        # Color based on utilization
        if utilization > 90:
            substation_color = QColor(244, 67, 54)  # Red - high load
        elif utilization > 70:
            substation_color = QColor(255, 152, 0)  # Orange - medium-high load
        else:
            substation_color = QColor(76, 175, 80)  # Green - normal load
        
        painter.setBrush(QBrush(substation_color))
        painter.setPen(QPen(Qt.black, 3))
        painter.drawRoundedRect(substation_x, substation_y, 160, 120, 10, 10)
        
        # Substation label
        painter.setPen(QPen(Qt.black))
        painter.setFont(QFont("Arial", 11, QFont.Bold))
        painter.drawText(substation_x + 20, substation_y + 25, "SMART HUB")
        painter.drawText(substation_x + 20, substation_y + 45, "SUBSTATION")
        
        # Power info
        painter.setFont(QFont("Arial", 9))
        painter.drawText(substation_x + 10, substation_y + 65, f"Generated: {total_generated:.1f} kW")
        painter.drawText(substation_x + 10, substation_y + 80, f"Available: {available_power:.1f} kW")
        painter.drawText(substation_x + 10, substation_y + 95, f"Load: {utilization:.1f}%")
        
        # Draw power lines (generators → substation → lightbulbs)
        painter.setPen(QPen(QColor(100, 100, 100), 2, Qt.DashLine))
        gen_center_x = 160
        substation_center_x = width // 2
        substation_center_y = height // 2
        bulb_center_x = width - 170
        
        # Lines from generators to substation
        for i, (plc_id, _) in enumerate(self.generator_data.items()):
            gen_y_pos = gen_y + i * gen_spacing + 50
            painter.drawLine(gen_center_x, gen_y_pos, substation_center_x, substation_center_y - 20)
        
        # Lines from substation to lightbulbs
        for i, (bulb_id, _) in enumerate(self.lightbulb_data.items()):
            bulb_y_pos = bulb_y + i * bulb_spacing + 30
            painter.drawLine(substation_center_x, substation_center_y + 20, bulb_center_x, bulb_y_pos)
    
    def update_generator_data(self, plc_id, data):
        """Update generator data and refresh display."""
        self.generator_data[plc_id] = data
        self.update()
    
    def update_lightbulb_data(self, bulb_id, data):
        """Update lightbulb data and refresh display."""
        self.lightbulb_data[bulb_id] = data
        self.update()
    
    def update_substation_data(self, substation_id, data):
        """Update substation data and refresh display."""
        print(f"[SiteDiagram] update_substation_data called for {substation_id}")
        print(f"[SiteDiagram] Data received: available_power={data.get('available_power', 0)}, total_generated={data.get('total_generated_power', 0)}")
        
        # Update the shared dictionary reference
        if substation_id in self.substation_data:
            self.substation_data[substation_id].update(data)
        else:
            self.substation_data[substation_id] = data
        
        print(f"[SiteDiagram] After update, substation_data[{substation_id}] = {self.substation_data[substation_id]}")
        print(f"[SiteDiagram] Calling self.update() to trigger repaint")
        
        # Force immediate repaint
        self.update()
        self.repaint()  # Also call repaint explicitly
        
        print(f"[SiteDiagram] Repaint completed")


class HMIGUI(QMainWindow):
    """Main HMI window."""
    def __init__(self, broker="localhost"):
        super().__init__()
        self.broker = broker
        self.setWindowTitle("Generator Control HMI - MQTT Demo")
        self.setGeometry(100, 100, 1000, 700)
        
        # MQTT client
        self.mqtt_client = mqtt.Client()
        self.mqtt_client.on_connect = self.on_connect
        self.mqtt_client.on_message = self.on_message
        
        # PLC panels storage
        self.plc_panels = {}
        
        # Lightbulb states
        self.lightbulb_states = {
            "bulb1": {"state": "OFF", "power_kw": 0.0},
            "bulb2": {"state": "OFF", "power_kw": 0.0},
            "bulb3": {"state": "OFF", "power_kw": 0.0},
            "bulb4": {"state": "OFF", "power_kw": 0.0}
        }
        
        # Generator data for site diagram
        self.generator_data = {
            "plc1": {"status": "UNKNOWN", "kw": 0.0, "fuel_level": 0.0, "fuel_max": 100.0},
            "plc2": {"status": "UNKNOWN", "kw": 0.0, "fuel_level": 0.0, "fuel_max": 80.0}
        }
        
        # Substation data
        self.substation_data = {
            "substation1": {
                "total_generated_power": 0.0,
                "total_consumption": 0.0,
                "available_power": 0.0,
                "utilization_percent": 0.0
            }
        }
        
        # MQTT message handler for thread-safe GUI updates
        self.message_handler = MQTTMessageHandler()
        self.message_handler.message_received.connect(self.on_mqtt_message)
        self.message_handler.lightbulb_message.connect(self.on_lightbulb_message)
        
        # Setup UI
        self.setup_ui()
        
        # Connect message handler to panels
        self.message_handler.plc_panels = self.plc_panels
        
        # Connect to MQTT
        self.connect_mqtt()
        
        # Timer for connection status check
        self.connection_timer = QTimer()
        self.connection_timer.timeout.connect(self.check_connection)
        self.connection_timer.start(1000)
    
    def setup_ui(self):
        """Setup the user interface."""
        # Create tab widget
        tabs = QTabWidget()
        self.setCentralWidget(tabs)
        
        # Tab 1: Control Panel
        control_tab = QWidget()
        control_layout = QVBoxLayout()
        control_tab.setLayout(control_layout)
        
        # Title
        title = QLabel("Generator Control & Monitoring System")
        title.setAlignment(Qt.AlignCenter)
        title.setFont(QFont("Arial", 16, QFont.Bold))
        title.setStyleSheet("padding: 10px; background-color: #2196F3; color: white;")
        control_layout.addWidget(title)
        
        # Connection status
        self.connection_label = QLabel("Connecting to MQTT broker...")
        self.connection_label.setAlignment(Qt.AlignCenter)
        self.connection_label.setStyleSheet("padding: 5px; background-color: #FFC107; font-weight: bold;")
        control_layout.addWidget(self.connection_label)
        
        # PLC panels layout
        panels_layout = QHBoxLayout()
        
        # Create panels for known PLCs
        for plc_id in ["plc1", "plc2"]:
            panel = PLCPanel(plc_id, self.mqtt_client)
            self.plc_panels[plc_id] = panel
            panels_layout.addWidget(panel)
        
        control_layout.addLayout(panels_layout)
        
        # Lightbulb controls
        bulb_group = QGroupBox("Lightbulb Controls")
        bulb_layout = QGridLayout()
        
        self.bulb_buttons = {}
        for i, bulb_id in enumerate(["bulb1", "bulb2", "bulb3", "bulb4"]):
            row = i // 2
            col = (i % 2) * 3
            
            label = QLabel(f"{bulb_id.upper()}:")
            bulb_layout.addWidget(label, row, col)
            
            # Toggle switch button
            switch_btn = QPushButton("OFF")
            switch_btn.setCheckable(True)
            switch_btn.setStyleSheet("""
                QPushButton {
                    background-color: #f44336;
                    color: white;
                    font-weight: bold;
                    padding: 8px 20px;
                    border-radius: 4px;
                    border: 2px solid #d32f2f;
                }
                QPushButton:checked {
                    background-color: #4CAF50;
                    border: 2px solid #388e3c;
                }
                QPushButton:hover {
                    background-color: #e57373;
                }
                QPushButton:checked:hover {
                    background-color: #66bb6a;
                }
            """)
            switch_btn.clicked.connect(lambda checked, b=bulb_id: self.toggle_bulb_switch(b, checked))
            bulb_layout.addWidget(switch_btn, row, col + 1)
            
            status_label = QLabel("OFF - 0.00kW")
            status_label.setStyleSheet("font-weight: bold; padding: 5px;")
            bulb_layout.addWidget(status_label, row, col + 2)
            
            self.bulb_buttons[bulb_id] = {"switch": switch_btn, "status": status_label}
        
        bulb_group.setLayout(bulb_layout)
        control_layout.addWidget(bulb_group)
        
        # Log area
        log_group = QGroupBox("MQTT Messages Log")
        log_layout = QVBoxLayout()
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setMaximumHeight(150)
        self.log_text.setStyleSheet("font-family: 'Courier New'; font-size: 10px;")
        log_layout.addWidget(self.log_text)
        log_group.setLayout(log_layout)
        control_layout.addWidget(log_group)
        
        tabs.addTab(control_tab, "Control Panel")
        
        # Tab 2: Site Diagram
        self.site_diagram = SiteDiagramWidget(
            self.mqtt_client,
            self.generator_data,
            self.lightbulb_states,
            self.substation_data
        )
        tabs.addTab(self.site_diagram, "Site Diagram")
    
    def connect_mqtt(self):
        """Connect to MQTT broker."""
        try:
            self.mqtt_client.connect(self.broker, 1883, 60)
            self.mqtt_client.loop_start()
            self.log_message(f"Connecting to MQTT broker at {self.broker}:1883...")
        except Exception as e:
            self.log_message(f"Error connecting to broker: {e}")
            self.connection_label.setText(f"Connection Error: {e}")
            self.connection_label.setStyleSheet("padding: 5px; background-color: #f44336; color: white; font-weight: bold;")
    
    def on_connect(self, client, userdata, flags, rc):
        """Callback when MQTT client connects."""
        if rc == 0:
            # Subscribe to HMI topics (data from central controller)
            client.subscribe("hmi/status/#")
            client.subscribe("hmi/telemetry/#")
            client.subscribe("hmi/heartbeat/#")
            client.subscribe("hmi/lightbulb/status/#")
            client.subscribe("hmi/substation/status/#")
            # Also subscribe directly to substation topic
            result1, mid1 = client.subscribe("substation/status/#")
            print(f"[HMI] Subscribed to substation/status/# - result: {result1}, mid: {mid1}")
            self.log_message("Connected to MQTT broker. Subscribed to hmi/# topics and substation/status/#")
            self.connection_label.setText("Connected to MQTT Broker")
            self.connection_label.setStyleSheet("padding: 5px; background-color: #4CAF50; color: white; font-weight: bold;")
        else:
            self.log_message(f"Failed to connect to broker. Return code: {rc}")
            self.connection_label.setText(f"Connection Failed (Code: {rc})")
            self.connection_label.setStyleSheet("padding: 5px; background-color: #f44336; color: white; font-weight: bold;")
    
    def on_message(self, client, userdata, msg):
        """Callback when MQTT message is received (runs in MQTT thread)."""
        topic = msg.topic
        payload = msg.payload.decode()
        
        # Debug: log all HMI and substation topics
        if topic.startswith("hmi/") or topic.startswith("substation/"):
            print(f"[HMI DEBUG] Received message on topic: {topic}")
        
        # Handle substation messages directly (from substation/status/#)
        if topic.startswith("substation/status/"):
            parts = topic.split("/")
            if len(parts) >= 3:
                substation_id = parts[-1]
                print(f"[HMI DEBUG] Processing direct substation message for {substation_id}, parts: {parts}")
                QTimer.singleShot(0, lambda sid=substation_id, pl=payload: self.on_substation_message(sid, pl))
                QTimer.singleShot(0, lambda: self.log_message(f"{topic} → {payload}"))
                return
        
        # Parse topic to extract device ID and message type (from HMI topics)
        parts = topic.split("/")
        if len(parts) >= 3 and parts[0] == "hmi":
            if parts[1] == "lightbulb" and parts[2] == "status":
                # Lightbulb status message
                bulb_id = parts[-1]
                self.message_handler.lightbulb_message.emit(bulb_id, payload)
            elif parts[1] == "substation" and parts[2] == "status" and len(parts) >= 4:
                # Substation status message
                substation_id = parts[-1]
                print(f"[HMI DEBUG] Processing substation message for {substation_id}, parts: {parts}")
                # Use a closure to capture the values properly
                QTimer.singleShot(0, lambda sid=substation_id, pl=payload: self.on_substation_message(sid, pl))
            else:
                # PLC message
                plc_id = parts[-1]  # Last part is PLC ID
                msg_type = parts[-2] if len(parts) >= 3 else None
                
                # Emit signal to handle in main thread (thread-safe)
                self.message_handler.message_received.emit(plc_id, msg_type, payload)
            
            # Log message (also needs to be thread-safe, but log_message uses QTimer which is safer)
            QTimer.singleShot(0, lambda: self.log_message(f"{topic} → {payload}"))
    
    def on_mqtt_message(self, plc_id, msg_type, payload):
        """Handle MQTT message in main thread (called via signal)."""
        self.message_handler.handle_message(plc_id, msg_type, payload)
        
        # Update generator data for site diagram
        if msg_type == "status":
            if plc_id in self.generator_data:
                self.generator_data[plc_id]["status"] = payload
                self.site_diagram.update_generator_data(plc_id, self.generator_data[plc_id])
        elif msg_type == "telemetry":
            try:
                data = json.loads(payload)
                if plc_id in self.generator_data:
                    self.generator_data[plc_id].update({
                        "kw": data.get("kw", 0.0),
                        "fuel_level": data.get("fuel_level", 0.0),
                        "fuel_max": data.get("fuel_max", 100.0)
                    })
                    self.site_diagram.update_generator_data(plc_id, self.generator_data[plc_id])
            except:
                pass
    
    def on_lightbulb_message(self, bulb_id, payload):
        """Handle lightbulb message in main thread."""
        try:
            data = json.loads(payload)
            if bulb_id in self.lightbulb_states:
                self.lightbulb_states[bulb_id] = {
                    "state": data.get("state", "OFF"),
                    "power_kw": data.get("power_kw", 0.0)
                }
                # Update site diagram
                self.site_diagram.update_lightbulb_data(bulb_id, self.lightbulb_states[bulb_id])
                # Update status label and switch
                if bulb_id in self.bulb_buttons:
                    state = self.lightbulb_states[bulb_id]["state"]
                    power = self.lightbulb_states[bulb_id]["power_kw"]
                    self.bulb_buttons[bulb_id]["status"].setText(f"{state} - {power:.2f}kW")
                    
                    # Update switch state (block signals to avoid feedback loop)
                    switch = self.bulb_buttons[bulb_id]["switch"]
                    switch.blockSignals(True)
                    switch.setChecked(state == "ON")
                    switch.setText(state)
                    switch.blockSignals(False)
        except:
            pass
    
    def on_substation_message(self, substation_id, payload):
        """Handle substation status message in main thread."""
        try:
            print(f"[HMI] on_substation_message called for {substation_id}")
            data = json.loads(payload)
            print(f"[HMI] Parsed substation data: available_power={data.get('available_power', 0)}, total_generated={data.get('total_generated_power', 0)}")
            
            # Update the shared dictionary
            if substation_id in self.substation_data:
                self.substation_data[substation_id].update(data)
                print(f"[HMI] Updated substation_data[{substation_id}], now contains: {self.substation_data[substation_id]}")
            else:
                print(f"[HMI] Adding new substation {substation_id} to data")
                self.substation_data[substation_id] = data
            
            # Force update the site diagram
            print(f"[HMI] Calling site_diagram.update_substation_data({substation_id})")
            self.site_diagram.update_substation_data(substation_id, self.substation_data[substation_id])
            print(f"[HMI] Site diagram update completed")
            self.log_message(f"Substation {substation_id}: {data.get('available_power', 0):.1f} kW available, {data.get('utilization_percent', 0):.1f}% load")
        except json.JSONDecodeError as e:
            print(f"[HMI] JSON decode error: {e}, payload: {payload}")
        except Exception as e:
            print(f"[HMI] Error processing substation message: {e}")
            import traceback
            traceback.print_exc()
    
    def toggle_bulb_switch(self, bulb_id, is_on):
        """Toggle lightbulb ON/OFF via central controller."""
        command = "ON" if is_on else "OFF"
        topic = topics.HMI_LIGHTBULB_CONTROL.format(bulb=bulb_id)
        self.mqtt_client.publish(topic, command)
        print(f"[HMI] Sent {command} to lightbulb {bulb_id} via {topic}")
        
        # Update button text
        if bulb_id in self.bulb_buttons:
            self.bulb_buttons[bulb_id]["switch"].setText(command)
    
    def toggle_bulb(self, bulb_id, command):
        """Legacy method - kept for compatibility."""
        self.toggle_bulb_switch(bulb_id, command == "ON")
    
    def log_message(self, message):
        """Add message to log area."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_text.append(f"[{timestamp}] {message}")
        # Auto-scroll to bottom
        scrollbar = self.log_text.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())
    
    def check_connection(self):
        """Check MQTT connection status."""
        if not self.mqtt_client.is_connected():
            if "Connected" in self.connection_label.text():
                self.connection_label.setText("Disconnected from MQTT Broker")
                self.connection_label.setStyleSheet("padding: 5px; background-color: #f44336; color: white; font-weight: bold;")
                self.log_message("Lost connection to MQTT broker. Attempting to reconnect...")
                self.connect_mqtt()


def main():
    """Main entry point."""
    app = QApplication(sys.argv)
    
    # Set application style
    app.setStyle("Fusion")
    
    window = HMIGUI()
    window.show()
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()

