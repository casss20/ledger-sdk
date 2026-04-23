"""
Catalog Pattern — Ledger SDK

Auto-discover governance rules from ledger/core/
Inspired by Weft's catalog architecture.
"""

import pkgutil
import importlib
from pathlib import Path
from typing import Dict, Any, Optional
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


@dataclass
class GovernanceRule:
    """Single source of truth for a governable action."""
    action: str
    resource: str
    flag: str
    risk: str  # "LOW", "MEDIUM", "HIGH"
    approval: str  # "NONE", "SOFT", "HARD"
    
    # Rate limits
    max_daily: Optional[int] = None
    max_hourly: Optional[int] = None
    
    # Validation
    required_fields: list = None
    optional_fields: list = None
    
    # Thresholds
    max_amount: Optional[float] = None  # For financial actions
    max_rows: Optional[int] = None  # For DB actions
    
    # UI
    display_name: Optional[str] = None
    icon: Optional[str] = None
    color: Optional[str] = None
    description: Optional[str] = None
    
    def __post_init__(self):
        if self.required_fields is None:
            self.required_fields = []
        if self.optional_fields is None:
            self.optional_fields = []


class Catalog:
    """
    Auto-discover governance rules from ledger/core/
    Like Weft's catalog/ directory.
    """
    
    def __init__(self):
        self._rules: Dict[str, GovernanceRule] = {}
        self._groups: Dict[str, list[str]] = {
            "communication": ["send_email", "send_slack", "send_discord"],
            "payment": ["stripe_charge", "refund", "create_invoice"],
            "infrastructure": ["github_action", "deploy", "scale_db"],
            "database": ["write_database", "delete_rows", "migrate"],
        }
    
    def load(self) -> None:
        """Auto-discover rules from ledger/core/"""
        ledger_path = Path(__file__).parent.parent / "ledger" / "core"
        
        if not ledger_path.exists():
            logger.warning(f"[Catalog] ledger/core/ not found at {ledger_path}")
            return
        
        for module_info in pkgutil.iter_modules([str(ledger_path)]):
            if module_info.name.startswith("_"):
                continue
            
            try:
                module = importlib.import_module(f"ledger.core.{module_info.name}")
                
                # Look for GOVERNANCE dict in module
                if hasattr(module, "GOVERNANCE"):
                    g = module.GOVERNANCE
                    rule = GovernanceRule(
                        action=g.get("action", module_info.name),
                        resource=g.get("resource", "unknown"),
                        flag=g.get("flag", g.get("action", "unknown")),
                        risk=g.get("risk", "MEDIUM"),
                        approval=g.get("approval", "SOFT"),
                        max_daily=g.get("max_daily"),
                        max_hourly=g.get("max_hourly"),
                        required_fields=g.get("required_fields", []),
                        optional_fields=g.get("optional_fields", []),
                        max_amount=g.get("max_amount"),
                        max_rows=g.get("max_rows"),
                        display_name=g.get("display_name"),
                        icon=g.get("icon"),
                        color=g.get("color"),
                        description=g.get("description"),
                    )
                    self._rules[rule.action] = rule
                    logger.debug(f"[Catalog] Loaded rule: {rule.action}")
                    
            except Exception as e:
                logger.error(f"[Catalog] Failed to load {module_info.name}: {e}")
        
        logger.info(f"[Catalog] Loaded {len(self._rules)} governance rules")
    
    def get(self, action: str) -> Optional[GovernanceRule]:
        """Get rule by action name."""
        return self._rules.get(action)
    
    def get_by_flag(self, flag: str) -> Optional[GovernanceRule]:
        """Get rule by flag."""
        for rule in self._rules.values():
            if rule.flag == flag:
                return rule
        return None
    
    def list_all(self) -> list[GovernanceRule]:
        """List all rules."""
        return list(self._rules.values())
    
    def list_by_group(self, group: str) -> list[GovernanceRule]:
        """List rules in a group."""
        actions = self._groups.get(group, [])
        return [self._rules[a] for a in actions if a in self._rules]
    
    def list_groups(self) -> Dict[str, list[str]]:
        """Get all groups."""
        return self._groups
    
    def classify_risk(self, action: str, context: dict = None) -> str:
        """Classify risk for an action with context."""
        rule = self.get(action)
        if not rule:
            return "MEDIUM"
        
        # Check thresholds
        if rule.max_amount and context:
            amount = context.get("amount", 0)
            if amount > rule.max_amount:
                return "HIGH"
        
        if rule.max_rows and context:
            rows = context.get("estimated_rows", 0)
            if rows > rule.max_rows:
                return "HIGH"
        
        return rule.risk


# Singleton
catalog_instance: Optional[Catalog] = None


def get_catalog() -> Catalog:
    """Get or create the global catalog."""
    global catalog_instance
    if catalog_instance is None:
        catalog_instance = Catalog()
        catalog_instance.load()
    return catalog_instance
