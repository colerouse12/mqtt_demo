# MQTT Topics and Data Structures Proposal
## Dispatch365 Microgrid Control System

**Status**: PROPOSAL - Awaiting Approval  
**Date**: 2025-10-01  
**Purpose**: Define MQTT topic hierarchy and data payload structures for the microgrid control system

---

## 1. Topic Hierarchy Design

### 1.1 Base Topic Structure
```
site/{site_id}/{category}/{subcategory}/{asset_id}/{data_type}
```

### 1.2 Topic Categories

#### **System-Level Topics** (No asset_id)
```
site/{site_id}/system/{data_type}
```

#### **Asset-Specific Topics** (With asset_id)
```
site/{site_id}/asset/{asset_id}/{data_type}
```

#### **Command Topics** (Bidirectional)
```
site/{site_id}/command/{asset_id}/{command_type}
```

### 1.3 Architecture: Lane 1 Adapters

**Python Adapters** (part of this project):
- Read data from PLCs via Modbus TCP
- Read data from embedded controllers
- Translate to MQTT topics
- Publish at appropriate frequencies:
  - **Most data**: 10 seconds
  - **Breaker status & faults**: 4Hz (4 times per second)
- Calculate and publish averages:
  - **1-minute averages**: Published every minute
  - **5-minute averages**: Published every 5 minutes
- Publish historic data:
  - **1-minute intervals**: For all telemetry
  - **Hourly intervals**: For aggregated data
  - **State changes**: Published immediately (not averaged)
  - **Faults**: Published immediately (not averaged)

---

## 2. Complete Topic List

### 2.1 System-Level Topics

| Topic | Retain | QoS | Update Rate | Description | Publisher | Subscriber |
|-------|--------|-----|-------------|-------------|-----------|------------|
| `site/{site_id}/system/state` | Yes | 1 | On change | FSM state, operational mode | Controller | GUI, PLC, Loggers |
| `site/{site_id}/system/telemetry` | Yes | 1 | 10s | System-wide measurements | Adapter | GUI, Database, Controller |
| `site/{site_id}/system/telemetry/1min` | Yes | 1 | 1min | 1-minute averaged telemetry | Adapter | GUI, Database |
| `site/{site_id}/system/telemetry/5min` | Yes | 1 | 5min | 5-minute averaged telemetry | Adapter | GUI, Database |
| `site/{site_id}/system/telemetry/hourly` | Yes | 1 | 1hr | Hourly aggregated telemetry | Adapter | Database, Analytics |
| `site/{site_id}/system/settings` | Yes | 1 | On change | System settings/configuration | Controller | GUI, PLC |
| `site/{site_id}/system/config` | Yes | 1 | On change | System configuration (rarely changes) | Controller | GUI, PLC, Adapters |
| `site/{site_id}/system/alarms` | No | 1 | Immediate | System alarms and events | Adapter/Controller | GUI, Loggers, PLC |
| `site/{site_id}/system/events` | No | 1 | On event | Event log entries | Controller | GUI, Database |
| `site/{site_id}/system/iso` | Yes | 1 | 10s | ISO pricing data | Controller | GUI, Economic Dispatch |
| `site/{site_id}/system/weather` | Yes | 1 | 10s | Weather data | Controller | GUI, Load Forecast |

### 2.2 Asset Telemetry Topics

**Power-Critical Data** (split for priority):
| Topic Pattern | Retain | QoS | Update Rate | Description | Publisher |
|---------------|--------|-----|-------------|-------------|-----------|
| `site/{site_id}/asset/{asset_id}/power` | Yes | 1 | 10s | Power measurements (critical) | Adapter |
| `site/{site_id}/asset/{asset_id}/power/1min` | Yes | 1 | 1min | 1-min averaged power | Adapter |
| `site/{site_id}/asset/{asset_id}/power/5min` | Yes | 1 | 5min | 5-min averaged power | Adapter |

**Complete Telemetry** (all parameters):
| Topic Pattern | Retain | QoS | Update Rate | Description | Publisher |
|---------------|--------|-----|-------------|-------------|-----------|
| `site/{site_id}/asset/{asset_id}/telemetry` | Yes | 1 | 10s | Complete asset telemetry | Adapter |
| `site/{site_id}/asset/{asset_id}/telemetry/1min` | Yes | 1 | 1min | 1-min averaged telemetry | Adapter |
| `site/{site_id}/asset/{asset_id}/telemetry/hourly` | Yes | 1 | 1hr | Hourly aggregated telemetry | Adapter |

