"""
Simple GUI to display messages forwarded from SQLite buffer
Subscribes to bridge/# topics to see forwarded messages
"""
import json
import tkinter as tk
from tkinter import ttk, scrolledtext
import paho.mqtt.client as mqtt
from datetime import datetime


class SimpleGUI:
    """Simple GUI to display forwarded buffer messages"""
    
    def __init__(self, root, broker="localhost", port=1883):
        self.root = root
        self.root.title("SQLite Buffer Monitor - Lane 2 POC")
        self.root.geometry("900x700")
        
        self.broker = broker
        self.port = port
        self.message_count = 0
        
        # MQTT client
        self.client = mqtt.Client()
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message
        
        self.setup_ui()
        self.connect_mqtt()
        
        # Auto-scroll timer
        self.auto_scroll = True
    
    def setup_ui(self):
        # Header frame
        header = ttk.Frame(self.root, padding="10")
        header.pack(fill=tk.X)
        
        self.status_label = ttk.Label(
            header,
            text="Connecting...",
            font=("Arial", 12, "bold")
        )
        self.status_label.pack(side=tk.LEFT)
        
        self.count_label = ttk.Label(
            header,
            text="Messages: 0",
            font=("Arial", 10)
        )
        self.count_label.pack(side=tk.LEFT, padx=20)
        
        # Clear button
        clear_btn = ttk.Button(header, text="Clear", command=self.clear_messages)
        clear_btn.pack(side=tk.RIGHT)
        
        # Messages display
        msg_frame = ttk.LabelFrame(self.root, text="Forwarded Messages from Buffer", padding="10")
        msg_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        self.messages_text = scrolledtext.ScrolledText(
            msg_frame,
            height=30,
            font=("Consolas", 9),
            wrap=tk.WORD
        )
        self.messages_text.pack(fill=tk.BOTH, expand=True)
        
        # Info label
        info_label = ttk.Label(
            self.root,
            text="Subscribed to: bridge/# (messages forwarded from SQLite buffer)",
            font=("Arial", 8),
            foreground="gray"
        )
        info_label.pack(side=tk.BOTTOM, pady=5)
    
    def connect_mqtt(self):
        """Connect to MQTT broker"""
        try:
            self.client.connect(self.broker, self.port, 60)
            self.client.loop_start()
        except Exception as e:
            self.add_message(f"ERROR: Failed to connect to MQTT: {e}", "error")
    
    def on_connect(self, client, userdata, flags, rc):
        """Callback when MQTT connects"""
        if rc == 0:
            # Subscribe to bridge topics (where forwarder publishes)
            client.subscribe("bridge/#", qos=1)
            self.status_label.config(text="✓ Connected", foreground="green")
            self.add_message("Connected to MQTT broker. Subscribed to bridge/#", "info")
        else:
            self.status_label.config(text=f"✗ Connection failed ({rc})", foreground="red")
            self.add_message(f"Connection failed with code: {rc}", "error")
    
    def on_message(self, client, userdata, msg):
        """Callback when MQTT message received"""
        try:
            topic = msg.topic
            payload_str = msg.payload.decode('utf-8')
            
            # Try to parse as JSON
            try:
                payload = json.loads(payload_str)
                payload_formatted = json.dumps(payload, indent=2)
            except json.JSONDecodeError:
                payload_formatted = payload_str
            
            self.message_count += 1
            self.count_label.config(text=f"Messages: {self.message_count}")
            
            # Add to display
            timestamp = datetime.now().strftime("%H:%M:%S")
            self.add_message(f"[{timestamp}] Topic: {topic}\n{payload_formatted}\n", "message")
            
        except Exception as e:
            self.add_message(f"Error processing message: {e}", "error")
    
    def add_message(self, text, msg_type="message"):
        """Add message to display"""
        self.messages_text.insert(tk.END, text + "\n" + ("-" * 80) + "\n\n")
        
        if self.auto_scroll:
            self.messages_text.see(tk.END)
        
        self.root.update_idletasks()
    
    def clear_messages(self):
        """Clear message display"""
        self.messages_text.delete(1.0, tk.END)
        self.message_count = 0
        self.count_label.config(text="Messages: 0")


if __name__ == "__main__":
    root = tk.Tk()
    app = SimpleGUI(root)
    
    print("GUI started. Waiting for messages from buffer forwarder...")
    print("Make sure the bridge service (main.py) is running!")
    
    root.mainloop()

