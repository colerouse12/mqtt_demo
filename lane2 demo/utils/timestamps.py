"""
Timestamp utilities
"""
from datetime import datetime
import time


def get_timestamp() -> datetime:
    """Get current UTC timestamp"""
    return datetime.utcnow()


def get_timestamp_ms() -> int:
    """Get current timestamp in milliseconds"""
    return int(time.time() * 1000)