**State and Status** (faults at 4Hz):
| Topic Pattern | Retain | QoS | Update Rate | Description | Publisher |
|---------------|--------|-----|-------------|-------------|-----------|
| `site/{site_id}/asset/{asset_id}/state` | Yes | 1 | 10s | Asset operational state | Adapter |
| `site/{site_id}/asset/{asset_id}/faults` | Yes | 1 | 4Hz | Fault status (high frequency) | Adapter |
| `site/{site_id}/asset/{asset_id}/breakers` | Yes | 1 | 4Hz | Breaker status (high frequency) | Adapter |

### 2.3 Asset Command Topics

| Topic Pattern | Retain | QoS | Description | Publisher | Subscriber |
|---------------|--------|-----|-------------|-----------|------------|
| `site/{site_id}/command/{asset_id}/setpoint` | No | 1 | Power/control setpoints | Controller | PLC |
| `site/{site_id}/command/{asset_id}/control` | No | 1 | Control commands (start/stop/etc) | Controller | PLC |
| `site/{site_id}/command/{asset_id}/ack` | No | 1 | Command acknowledgments | PLC | Controller |

### 2.4 Asset-Specific Topic Examples

**Generator (Gen1, asset_id=4):**
- `site/0/asset/4/telemetry` - Generator telemetry
- `site/0/asset/4/state` - Generator state
- `site/0/command/4/setpoint` - Power setpoint command
- `site/0/command/4/control` - Start/stop commands
- `site/0/command/4/ack` - Command acknowledgments

**Battery (Battery, asset_id=7):**
- `site/0/asset/7/telemetry` - Battery telemetry
- `site/0/asset/7/state` - Battery state
- `site/0/command/7/setpoint` - Charge/discharge setpoint
- `site/0/command/7/control` - Mode commands

**Load Bank (LoadBank, asset_id=6):**
- `site/0/asset/6/telemetry` - Load bank telemetry
- `site/0/asset/6/state` - Load bank state
- `site/0/command/6/setpoint` - Load setpoint
- `site/0/command/6/control` - Load bank control

---

## 3. Data Payload Structures

### 3.1 System State Payload
**Topic**: `site/{site_id}/system/state`

```json
{
  "timestamp": "2025-10-01T12:00:00Z",
  "site_id": "0",
  "fsm_state": "LOAD_FOLLOWING",
  "operational_mode": "SMG",
  "grid_connected": true,
  "system_ready": true,
  "fault_active": false,
  "maintenance_mode": false
}
```

### 3.2 System Telemetry Payload
**Topic**: `site/{site_id}/system/telemetry`

```json
{
  "timestamp": "2025-10-01T12:00:00Z",
  "site_id": "0",
  "load": {
    "substation_load_kw": 1250.5,
    "site_load_kw": 1200.0,
    "site_load_avg_kw": 1180.0,
    "site_load_avg_10min_kw": 1195.0,
    "day_peak_load_kw": 1500.0
  },
  "generation": {
    "total_gen_kw": 1400.0,
    "total_gen_capacity_kw": 2950.0,
    "available_capacity_kw": 1550.0,
    "reserve_power_kw": 200.0
  },
  "grid": {
    "grid_import_kw": 0.0,
    "grid_export_kw": 150.0,
    "grid_voltage_v": 12470.0,
    "grid_frequency_hz": 60.0
  },
  "battery": {
    "soc_percent": 75.5,
    "power_kw": -200.0,
    "capacity_kwh": 2000.0
  },
  "pv": {
    "power_kw": 150.0,
    "capacity_kw": 300.0,
    "irradiance_w_m2": 800.0
  }
}
```

### 3.3 System Settings Payload
**Topic**: `site/{site_id}/system/settings`

```json
{
  "timestamp": "2025-10-01T12:00:00Z",
  "site_id": "0",
  "settings": {
    "AutoDispatch": true,
    "CapacityMode": "RTP",
    "ISO": "PJM",
    "ISONode": "AEP",
    "MinImport": 100,
    "MinImport_Sys": 500,
    "Limit_kW": 2000,
    "Limit_kW_Sys": 5000,
    "Reserve Pwr (Startup)": 200,
    "StartupCosts": 50.0,
    "Headroom per Gen-Day": 100,
    "MinRuntime": 60,
    "UseCapAvoid": true,
    "UseCapSales": false,
    "UseSRModel": true
  }
}
```

### 3.4 System Configuration Payload
**Topic**: `site/{site_id}/system/config`

**Note**: This contains ALL static configuration parameters. Live/operational data goes in telemetry topics.

