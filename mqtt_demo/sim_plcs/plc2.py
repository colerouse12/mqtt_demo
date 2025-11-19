import random
from sim_plcs.base_plc import BasePLC


class PLC2(BasePLC):
    """PLC2 with different generator characteristics."""
    def __init__(self, plc_id, broker="localhost"):
        # PLC2 has a smaller fuel tank
        super().__init__(plc_id, broker, max_fuel=80.0)


if __name__ == "__main__":
    plc = PLC2("plc2")
    plc.run()

