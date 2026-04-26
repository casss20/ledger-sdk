"""
Citadel Router - Governance-aware output routing

The Citadel Router inspects agent outputs and produces routing decisions
to determine channel, approval requirements, and execution.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from citadel.utils.schema import (
    AgentOutput,
    ApprovalLevel,
    OutputType,
)


class RoutingDecision:
    """
    A routing decision produced by the Citadel Router.
    
    Attributes:
        output: The agent output being routed
        channel_id: Target channel identifier (e.g., "slack", "email")
        can_auto_route: Whether this output can proceed automatically
        requires_approval: Whether human approval is required
        reason: Human-readable explanation of the decision
        risk_level: low | medium | high
    """
    def __init__(
        self,
        output: AgentOutput,
        channel_id: Optional[str],
        can_auto_route: bool,
        requires_approval: bool,
        reason: str,
        risk_level: str = "low",
    ):
        self.output = output
        self.channel_id = channel_id
        self.can_auto_route = can_auto_route
        self.requires_approval = requires_approval
        self.reason = reason
        self.risk_level = risk_level
        self.decided_at = datetime.utcnow().isoformat()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "output_id": self.output.id,
            "output_type": self.output.output_type,
            "agent_name": self.output.agent_name,
            "channel_id": self.channel_id,
            "can_auto_route": self.can_auto_route,
            "requires_approval": self.requires_approval,
            "reason": self.reason,
            "risk_level": self.risk_level,
            "decided_at": self.decided_at,
        }


class CitadelRouter:
    """
    Central routing authority - sits between agents and platform adapters.

    Usage:
        router = CitadelRouter()
        decision = router.decide(output)

        if decision.requires_approval:
            # Hold in approval queue - show to human
            pass
        else:
            # Auto-route
            result = await execute(decision)
    """

    def __init__(self):
        self._approval_rules = {
            OutputType.LISTING: (True, "high", "Listings always require human approval"),
            OutputType.MESSAGE: (True, "high", "Messages always require human approval"),
            OutputType.ASSET: (True, "medium", "Assets require approval before use"),
            OutputType.RESEARCH: (False, "low", "Research is informational"),
            OutputType.TASK: (False, "low", "Tasks are internal orchestration"),
            OutputType.GENERIC: (True, "medium", "Unknown type - held for review"),
        }

    def decide(self, output: AgentOutput, channel_id: Optional[str] = None) -> RoutingDecision:
        """
        Inspect an agent output and produce a routing decision.
        Does NOT execute anything - just evaluates.
        """
        requires_approval, risk_level, reason = self._evaluate_risk(output)

        can_auto = (
            not requires_approval
            and channel_id is not None
        )

        return RoutingDecision(
            output=output,
            channel_id=channel_id,
            can_auto_route=can_auto,
            requires_approval=requires_approval,
            reason=reason,
            risk_level=risk_level,
        )

    def _evaluate_risk(self, output: AgentOutput) -> tuple[bool, str, str]:
        """
        Returns (requires_approval, risk_level, reason).
        These rules are constitution-grade - never bypassed.
        """
        rule = self._approval_rules.get(output.output_type, self._approval_rules[OutputType.GENERIC])
        return rule

    def get_routing_summary(self) -> Dict[str, Any]:
        """Current routing state and approval rules."""
        return {
            "approval_rules": {
                OutputType.LISTING: "HARD - always requires human approval",
                OutputType.MESSAGE: "HARD - always requires human approval",
                OutputType.ASSET: "HARD - requires approval before use",
                OutputType.RESEARCH: "SOFT - informational, no platform action",
                OutputType.TASK: "NONE - internal orchestration",
            },
        }
