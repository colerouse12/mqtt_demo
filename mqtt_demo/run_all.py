"""
Simple launcher that runs multiple PLCs in parallel threads and opens the HMI.
"""
import threading
import sys
import time
from sim_plcs.plc1 import PLC1
from sim_plcs.plc2 import PLC2
from sim_plcs.lightbulb import Lightbulb
from sim_plcs.substation import SmartSubstation
from central_controller.central_mqtt import CentralController


def start_plc(plc_class, plc_id):
    plc = plc_class(plc_id)
    plc.run()


def start_lightbulb(bulb_id, power_consumption=0.1):
    bulb = Lightbulb(bulb_id, power_consumption=power_consumption)
    bulb.run()


if __name__ == "__main__":
    threads = []

    # Start PLCs
    print("Starting PLCs...")
    threads.append(threading.Thread(target=start_plc, args=(PLC1, "plc1")))
    threads.append(threading.Thread(target=start_plc, args=(PLC2, "plc2")))
    
    # Start smart hub substation
    print("Starting smart hub substation...")
    substation = SmartSubstation("substation1")
    substation_thread = threading.Thread(target=substation.run)
    substation_thread.daemon = True
    substation_thread.start()
    
    # Give substation time to connect
    time.sleep(1)
    
    # Start lightbulbs
    print("Starting lightbulbs...")
    threads.append(threading.Thread(target=start_lightbulb, args=("bulb1", 0.1)))
    threads.append(threading.Thread(target=start_lightbulb, args=("bulb2", 0.15)))
    threads.append(threading.Thread(target=start_lightbulb, args=("bulb3", 0.12)))
    threads.append(threading.Thread(target=start_lightbulb, args=("bulb4", 0.08)))
    
    for t in threads:
        t.daemon = True
        t.start()

    # Start central controller
    print("Starting central controller...")
    central = CentralController()

    # Give PLCs time to connect
    print("Waiting for PLCs to connect...")
    time.sleep(2)

    # Start HMI in main thread (Qt requires main thread)
    print("Starting HMI...")
    print("System running. Use the HMI to control generators:")
    print("  - Use sliders to set kW output")
    print("  - Use TURN ON/OFF buttons to control generators")
    print("  - Monitor fuel levels and consumption")
    
    # Execute the HMI launcher
    try:
        from simple_hmi.run_hmi import run as hmi_run
        hmi_run()
    except Exception as e:
        print(f"Error starting HMI: {e}")
        import traceback
        traceback.print_exc()
        print("Make sure PySide6 is installed: py -m pip install PySide6")
        input("Press Enter to exit...")