```json
{
  "timestamp": "2025-10-01T12:00:00Z",
  "site_id": "0",
  "site_name": "TestSite",
  "assets": [
    {
      "asset_id": "4",
      "asset_type": "Gen",
      "name": "Gen1",
      "enabled": true,
      "modbus_tags": {
        "power_tag": 5,
        "status_tag": 4,
        "fuel_tag": 7,
        "t1_tag": 6,
        "start_stop_tag": 24,
        "breaker_tag": 25,
        "hour_tag": 26
      },
      "performance": {
        "capacity_kw": 1475,
        "capacity_kw_80f": 1475,
        "capacity_kw_100f": 1475,
        "min_power_kw": 750,
        "max_power_kw": 1475,
        "para_kw": 0,
        "kw_derate": 0,
        "nominal_temp_f": 60
      },
      "heat_rates": {
        "hr_100_percent": 11000,
        "hr_75_percent": 12000,
        "hr_50_percent": 13000,
        "hr_derate": 0.028625425
      },
      "emissions": {
        "nox_lb_mmbtu": 0.280035394,
        "co_lb_mmbtu": 0.034077887,
        "pm_lb_mmbtu": 0.00991,
        "pm10_lb_mmbtu": 0.0000771,
        "vom_lb_mmbtu": 0.022355094,
        "so2_lb_mmbtu": 0.000588,
        "haps_lb_mmbtu": 0.038323069,
        "form_lb_mmbtu": 0.012
      },
      "operational": {
        "start_time_s": 60,
        "stop_time_s": 10,
        "fuel_type": "diesel",
        "no_export": false
      },
      "maintenance": {
        "maint_dol_hr": 0.0,
        "maint_dol_kwh": 0.0
      }
    },
    {
      "asset_id": "7",
      "asset_type": "Batt",
      "name": "Battery",
      "enabled": true,
      "config": {
        "capacity_kwh": 2000,
        "max_charge_kw": 1800,
        "max_discharge_kw": 2000,
        "min_power_kw": 200,
        "low_kwh": 200,
        "high_kwh": 1800,
        "efficiency": 0.90
      }
    },
    {
      "asset_id": "6",
      "asset_type": "PV",
      "name": "Solar PV",
      "enabled": true,
      "config": {
        "capacity_kw": 300,
        "max_power_kw": 300,
        "efficiency": 0.20,
        "inverter_efficiency": 0.95
      }
    },
    {
      "asset_id": "6",
      "asset_type": "LoadBank",
      "name": "LoadBank",
      "enabled": true,
      "config": {
        "max_load_kw": 500,
        "load_step_kw": 25,
        "min_load_kw": 0
      }
    }
  ]
}
```

### 3.5 Generator Power Payload (Priority Topic)
**Topic**: `site/{site_id}/asset/{asset_id}/power`

**Note**: This is the critical power data published at 10s intervals for power balance calculations.

```json
{
  "timestamp": "2025-10-01T12:00:00Z",
  "asset_id": "4",
  "asset_type": "Gen",
  "power_output_kw": 750.0,
  "power_setpoint_kw": 750.0,
  "reactive_kvar": 50.0,
  "power_factor": 0.95,
  "available_capacity_kw": 725.0
}
```

### 3.6 Generator Telemetry Payload (Complete)
**Topic**: `site/{site_id}/asset/{asset_id}/telemetry`

**Note**: Full telemetry with all parameters. Published at 10s intervals.

```json
{
  "timestamp": "2025-10-01T12:00:00Z",
  "asset_id": "4",
  "asset_type": "Gen",
  "power": {
    "output_kw": 750.0,
    "setpoint_kw": 750.0,
    "reactive_kvar": 50.0,
    "power_factor": 0.95
  },
  "electrical": {
    "voltage_l1_l2_v": 480.0,
    "voltage_l2_l3_v": 480.0,
    "voltage_l3_l1_v": 480.0,
    "current_l1_a": 900.0,
    "current_l2_a": 900.0,
    "current_l3_a": 900.0,
    "frequency_hz": 60.0
  },
  "engine": {
    "oil_pressure_kpa": 350.0,
    "oil_temp_c": 85.0,
    "coolant_temp_c": 90.0,
    "fuel_flow_kg_h": 200.0,
    "engine_hours": 883113.0,
    "corrected_hours": 883113.0,
    "ambient_temp_f": 72.0,
    "ambient_temp_c": 22.2
  },
  "exhaust": {
    "exhaust_temp_1_c": 450.0,
    "exhaust_temp_2_c": 455.0,
    "exhaust_temp_3_c": 448.0,
    "exhaust_temp_4_c": 452.0,
    "exhaust_temp_5_c": 450.0,
    "exhaust_temp_6_c": 453.0,
    "exhaust_temp_7_c": 451.0,
    "exhaust_temp_8_c": 449.0,
    "exhaust_temp_9_c": 452.0,
    "exhaust_temp_10_c": 450.0,
    "exhaust_temp_11_c": 454.0,
    "exhaust_temp_12_c": 451.0,
    "exhaust_temp_13_c": 453.0,
    "exhaust_temp_14_c": 450.0,
    "exhaust_temp_15_c": 452.0,
    "exhaust_temp_16_c": 451.0
  },
  "filters": {
    "oil_filter_dp_kpa": 10.0
  },
  "air": {
    "intake_manifold_airflow_scfm": 5000.0
  }
}
```

