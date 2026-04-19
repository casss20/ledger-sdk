"""Ledger Core — Fundamental governance components.

Implements:
- GOVERNOR.md → governor.py (strategic oversight, intervention)
- CONSTITUTION.md → constitution.py (behavioral constraints)
- RUNTIME.md → runtime.py (activation model)
- EXECUTOR.md → executor.py (execution momentum)

These are the foundation. All other layers depend on core.
"""

from .governor import Governor, EscalationLevel, ExecutionLocked, get_governor

__all__ = [
    "Governor",
    "EscalationLevel", 
    "ExecutionLocked",
    "get_governor",
]
