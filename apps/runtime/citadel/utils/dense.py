"""
Dense Syntax — Citadel SDK

Like Weft's "Dense for AI generation":
- Constrained grammar so AI writes correct code on first try
- Dense syntax = fewer tokens
- Immutable configs validated at definition time
"""

from typing import Any, Dict, List, Optional, Union, Literal
from dataclasses import dataclass, field
import re
import logging

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class DenseRule:
    """
    Compact, immutable governance rule.
    Like Weft's dense node definitions.
    """
    action: str
    resource: str
    flag: str
    risk: Literal["LOW", "MEDIUM", "HIGH"]
    approval: Literal["NONE", "SOFT", "HARD"]
    
    # Compact field spec: "field1, field2, field3"
    requires: str = ""  # Required fields
    optional: str = ""  # Optional fields
    
    # Rate limits as compact string: "100/hour, 1000/day"
    limits: str = ""
    
    # Thresholds
    max_amount: Optional[float] = None
    max_rows: Optional[int] = None
    
    def __post_init__(self):
        # Validate action is snake_case
        if not re.match(r'^[a-z][a-z0-9_]*$', self.action):
            raise ValueError(f"Action '{self.action}' must be snake_case")
        
        # Validate requires/optional don't overlap
        req_set = set(self._parse_fields(self.requires))
        opt_set = set(self._parse_fields(self.optional))
        overlap = req_set & opt_set
        if overlap:
            raise ValueError(f"Fields cannot be both required and optional: {overlap}")
    
    def _parse_fields(self, spec: str) -> List[str]:
        """Parse comma-separated field spec."""
        return [f.strip() for f in spec.split(",") if f.strip()]
    
    def _parse_limits(self) -> Dict[str, int]:
        """Parse limits string into dict."""
        result = {}
        if not self.limits:
            return result
        
        for part in self.limits.split(","):
            part = part.strip()
            if "/" in part:
                count, period = part.split("/")
                result[period.strip()] = int(count.strip())
        return result
    
    def to_expanded(self) -> Dict[str, Any]:
        """Expand dense rule to full config dict."""
        limits = self._parse_limits()
        
        return {
            "action": self.action,
            "resource": self.resource,
            "flag": self.flag or self.action,
            "risk": self.risk,
            "approval": self.approval,
            "required_fields": self._parse_fields(self.requires),
            "optional_fields": self._parse_fields(self.optional),
            "max_daily": limits.get("day"),
            "max_hourly": limits.get("hour"),
            "max_amount": self.max_amount,
            "max_rows": self.max_rows,
        }
    
    @property
    def has_hard_approval(self) -> bool:
        return self.approval == "HARD"
    
    @property
    def is_high_risk(self) -> bool:
        return self.risk == "HIGH"


class gov:
    """
    Dense DSL for governance rules.
    
    Like Weft's constrained grammar for AI generation.
    
    Usage:
        from citadel.dense import gov
        
        EMAIL = gov.action(
            "send_email",
            resource="outbound_email",
            risk="HIGH",
            approval="HARD",
            requires="to, subject, body",
            optional="cc, bcc, attachments",
            limits="20/hour, 100/day"
        )
        
        # Access expanded config
        config = EMAIL.to_expanded()
    """
    
    @staticmethod
    def action(
        name: str,
        resource: str,
        risk: Literal["LOW", "MEDIUM", "HIGH"],
        approval: Literal["NONE", "SOFT", "HARD"],
        requires: str = "",
        optional: str = "",
        limits: str = "",
        max_amount: Optional[float] = None,
        max_rows: Optional[int] = None,
        flag: Optional[str] = None,
    ) -> DenseRule:
        """
        Define a governance action with compact syntax.
        
        Args:
            name: Action name (snake_case, e.g., "send_email")
            resource: Resource being accessed (e.g., "outbound_email")
            risk: Risk level (LOW, MEDIUM, HIGH)
            approval: Approval level (NONE, SOFT, HARD)
            requires: Comma-separated required fields
            optional: Comma-separated optional fields
            limits: Rate limits (e.g., "20/hour, 100/day")
            max_amount: Max dollar amount for financial actions
            max_rows: Max rows for DB actions
            flag: Kill switch flag (defaults to action name)
        
        Returns:
            Immutable DenseRule
        """
        return DenseRule(
            action=name,
            resource=resource,
            flag=flag or name,
            risk=risk,
            approval=approval,
            requires=requires,
            optional=optional,
            limits=limits,
            max_amount=max_amount,
            max_rows=max_rows,
        )
    
    @staticmethod
    def email(
        name: str = "send_email",
        risk: Literal["MEDIUM", "HIGH"] = "HIGH",
        approval: Literal["SOFT", "HARD"] = "HARD",
        limits: str = "20/hour, 100/day"
    ) -> DenseRule:
        """Preset for email actions."""
        return gov.action(
            name=name,
            resource="outbound_email",
            risk=risk,
            approval=approval,
            requires="to, subject, body",
            optional="cc, bcc, attachments",
            limits=limits,
        )
    
    @staticmethod
    def payment(
        name: str = "stripe_charge",
        max_amount: float = 10000.0,
        limits: str = "10/hour, 50/day"
    ) -> DenseRule:
        """Preset for payment actions."""
        return gov.action(
            name=name,
            resource="stripe",
            risk="HIGH",
            approval="HARD",
            requires="amount, customer_id",
            optional="description, metadata",
            limits=limits,
            max_amount=max_amount,
        )
    
    @staticmethod
    def database(
        name: str = "write_database",
        max_rows: int = 10000,
        limits: str = "100/hour, 1000/day"
    ) -> DenseRule:
        """Preset for database actions."""
        return gov.action(
            name=name,
            resource="production_db",
            risk="MEDIUM",
            approval="HARD",
            requires="query",
            optional="params, transaction_id",
            limits=limits,
            max_rows=max_rows,
        )


# Example usage showing density
EMAIL = gov.email()
PAYMENT = gov.payment(max_amount=5000.0)
DATABASE = gov.database()

# Custom examples
SLACK = gov.action(
    "send_slack",
    resource="slack",
    risk="MEDIUM",
    approval="SOFT",
    requires="channel, message",
    limits="100/hour, 500/day"
)

GITHUB = gov.action(
    "github_action",
    resource="github",
    risk="HIGH",
    approval="HARD",
    requires="workflow, ref",
    optional="inputs",
    limits="10/hour, 50/day"
)

__all__ = ['gov', 'DenseRule']