### 3.7 Generator State Payload
**Topic**: `site/{site_id}/asset/{asset_id}/state`

```json
{
  "timestamp": "2025-10-01T12:00:00Z",
  "asset_id": "4",
  "asset_type": "Gen",
  "running": true,
  "ready_to_load": true,
  "fault": false,
  "warning": false,
  "comm_fault": false,
  "failed_start": false,
  "maintenance_lock": false,
  "dispatched": false,
  "start_replacement": false,
  "hard_fault": false,
  "fault_lock": false,
  "num_starts": 890,
  "start_date": "2025-08-20T14:44:52Z",
  "run_minutes": 883113,
  "start_minutes": 883113.0,
  "bias_minutes": 227820
}
```

### 3.8 Generator Faults Payload (4Hz)
**Topic**: `site/{site_id}/asset/{asset_id}/faults`

**Note**: Published at 4Hz for rapid fault detection.

```json
{
  "timestamp": "2025-10-01T12:00:00.250Z",
  "asset_id": "4",
  "asset_type": "Gen",
  "hard_fault": false,
  "fault_lock": false,
  "warning": false,
  "comm_fault": false,
  "failed_start": false,
  "common_warning_alarm": false,
  "common_shutdown_alarm": false,
  "fault_code": 0,
  "fault_message": ""
}
```

### 3.9 Generator Breakers Payload (4Hz)
**Topic**: `site/{site_id}/asset/{asset_id}/breakers`

**Note**: Published at 4Hz for rapid breaker status monitoring.

```json
{
  "timestamp": "2025-10-01T12:00:00.250Z",
  "asset_id": "4",
  "asset_type": "Gen",
  "generator_breaker_closed": true,
  "generator_breaker_tripped": false,
  "grid_breaker_closed": true,
  "grid_breaker_tripped": false
}
```

### 3.10 Generator Command Payloads

**Power Setpoint Command:**
**Topic**: `site/{site_id}/command/{asset_id}/setpoint`

```json
{
  "timestamp": "2025-10-01T12:00:00Z",
  "asset_id": "4",
  "command_id": "cmd_12345",
  "power_setpoint_kw": 1000.0,
  "priority": 1
}
```

**Control Command:**
**Topic**: `site/{site_id}/command/{asset_id}/control`

```json
{
  "timestamp": "2025-10-01T12:00:00Z",
  "asset_id": "4",
  "command_id": "cmd_12346",
  "command": "start",
  "power_setpoint_kw": 1000.0,
  "timeout_s": 60
}
```

**Command Acknowledgment:**
**Topic**: `site/{site_id}/command/{asset_id}/ack`

```json
{
  "timestamp": "2025-10-01T12:00:01Z",
  "asset_id": "4",
  "command_id": "cmd_12346",
  "status": "accepted",
  "message": "Generator start command accepted"
}
```

### 3.11 Battery Power Payload (Priority Topic)
**Topic**: `site/{site_id}/asset/{asset_id}/power`

```json
{
  "timestamp": "2025-10-01T12:00:00Z",
  "asset_id": "7",
  "asset_type": "Batt",
  "power_kw": -200.0,
  "soc_percent": 75.5,
  "available_charge_kw": 1800.0,
  "available_discharge_kw": 2000.0
}
```

### 3.12 Battery Telemetry Payload (Complete)
**Topic**: `site/{site_id}/asset/{asset_id}/telemetry`

**Note**: Live operational data only. Config parameters (capacity, max_charge, max_discharge) are in system/config.

```json
{
  "timestamp": "2025-10-01T12:00:00Z",
  "asset_id": "7",
  "asset_type": "Batt",
  "soc_percent": 75.5,
  "soc_kwh": 1510.0,
  "power_kw": -200.0,
  "voltage_v": 480.0,
  "current_a": -416.7,
  "temperature_c": 25.0,
  "charge_power_kw": 200.0,
  "discharge_power_kw": 0.0
}
```

### 3.13 Battery State Payload
**Topic**: `site/{site_id}/asset/{asset_id}/state`

```json
{
  "timestamp": "2025-10-01T12:00:00Z",
  "asset_id": "7",
  "asset_type": "Batt",
  "mode": "charge",
  "enabled": true,
  "fault": false,
  "warning": false,
  "comm_fault": false
}
```

