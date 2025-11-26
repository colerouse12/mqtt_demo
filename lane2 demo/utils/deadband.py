"""
Change-of-value logic (deadband filtering)
"""
from typing import Any, Optional


class DeadbandFilter:
    """Filters values that haven't changed beyond threshold"""
    
    def __init__(self, threshold: float = 0.01):
        self.threshold = threshold
        self.last_values = {}
    
    def should_publish(self, tag: str, value: Any) -> bool:
        """Check if value change exceeds deadband"""
        if tag not in self.last_values:
            self.last_values[tag] = value
            return True
        
        last_value = self.last_values[tag]
        if isinstance(value, (int, float)) and isinstance(last_value, (int, float)):
            change = abs(value - last_value) / max(abs(last_value), 1e-6)
            if change >= self.threshold:
                self.last_values[tag] = value
                return True
            return False
        
        # Non-numeric values always publish
        if value != last_value:
            self.last_values[tag] = value
            return True
        
        return False

