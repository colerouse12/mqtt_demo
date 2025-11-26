"""
Launcher for Lane 2 Buffer POC
Starts all components: Bridge Service, PLC Simulator GUI, and Buffer Monitor GUI
"""
import subprocess
import sys
import time
import os
from pathlib import Path

# Get the directory where this script is located
SCRIPT_DIR = Path(__file__).parent
VENV_PYTHON = SCRIPT_DIR.parent / ".venv" / "Scripts" / "python.exe"

# Use venv Python if available, otherwise use system Python
if VENV_PYTHON.exists():
    PYTHON = str(VENV_PYTHON)
else:
    PYTHON = sys.executable

def start_bridge_service():
    """Start the bridge service (main.py)"""
    print("=" * 60)
    print("Starting Bridge Service...")
    print("=" * 60)
    bridge_script = SCRIPT_DIR / "main.py"
    return subprocess.Popen(
        [PYTHON, str(bridge_script)],
        cwd=str(SCRIPT_DIR),
        creationflags=subprocess.CREATE_NEW_CONSOLE if sys.platform == "win32" else 0
    )

def start_plc_simulator():
    """Start the PLC Simulator GUI"""
    print("=" * 60)
    print("Starting PLC Simulator GUI...")
    print("=" * 60)
    plc_script = SCRIPT_DIR / "plc_simulator_gui.py"
    return subprocess.Popen(
        [PYTHON, str(plc_script)],
        cwd=str(SCRIPT_DIR),
        creationflags=subprocess.CREATE_NEW_CONSOLE if sys.platform == "win32" else 0
    )

def start_buffer_gui():
    """Start the Buffer Monitor GUI"""
    print("=" * 60)
    print("Starting Buffer Monitor GUI...")
    print("=" * 60)
    gui_script = SCRIPT_DIR / "buffer_gui.py"
    return subprocess.Popen(
        [PYTHON, str(gui_script)],
        cwd=str(SCRIPT_DIR),
        creationflags=subprocess.CREATE_NEW_CONSOLE if sys.platform == "win32" else 0
    )

def main():
    """Main launcher"""
    print("\n" + "=" * 60)
    print("Lane 2 Buffer POC - Launcher")
    print("=" * 60)
    print("\nThis will start:")
    print("  1. Bridge Service (MQTT → Buffer → Forwarder)")
    print("  2. PLC Simulator GUI (send test messages)")
    print("  3. Buffer Monitor GUI (receive forwarded messages)")
    print("\nMake sure MQTT broker is running on localhost:1883")
    print("=" * 60 + "\n")
    
    processes = []
    
    try:
        # Start bridge service first (give it time to initialize)
        print("Starting components...\n")
        bridge_process = start_bridge_service()
        processes.append(("Bridge Service", bridge_process))
        time.sleep(2)  # Give bridge service time to start
        
        # Start GUIs
        plc_process = start_plc_simulator()
        processes.append(("PLC Simulator", plc_process))
        time.sleep(1)
        
        gui_process = start_buffer_gui()
        processes.append(("Buffer Monitor", gui_process))
        
        print("\n" + "=" * 60)
        print("All components started!")
        print("=" * 60)
        print("\nComponents running:")
        for name, proc in processes:
            status = "✓ Running" if proc.poll() is None else "✗ Stopped"
            print(f"  {name}: {status}")
        
        print("\n" + "=" * 60)
        print("Instructions:")
        print("  1. Use PLC Simulator GUI to send test messages")
        print("  2. Watch Buffer Monitor GUI for forwarded messages")
        print("  3. Close this window to stop all components")
        print("=" * 60 + "\n")
        
        # Wait for user to close
        input("Press Enter to stop all components...\n")
        
    except KeyboardInterrupt:
        print("\n\nStopping all components...")
    except Exception as e:
        print(f"\nError: {e}")
    finally:
        # Cleanup
        print("\nShutting down components...")
        for name, proc in processes:
            try:
                if proc.poll() is None:  # Still running
                    print(f"  Stopping {name}...")
                    proc.terminate()
                    proc.wait(timeout=5)
            except Exception as e:
                print(f"  Error stopping {name}: {e}")
                try:
                    proc.kill()
                except:
                    pass
        
        print("\nAll components stopped.")
        print("=" * 60)


if __name__ == "__main__":
    main()