### 3.14 PV Power Payload (Priority Topic)
**Topic**: `site/{site_id}/asset/{asset_id}/power`

```json
{
  "timestamp": "2025-10-01T12:00:00Z",
  "asset_id": "6",
  "asset_type": "PV",
  "power_kw": 150.0,
  "available_capacity_kw": 150.0
}
```

### 3.15 PV Telemetry Payload (Complete)
**Topic**: `site/{site_id}/asset/{asset_id}/telemetry`

**Note**: Live operational data only. Config parameters (capacity) are in system/config.

```json
{
  "timestamp": "2025-10-01T12:00:00Z",
  "asset_id": "6",
  "asset_type": "PV",
  "power_kw": 150.0,
  "irradiance_w_m2": 800.0,
  "voltage_v": 480.0,
  "current_a": 312.5,
  "temperature_c": 35.0,
  "enabled": true,
  "curtailed": false
}
```

### 3.16 Load Bank Power Payload (Priority Topic)
**Topic**: `site/{site_id}/asset/{asset_id}/power`

```json
{
  "timestamp": "2025-10-01T12:00:00Z",
  "asset_id": "6",
  "asset_type": "LoadBank",
  "power_kw": 400.0,
  "power_setpoint_kw": 400.0
}
```

### 3.17 Load Bank Telemetry Payload (Complete)
**Topic**: `site/{site_id}/asset/{asset_id}/telemetry`

**Note**: Live operational data only. Config parameters (max_load, step_size) are in system/config.

```json
{
  "timestamp": "2025-10-01T12:00:00Z",
  "asset_id": "6",
  "asset_type": "LoadBank",
  "power_kw": 400.0,
  "power_setpoint_kw": 400.0,
  "reactive_kvar": 0.0,
  "voltage_v": 480.0,
  "frequency_hz": 60.0,
  "status": "running",
  "fault": false,
  "error_code": 0
}
```

### 3.18 Load Bank State Payload
**Topic**: `site/{site_id}/asset/{asset_id}/state`

```json
{
  "timestamp": "2025-10-01T12:00:00Z",
  "asset_id": "6",
  "asset_type": "LoadBank",
  "current_command_kw": 400.0,
  "last_change_time": "2025-10-01T11:55:00Z",
  "enabled": true,
  "fault": false
}
```

### 3.19 POC (Point of Common Coupling) State Payload
**Topic**: `site/{site_id}/asset/{asset_id}/state`

```json
{
  "timestamp": "2025-10-01T12:00:00Z",
  "asset_id": "8",
  "asset_type": "POC",
  "position": "closed",
  "permissive": true,
  "grid_connected": true
}
```

### 3.20 ISO Pricing Payload
**Topic**: `site/{site_id}/system/iso`

```json
{
  "timestamp": "2025-10-01T12:00:00Z",
  "site_id": "0",
  "iso": "PJM",
  "node_id": "AEP",
  "current_rtp": 0.045,
  "rtp_predictor": 0.048,
  "rtp_std_dev": 0.005,
  "dap": {
    "prices": [0.042, 0.044, 0.046, 0.048, 0.050],
    "hours": [13, 14, 15, 16, 17]
  },
  "iso_load": 50000.0,
  "cap_request": false,
  "cap_event": false,
  "dap_event": false,
  "rtp_event": false,
  "effective_on_peak_elec_energy_rate": 0.12,
  "effective_off_peak_elec_energy_rate": 0.08,
  "effective_billed_rate": 0.10
}
```

### 3.21 Weather Data Payload
**Topic**: `site/{site_id}/system/weather`

```json
{
  "timestamp": "2025-10-01T12:00:00Z",
  "site_id": "0",
  "temperature_f": 72.0,
  "temperature_c": 22.2,
  "humidity": 65.0,
  "wind_speed_mph": 10.0,
  "wind_speed_ms": 4.5,
  "wind_direction": 180.0,
  "pressure_inhg": 29.92,
  "pressure_pa": 101325.0,
  "visibility_mi": 10.0,
  "visibility_m": 16093.0,
  "description": "Partly Cloudy",
  "station_id": "KXYZ",
  "station_name": "Weather Station",
  "irradiance_w_m2": 800.0,
  "forecast": {
    "temperature_f": [72, 75, 78],
    "hours": [13, 14, 15]
  }
}
```

### 3.22 Alarm Payload
**Topic**: `site/{site_id}/system/alarms`

```json
{
  "timestamp": "2025-10-01T12:00:00Z",
  "site_id": "0",
  "alarm_id": "alm_12345",
  "alarm_type": "generator_fault",
  "severity": "critical",
  "asset_id": "4",
  "asset_type": "Gen",
  "message": "Generator 1 hard fault detected",
  "acknowledged": false,
  "cleared": false
}
```

