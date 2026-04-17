"""
Feature flags and emergency kill switch.
"""

from dataclasses import dataclass


@dataclass
class Flag:
    name: str
    enabled: bool = True
    reason: str = ""


class KillSwitch:
    def __init__(self) -> None:
        self._flags: dict[str, Flag] = {}

    def register(self, name, enabled=True):
        self._flags.setdefault(name, Flag(name=name, enabled=enabled))

    def is_enabled(self, name):
        f = self._flags.get(name)
        return bool(f and f.enabled)

    def kill(self, name, reason="emergency"):
        f = self._flags.get(name) or Flag(name=name)
        f.enabled = False
        f.reason = reason
        self._flags[name] = f

    def revive(self, name):
        f = self._flags.get(name)
        if f:
            f.enabled, f.reason = True, ""

    def status(self):
        return [f.__dict__ for f in self._flags.values()]