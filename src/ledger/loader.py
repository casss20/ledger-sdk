"""
Loads governance markdown by runtime path (Fast/Standard/Structured/High-Risk).
Caches core files — they rarely change. Context files refreshed per session.
"""

from functools import lru_cache
from pathlib import Path
from typing import Literal

Path_ = Literal["fast", "standard", "structured", "high_risk"]

# Use relative path from this file's location
LEDGER_DIR = Path(__file__).resolve().parent.parent.parent / "ledger"

PATH_FILES: dict[Path_, list[str]] = {
    "fast": ["CONSTITUTION.md", "IDENTITY.md"],
    "standard": ["CONSTITUTION.md", "IDENTITY.md", "EXECUTOR.md"],
    "structured": ["CONSTITUTION.md", "IDENTITY.md", "EXECUTOR.md", "PLANNER.md", "CRITIC.md", "FOCUS.md"],
    "high_risk": ["CONSTITUTION.md", "IDENTITY.md", "EXECUTOR.md", "PLANNER.md", "CRITIC.md", "FOCUS.md", "GOVERNOR.md", "ALIGNMENT.md", "FAILURE.md"],
}


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8") if path.exists() else ""


@lru_cache(maxsize=8)
def core_governance(path: Path_) -> str:
    parts = []
    for name in PATH_FILES[path]:
        body = _read(LEDGER_DIR / "core" / name)
        if body:
            parts.append(f"## [{name}]\n{body}")
    return "\n\n---\n\n".join(parts)


def agent_identity(agent: str) -> str:
    folder = LEDGER_DIR / "agents" / agent.lower()
    parts = []
    for fname in ("IDENTITY.md", "SOUL.md"):
        body = _read(folder / fname)
        if body:
            parts.append(f"## [agent:{agent}/{fname}]\n{body}")
    return "\n\n".join(parts)


def session_context(session_id: str) -> str:
    folder = LEDGER_DIR / "context" / session_id
    parts = []
    for fname in ("WORLD.md", "USER.md", "MEMORY.md", "DECISIONS.md"):
        body = _read(folder / fname)
        if body:
            parts.append(f"## [context/{fname}]\n{body}")
    return "\n\n".join(parts)


def build_system_prompt(*, agent: str, path: Path_, session_id: str, task: str) -> str:
    sections = [
        core_governance(path),
        agent_identity(agent),
        session_context(session_id),
        f"## [TASK]\n{task}",
    ]
    return "\n\n===\n\n".join(s for s in sections if s)