### 3.23 Event Log Payload
**Topic**: `site/{site_id}/system/events`

```json
{
  "timestamp": "2025-10-01T12:00:00Z",
  "site_id": "0",
  "event_id": "evt_12345",
  "event_type": "gen_start",
  "asset_id": "4",
  "message": "Generator 1 started",
  "data": {
    "power_setpoint_kw": 1000.0,
    "start_time_s": 60
  }
}
```

---

## 4. Python Data Structure Organization

### 4.1 Recommended Approach: Dataclasses + Dictionaries

**For FSM and Core Logic:**
- Use **dataclasses** for structured, type-safe data
- Fast access, easy to serialize/deserialize
- Good for state management

**For GUI and Flexible Access:**
- Use **dictionaries** for dynamic, flexible access
- Easy to iterate, filter, search
- Good for display and configuration

### 4.2 Proposed Python Structure

```python
# Core data structures (dataclasses)
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from datetime import datetime

@dataclass
class SystemState:
    """System-level state for FSM"""
    timestamp: datetime
    site_id: str
    fsm_state: str
    operational_mode: str
    grid_connected: bool
    system_ready: bool
    fault_active: bool
    maintenance_mode: bool

@dataclass
class SystemTelemetry:
    """System-level telemetry"""
    timestamp: datetime
    site_id: str
    load: Dict[str, float]
    generation: Dict[str, float]
    grid: Dict[str, float]
    battery: Optional[Dict[str, float]] = None
    pv: Optional[Dict[str, float]] = None

@dataclass
class AssetTelemetry:
    """Asset telemetry (generic structure)"""
    timestamp: datetime
    asset_id: str
    asset_type: str
    data: Dict[str, Any]  # Flexible structure for different asset types

@dataclass
class AssetState:
    """Asset state (generic structure)"""
    timestamp: datetime
    asset_id: str
    asset_type: str
    state: Dict[str, Any]  # Flexible structure for different asset types

@dataclass
class Command:
    """Command structure"""
    timestamp: datetime
    asset_id: str
    command_id: str
    command_type: str
    data: Dict[str, Any]
```

### 4.3 Message Bus Data Storage

**For FSM:**
```python
class FSMController:
    def __init__(self):
        # Use dataclasses for fast, structured access
        self.system_state = SystemState(...)
        self.system_telemetry = SystemTelemetry(...)
        self.asset_states: Dict[str, AssetState] = {}
        self.asset_telemetry: Dict[str, AssetTelemetry] = {}
```

**For GUI:**
```python
class GUIController:
    def __init__(self):
        # Use dictionaries for flexible access
        self.message_cache: Dict[str, Dict] = {
            'system/state': {},
            'system/telemetry': {},
            'asset/4/telemetry': {},
            'asset/4/state': {},
            # ... etc
        }
    
    def update_from_mqtt(self, topic: str, payload: Dict):
        """Update cache from MQTT message"""
        self.message_cache[topic] = payload
```

### 4.4 Unified Message Bus Interface

```python
class MessageBusData:
    """Unified message bus data storage"""
    
    def __init__(self):
        # Structured data for FSM/core logic
        self.system_state: SystemState = None
        self.system_telemetry: SystemTelemetry = None
        self.asset_states: Dict[str, AssetState] = {}
        self.asset_telemetry: Dict[str, AssetTelemetry] = {}
        
        # Raw data cache for GUI/flexible access
        self.raw_cache: Dict[str, Dict] = {}
        
        # Settings and configuration
        self.settings: Dict[str, Any] = {}
        self.config: Dict[str, Any] = {}
    
    def update_from_mqtt(self, topic: str, payload: Dict):
        """Update both structured and raw data"""
        # Update raw cache
        self.raw_cache[topic] = payload
        
        # Update structured data based on topic
        if topic.endswith('/system/state'):
            self.system_state = SystemState(**payload)
        elif topic.endswith('/system/telemetry'):
            self.system_telemetry = SystemTelemetry(**payload)
        elif '/asset/' in topic and topic.endswith('/telemetry'):
            asset_id = self._extract_asset_id(topic)
            self.asset_telemetry[asset_id] = AssetTelemetry(**payload)
        # ... etc
```

---

## 5. Topic Size Limits and Recommendations

### 5.1 MQTT Message Size Limits
- **MQTT Standard**: Maximum payload size is 256MB (theoretical)
- **Practical Limit**: Most brokers recommend < 1MB per message
- **Recommended Limit**: < 100KB per message for reliable operation
- **Optimal Size**: < 10KB per message for best performance

### 5.2 Topic Splitting Strategy

