"""
Loads Modbus register map from shared/config/modbus_map.yaml
"""
import yaml
from pathlib import Path
from typing import Dict, Any


def load_modbus_map() -> Dict[str, Any]:
    """Load authoritative Modbus address map"""
    config_path = Path(__file__).parent.parent.parent / "shared" / "config" / "modbus_map.yaml"
    with open(config_path, 'r') as f:
        return yaml.safe_load(f)

