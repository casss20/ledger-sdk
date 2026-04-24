"""
Citadel framework integrations.

Provides governed wrappers for popular AI agent frameworks:
- K2.6 (Moonshot AI)
- LangGraph
- Codex (OpenAI)
- Claude Code (Anthropic)
- LangChain
- CrewAI
- AutoGen
- OpenAI
- Anthropic
- Kimi
"""

from .k2_6 import (
    GovernedK26Agent,
    GovernedK26Task,
    GovernedK26Workflow,
    K26GovernanceServer,
)
from .langgraph import (
    GovernedNode,
    GovernedStateGraph,
    LangGraphGovernanceServer,
)
from .codex import (
    GovernedCodex,
    CodexGovernanceServer,
)
from .claude_code import (
    GovernedClaudeCode,
    ClaudeCodeGovernanceServer,
)

__all__ = [
    # K2.6
    "GovernedK26Agent",
    "GovernedK26Task",
    "GovernedK26Workflow",
    "K26GovernanceServer",
    # LangGraph
    "GovernedNode",
    "GovernedStateGraph",
    "LangGraphGovernanceServer",
    # Codex
    "GovernedCodex",
    "CodexGovernanceServer",
    # Claude Code
    "GovernedClaudeCode",
    "ClaudeCodeGovernanceServer",
]