**Power-Critical Topics** (Small, Fast):
- `site/{site_id}/asset/{asset_id}/power` - ~200 bytes
- Published at 10s intervals
- Contains only power balance critical data

**Complete Telemetry Topics** (Larger, Less Frequent):
- `site/{site_id}/asset/{asset_id}/telemetry` - ~2-5KB
- Published at 10s intervals
- Contains all 30-40 parameters

**Fault/Breaker Topics** (Small, High Frequency):
- `site/{site_id}/asset/{asset_id}/faults` - ~200 bytes
- `site/{site_id}/asset/{asset_id}/breakers` - ~200 bytes
- Published at 4Hz (4 times per second)

**Configuration Topics** (Large, Rarely Changes):
- `site/{site_id}/system/config` - ~10-50KB
- Published only on configuration changes
- Contains all asset configurations

### 5.3 Recommended Approach

✅ **Split Power Data**: Separate power-critical data into `/power` topics
- Faster processing for power balance calculations
- Smaller message size
- Can be subscribed separately

✅ **Full Telemetry**: Keep complete telemetry in `/telemetry` topics
- All parameters available when needed
- Published at 10s intervals (acceptable size)

✅ **High-Frequency Topics**: Separate faults/breakers for 4Hz updates
- Small message size
- Rapid fault detection

✅ **Configuration Separate**: All static config in `/system/config`
- Published only on changes
- Can be large (acceptable)

### 5.4 Parameter Count Recommendations

| Topic Type | Max Parameters | Typical Size | Update Rate |
|------------|----------------|--------------|-------------|
| Power (critical) | 5-10 | < 500 bytes | 10s |
| Complete Telemetry | 30-40 | 2-5 KB | 10s |
| Faults/Breakers | 5-10 | < 500 bytes | 4Hz |
| Configuration | Unlimited | 10-50 KB | On change |
| State | 10-20 | < 1 KB | 10s |

## 6. Historical Data Publishing

### 6.1 Averaging Intervals

**1-Minute Averages:**
- Topic: `site/{site_id}/asset/{asset_id}/telemetry/1min`
- Published: Every 1 minute
- Contains: Average, min, max, count for all telemetry parameters
- Use Case: Short-term trending, database storage

**5-Minute Averages:**
- Topic: `site/{site_id}/asset/{asset_id}/telemetry/5min`
- Published: Every 5 minutes
- Contains: Average, min, max, count for all telemetry parameters
- Use Case: Medium-term trending, analysis

**Hourly Aggregates:**
- Topic: `site/{site_id}/asset/{asset_id}/telemetry/hourly`
- Published: Every 1 hour
- Contains: Aggregated statistics (avg, min, max, sum, count)
- Use Case: Long-term analysis, reporting

### 6.2 State Changes and Faults

**State Changes:**
- Published immediately (not averaged)
- Topic: `site/{site_id}/asset/{asset_id}/state`
- Also published to: `site/{site_id}/system/events`

**Faults:**
- Published immediately (not averaged)
- Topic: `site/{site_id}/asset/{asset_id}/faults`
- Also published to: `site/{site_id}/system/alarms`

## 7. Adapter Architecture

### 7.1 Lane 1 Python Adapters

**Purpose**: Translate PLC/embedded controller data to MQTT

**Responsibilities**:
1. Read data from PLCs via Modbus TCP
2. Read data from embedded controllers
3. Calculate averages (1-min, 5-min)
4. Publish to MQTT at appropriate frequencies:
   - Most data: 10 seconds
   - Breaker status & faults: 4Hz
5. Publish historical data:
   - 1-minute averages: Every minute
   - 5-minute averages: Every 5 minutes
   - Hourly aggregates: Every hour

**Adapter Topics**:
- Adapters publish to: `site/{site_id}/asset/{asset_id}/*`
- Adapters subscribe to: `site/{site_id}/command/{asset_id}/*`

**Example Adapter Structure**:
```
adapters/
├── plc_adapter.py          # Main PLC adapter
├── generator_adapter.py    # Generator-specific adapter
├── battery_adapter.py      # Battery adapter
├── pv_adapter.py           # PV adapter
└── loadbank_adapter.py     # Load bank adapter
```

---

## 8. Emissions Calculations

### 8.1 Emissions Factors (from Config)

Each generator has emissions factors in `system/config`:
- `nox_lb_mmbtu`: NOx emissions (lb/MMBtu)
- `co_lb_mmbtu`: CO emissions (lb/MMBtu)
- `pm_lb_mmbtu`: PM emissions (lb/MMBtu)
- `pm10_lb_mmbtu`: PM10 emissions (lb/MMBtu)
- `vom_lb_mmbtu`: VOM emissions (lb/MMBtu)
- `so2_lb_mmbtu`: SO2 emissions (lb/MMBtu)
- `haps_lb_mmbtu`: HAPS emissions (lb/MMBtu)
- `form_lb_mmbtu`: Formaldehyde emissions (lb/MMBtu)

