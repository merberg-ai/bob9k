from __future__ import annotations


class BaseDetector:
    name = "base"

    def is_available(self) -> bool:
        return True

    def get_status(self) -> dict:
        available = bool(self.is_available())
        return {
            'name': self.name,
            'available': available,
            'enabled_by_config': True,
            'dependency_ok': available,
            'model_ready': available,
            'reason': None if available else 'unavailable',
        }

    def detect(self, frame):
        """Return a list of Detection objects."""
        raise NotImplementedError
