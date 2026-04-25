"""Citadel Core — Fundamental governance components.

Implements:
- START.md → start.py (boot orchestration)
- RUNTIME.md → runtime.py (activation cycle)
- CONSTITUTION.md → constitution.py (behavioral constraints)
- GOVERNOR.md → governor.py (strategic oversight, intervention)
- EXECUTOR.md → executor.py (execution momentum)

These are the foundation. All other layers depend on core.

SOURCE OF TRUTH: citadel/core/*.md files
If Python code contradicts MD files, MD files are correct.
"""

from .constitution import (
    Constitution,
    ConstitutionalRule,
    ConstitutionViolation,
    RuleType,
    SAFETY_CONSTITUTION,
    TRANSPARENCY_CONSTITUTION,
    PRIVACY_CONSTITUTION,
    DEFAULT_CONSTITUTION,
)
from .governor import Governor, EscalationLevel, ExecutionLocked, get_governor
from .executor import Executor, ExecutionMode, AutonomyMode, executor, ExecutionLocked as ExecutorLocked
from .runtime import (
    Runtime,
    RuntimeContext,
    RuntimeDecision,
    PathType,
    Layer,
    get_runtime,
)

__all__ = [
    # Constitution
    "Constitution",
    "ConstitutionalRule",
    "ConstitutionViolation",
    "RuleType",
    "SAFETY_CONSTITUTION",
    "TRANSPARENCY_CONSTITUTION",
    "PRIVACY_CONSTITUTION",
    "DEFAULT_CONSTITUTION",
    # Governor
    "Governor",
    "EscalationLevel",
    "ExecutionLocked",
    "get_governor",
    # Executor
    "Executor",
    "ExecutionMode",
    "AutonomyMode",
    "executor",
    "ExecutorLocked",
    # Runtime
    "Runtime",
    "RuntimeContext",
    "RuntimeDecision",
    "PathType",
    "Layer",
    "get_runtime",
]