### 8.2 Emissions Calculation

**Required Data**:
- Fuel flow (from telemetry): `fuel_flow_kg_h`
- Heat rate (from config, based on load %): `hr_100`, `hr_75`, `hr_50`
- Emissions factors (from config): jurisdiction-dependent

**Calculation**:
1. Determine heat rate based on current load percentage
2. Calculate MMBtu/h: `mmbtu_per_hour = (power_kw * heat_rate) / 1000`
3. Calculate emissions: `emissions_lb_h = mmbtu_per_hour * emissions_factor`

**Emissions Payload** (can be added to telemetry or separate topic):
```json
{
  "timestamp": "2025-10-01T12:00:00Z",
  "asset_id": "4",
  "asset_type": "Gen",
  "emissions": {
    "nox_lb_h": 0.25,
    "co_lb_h": 0.03,
    "pm_lb_h": 0.009,
    "pm10_lb_h": 0.00007,
    "vom_lb_h": 0.02,
    "so2_lb_h": 0.0005,
    "haps_lb_h": 0.03,
    "form_lb_h": 0.01
  },
  "fuel_consumption": {
    "fuel_flow_kg_h": 200.0,
    "heat_rate_btu_kwh": 11000,
    "load_percent": 50.8
  }
}
```

## 9. Recommendations

### 9.1 Topic Organization
✅ **Recommended**: Use the hierarchical structure proposed above
- Clear separation of concerns
- Easy to subscribe to specific data types
- Scalable for multiple sites/assets
- **Power-critical data split** for fast access

### 9.2 Configuration vs Live Data
✅ **Recommended**: Strict separation
- **Configuration**: All static parameters in `system/config`
  - Generator: capacity, heat rates, emissions factors, temperature derating
  - Battery: capacity, max_charge, max_discharge
  - PV: capacity
  - Load Bank: max_load, step_size
- **Live Data**: Only operational/measured values in telemetry
  - Power output, temperatures, status, etc.

### 9.3 Data Structure
✅ **Recommended**: Hybrid approach
- **Dataclasses** for FSM/core logic (fast, type-safe)
- **Dictionaries** for GUI/flexible access
- **Unified interface** that maintains both

### 9.4 Update Strategy
✅ **Recommended**:
- **State changes**: Publish immediately (retain=True)
- **Telemetry**: 10 seconds (retain=True)
- **Power data**: 10 seconds (retain=True) - separate topic for speed
- **Faults/Breakers**: 4Hz (retain=True) - high frequency
- **Commands**: Publish on-demand (retain=False)
- **Alarms/Events**: Publish immediately (retain=False)
- **Averages**: 1-min, 5-min, hourly (retain=True)

### 9.5 Adapter Architecture
✅ **Recommended**:
- **Python adapters** (Lane 1) read from PLCs/embedded controllers
- **Adapters publish** directly to MQTT
- **Adapters subscribe** to commands from controller
- **Controller** can also use Modbus TCP as fallback
- **Both protocols** supported simultaneously

---

## 10. Summary of Changes from Original Proposal

### 10.1 Key Updates

1. **Separated Configuration from Live Data**
   - All static config parameters moved to `system/config`
   - Live telemetry contains only operational/measured values

2. **Added Missing Generator Parameters**
   - Heat rates: HR100, HR75, HR50
   - Temperature derating: CapacitykW80, CapacitykW100
   - All emissions factors: NOX, CO, PM, PM10, VOM, SO2, HAPS, FORM

3. **Split Power Data**
   - Separate `/power` topics for power-critical data
   - Smaller, faster messages for power balance calculations
   - Complete telemetry still available in `/telemetry` topics

4. **Updated Frequencies**
   - Most data: 10 seconds
   - Breaker status & faults: 4Hz (4 times per second)
   - Averages: 1-min, 5-min, hourly

5. **Added Adapter Architecture**
   - Lane 1 Python adapters for PLC/embedded controller translation
   - Adapters handle averaging and historical data publishing

6. **Added Emissions Calculations**
   - Emissions factors in config
   - Calculation methodology documented

## 11. Next Steps

1. **Review and approve** this updated proposal
2. **Confirm topic splitting strategy** (power vs complete telemetry)
3. **Implement data structures** in Python
4. **Implement MQTT interface** with topic management
5. **Implement adapter framework** for Lane 1
6. **Test with simulator** and PLC

---

**End of Proposal**

