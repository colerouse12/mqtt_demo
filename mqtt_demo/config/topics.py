# Topic templates for use throughout the system

# PLC topics (PLCs publish/subscribe to these)
CONTROL = "plc/control/{plc}"
STATUS = "plc/status/{plc}"
TELEMETRY = "plc/telemetry/{plc}"
HEARTBEAT = "plc/heartbeat/{plc}"
EVENT = "plc/event/{plc}"
SETPOINT = "plc/setpoint/{plc}"

# HMI topics (HMI publishes commands, subscribes to data)
HMI_COMMAND = "hmi/command/{plc}"
HMI_STATUS = "hmi/status/{plc}"
HMI_TELEMETRY = "hmi/telemetry/{plc}"
HMI_HEARTBEAT = "hmi/heartbeat/{plc}"

# Lightbulb topics
LIGHTBULB_CONTROL = "lightbulb/control/{bulb}"
LIGHTBULB_STATUS = "lightbulb/status/{bulb}"
HMI_LIGHTBULB_CONTROL = "hmi/lightbulb/control/{bulb}"
HMI_LIGHTBULB_STATUS = "hmi/lightbulb/status/{bulb}"

# Substation topics
SUBSTATION_STATUS = "substation/status/{substation}"
SUBSTATION_POWER_REQUEST = "substation/power_request/{device}"
SUBSTATION_POWER_RESPONSE = "substation/power_response/{device}"
HMI_SUBSTATION_STATUS = "hmi/substation/status/{substation}"

