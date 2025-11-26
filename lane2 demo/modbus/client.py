"""
pymodbus client wrapper
"""
from pymodbus.client import AsyncModbusTcpClient
from typing import Optional


class ModbusClient:
    """Wrapper around pymodbus AsyncModbusTcpClient"""
    
    def __init__(self, host: str = "localhost", port: int = 502):
        self.host = host
        self.port = port
        self.client: Optional[AsyncModbusTcpClient] = None
    
    async def connect(self):
        """Connect to Modbus server"""
        self.client = AsyncModbusTcpClient(host=self.host, port=self.port)
        await self.client.connect()
    
    async def disconnect(self):
        """Disconnect from Modbus server"""
        if self.client:
            await self.client.close()

