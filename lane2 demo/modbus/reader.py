"""
Bulk Modbus reads from PLC
"""
import asyncio
import time
import logging
from typing import Dict, Any
from .client import ModbusClient
from .map_loader import load_modbus_map
from buffer.sqlite_buffer import enqueue_record

logger = logging.getLogger(__name__)


class ModbusReader:
    """Reads all Modbus registers defined in config"""
    
    def __init__(self):
        modbus_config = load_modbus_map()
        server_config = modbus_config.get("modbus", {}).get("server", {})
        self.client = ModbusClient(
            host=server_config.get("host", "localhost"),
            port=server_config.get("port", 502)
        )
        self.map = modbus_config
        self.unit_id = server_config.get("unit_id", 1)
        self.last_message_time: Optional[float] = None
    
    async def connect(self):
        """Connect to Modbus client"""
        await self.client.connect()
        logger.info("Modbus client connected")
    
    async def disconnect(self):
        """Disconnect from Modbus client"""
        await self.client.disconnect()
        logger.info("Modbus client disconnected")
    
    def _decode_register(self, value: int, tag: str) -> Any:
        """
        Decode register value based on tag type
        For now, return as-is; can be extended for scaling, data types, etc.
        """
        return value
    
    async def read_all(self) -> Dict[str, Any]:
        """
        Read all registers from modbus_map.yaml
        Decodes data and writes to SQLite buffer
        """
        import time
        self.last_message_time = time.time()
        
        if not self.client.client:
            logger.warning("Modbus client not connected")
            return {}
        
        data = {}
        modbus_config = self.map.get("modbus", {})
        telemetry = modbus_config.get("telemetry", {})
        
        try:
            # Read telemetry registers by device type
            for device_type, registers in telemetry.items():
                device_data = {}
                
                for reg_def in registers:
                    address = reg_def.get("address")
                    tag = reg_def.get("tag")
                    reg_type = reg_def.get("type", "input_register")
                    count = reg_def.get("count", 1)
                    
                    if not address or not tag:
                        continue
                    
                    try:
                        # Read register(s)
                        # pymodbus uses 0-based addressing
                        # Input registers (3xxxx) start at 30001 -> address 0
                        # Holding registers (4xxxx) start at 40001 -> address 0
                        if reg_type == "input_register":
                            # Input registers: 30001 -> 0, 30002 -> 1, etc.
                            modbus_address = address - 30001
                            result = await self.client.client.read_input_registers(
                                modbus_address,
                                count,
                                unit=self.unit_id
                            )
                        elif reg_type == "holding_register":
                            # Holding registers: 40001 -> 0, 40002 -> 1, etc.
                            modbus_address = address - 40001
                            result = await self.client.client.read_holding_registers(
                                modbus_address,
                                count,
                                unit=self.unit_id
                            )
                        else:
                            logger.warning(f"Unknown register type: {reg_type}")
                            continue
                        
                        if result.isError():
                            logger.error(f"Error reading {tag} at {address}: {result}")
                            continue
                        
                        # Decode value
                        if count == 1:
                            value = self._decode_register(result.registers[0], tag)
                        else:
                            # For multi-register values, return as list
                            value = [self._decode_register(r, tag) for r in result.registers]
                        
                        device_data[tag] = value
                        
                    except Exception as e:
                        logger.error(f"Error reading register {tag} at {address}: {e}")
                        continue
                
                if device_data:
                    data[device_type] = device_data
            
            # Normalize into dict structure
            normalized = {
                "device": "modbus",
                "data": data,
                "read_at": int(time.time())
            }
            
            # Insert into SQLite buffer
            source = "modbus:plc"
            enqueue_record(source=source, payload=normalized)
            
            logger.debug(f"Buffered Modbus data: {len(data)} device types")
            
        except Exception as e:
            logger.error(f"Error reading Modbus data: {e}", exc_info=True)
        
        return data

