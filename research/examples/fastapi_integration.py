"""
FastAPI Integration Example — Governance initialization wrapper.

This shows how to wire Citadel SDK into a FastAPI application.
Copy this file to your project and adapt as needed.
"""

import os
import logging
from typing import Callable, Awaitable, Any

logger = logging.getLogger(__name__)

# Lazy import to avoid circular deps
_gov = None


def get_governance():
    """Get or create the Citadel governance instance."""
    global _gov
    if _gov is None:
        try:
            from citadel.sdk import Citadel
        except ImportError:
            logger.warning("citadel-sdk not installed. Governance disabled.")
            return None

        audit_dsn = os.getenv(
            "LEDGER_AUDIT_DSN",
            "postgresql://user:pass@localhost/postgres"
        )
        _gov = Citadel(audit_dsn=audit_dsn, agent="app")
    return _gov


async def start_governance():
    """Initialize governance at app startup."""
    gov = get_governance()
    if gov:
        try:
            await gov.start()
            logger.info("✅ Governance layer started")

            # Register kill switches for critical actions
            gov.killsw.register("agent_spawn", enabled=True)
            gov.killsw.register("agent_execute", enabled=True)
            gov.killsw.register("tool_call", enabled=True)
            gov.killsw.register("output_publish", enabled=True)

        except Exception as e:
            logger.error(f"Failed to start governance: {e}")


async def stop_governance():
    """Shut down governance at app shutdown."""
    global _gov
    if _gov:
        try:
            await _gov.stop()
            logger.info("✅ Governance layer stopped")
            _gov = None
        except Exception as e:
            logger.error(f"Error stopping governance: {e}")


async def set_approval_hook(hook: Callable[[dict], Awaitable[bool]]):
    """
    Set the approval hook. Called when an action needs HARD approval.
    """
    gov = get_governance()
    if gov:
        gov.set_approval_hook(hook)
        logger.info("✅ Approval hook registered")


def build_system_prompt(task: str, agent_name: str = "default", session_id: str = "default") -> str:
    """
    Build system prompt with governance constitution + markdown layers.
    Call this when constructing LLM prompts.
    """
    gov = get_governance()
    if not gov:
        return ""

    return gov.build_prompt(
        task=task,
        session_id=session_id,
        agent=agent_name,
    )


class GovernanceManager:
    """Convenience wrapper for governance lifecycle."""

    async def start(self):
        await start_governance()

    async def stop(self):
        await stop_governance()

    def get(self):
        return get_governance()

    def build_prompt(self, task, agent="default", session="default"):
        return build_system_prompt(task, agent, session)

    async def set_approval_hook(self, hook):
        await set_approval_hook(hook)
