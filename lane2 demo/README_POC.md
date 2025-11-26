# SQLite Buffer Proof of Concept

## Flow
```
PLC Simulator → MQTT Broker → MQTT Subscriber → SQLite Buffer → Buffer Forwarder → MQTT Broker → GUI
```

## How to Test

### 1. Start MQTT Broker
Make sure you have an MQTT broker running on `localhost:1883`

### 2. Start the Bridge Service (Terminal 1)
```powershell
cd "lane2 demo"
.\.venv\Scripts\python.exe main.py
```

This will:
- Initialize SQLite buffer
- Connect MQTT subscriber (listens to `plc/telemetry/#`)
- Connect MQTT publisher (forwards to `bridge/#`)
- Start forwarding loop

### 3. Start PLC Simulator (Terminal 2)
```powershell
cd "lane2 demo"
.\.venv\Scripts\python.exe test_plc_simulator.py
```

This will publish test telemetry messages every 2 seconds to `plc/telemetry/plc1`

### 4. Start Simple GUI (Terminal 3)
```powershell
cd "lane2 demo"
.\.venv\Scripts\python.exe simple_gui.py
```

This will:
- Connect to MQTT broker
- Subscribe to `bridge/#` (where forwarder publishes)
- Display all forwarded messages

## What to Expect

1. **PLC Simulator** publishes messages like:
   ```json
   {
     "plc_id": "plc1",
     "timestamp": 1234567890,
     "sequence": 1,
     "voltage": 240.5,
     "current": 10.2,
     "power_kw": 2.45,
     "status": "RUNNING"
   }
   ```

2. **Bridge Service** receives these, stores in SQLite buffer, then forwards them to `bridge/mqtt:plc/telemetry/plc1`

3. **GUI** displays the forwarded messages in real-time

## Verify Buffer is Working

Check the SQLite database:
```powershell
python -c "from buffer.sqlite_buffer import get_buffer_depth; print(f'Buffer depth: {get_buffer_depth()}')"
```

Or use a SQLite viewer to inspect `buffer/bridge_buffer.db`

