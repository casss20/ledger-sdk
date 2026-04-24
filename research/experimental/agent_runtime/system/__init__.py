"""CITADEL System â€” Core system services.

Implements:
- FOCUS.md â†’ focus.py (anti-distraction)
- HEARTBEAT.md â†’ heartbeat.py (system health)
- SELF-MOD.md â†’ self_mod.py (system evolution)
- START.md â†’ start.py (boot orchestration)

These components handle system-level concerns:
focus protection, health monitoring, self-modification, and startup.
"""

from .focus import Focus, FocusState, CurrentTask, get_focus

__all__ = [
    # Focus
    "Focus",
    "FocusState",
    "CurrentTask",
    "get_focus",
]