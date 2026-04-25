"""Citadel System — Core system services.

Implements:
- FOCUS.md → focus.py (anti-distraction)
- HEARTBEAT.md → heartbeat.py (system health)
- SELF-MOD.md → self_mod.py (system evolution)
- START.md → start.py (boot orchestration)

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