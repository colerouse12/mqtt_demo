from sim_plcs.base_plc import BasePLC


class PLC1(BasePLC):
    pass


if __name__ == "__main__":
    plc = PLC1("plc1")
    plc.run()

