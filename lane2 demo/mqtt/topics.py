"""
Loads MQTT topic definitions from shared/config/mqtt_topics.yaml
"""
import yaml
from pathlib import Path
from typing import Dict, str


def load_topic_map() -> Dict[str, str]:
    """Load topic definitions"""
    config_path = Path(__file__).parent.parent.parent / "shared" / "config" / "mqtt_topics.yaml"
    with open(config_path, 'r') as f:
        return yaml.safe_load(f)


def get_topic(asset_type: str, asset_id: str, data_type: str) -> str:
    """Construct MQTT topic from components"""
    # TODO: Implement topic construction
    return f"dispatch365/{asset_type}/{asset_id}/{data_type}"

