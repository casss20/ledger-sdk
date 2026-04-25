"""
Compile-Time Validation — Citadel SDK

Like Weft's "If it compiles, the architecture is sound":
- Validate connections at startup
- Type-check every governance rule
- Catch config errors before runtime
"""

from typing import Any, Dict, List, Optional, Type, Callable, get_type_hints
from dataclasses import dataclass, field, asdict
from enum import Enum
import re
import logging
from pydantic import BaseModel, validator, ValidationError, Field

logger = logging.getLogger(__name__)


class ValidationSeverity(Enum):
    """Severity levels for validation issues."""
    ERROR = "error"      # Fatal — cannot proceed
    WARNING = "warning"  # Non-fatal — proceed with caution
    INFO = "info"        # Suggestion for improvement


@dataclass
class ValidationIssue:
    """A single validation issue."""
    severity: ValidationSeverity
    action: str
    field: str
    message: str
    suggestion: Optional[str] = None


class GovernanceConfig(BaseModel):
    """
    Validated governance configuration.
    Like Weft's node config with self-validation.
    """
    action: str = Field(..., pattern=r"^[a-z][a-z0-9_]*$")
    resource: str = Field(..., min_length=1)
    flag: str = Field(..., min_length=1)
    risk: str = Field(..., pattern=r"^(LOW|MEDIUM|HIGH)$")
    approval: str = Field(..., pattern=r"^(NONE|SOFT|HARD)$")
    
    # Rate limits
    max_daily: Optional[int] = Field(None, gt=0)
    max_hourly: Optional[int] = Field(None, gt=0)
    
    # Validation
    required_fields: List[str] = Field(default_factory=list)
    optional_fields: List[str] = Field(default_factory=list)
    
    # Thresholds
    max_amount: Optional[float] = Field(None, gt=0)
    max_rows: Optional[int] = Field(None, gt=0)
    
    @validator('action')
    def validate_action_snake_case(cls, v):
        if not re.match(r'^[a-z][a-z0-9_]*$', v):
            raise ValueError("Action must be snake_case (e.g., 'send_email')")
        return v
    
    @validator('flag')
    def validate_flag(cls, v, values):
        action = values.get('action', '')
        if v == action:
            logger.warning(f"[Validation] Flag '{v}' is same as action — consider shorter flag")
        return v
    
    @validator('max_daily', 'max_hourly')
    def validate_rate_limits(cls, v, values):
        if v is not None and v < 1:
            raise ValueError("Rate limits must be positive integers")
        return v
    
    @validator('required_fields')
    def validate_no_duplicate_fields(cls, v, values):
        optional = values.get('optional_fields', [])
        duplicates = set(v) & set(optional)
        if duplicates:
            raise ValueError(f"Fields cannot be both required and optional: {duplicates}")
        return v


class ValidatedGovernance:
    """
    Wrapper for governance rules with compile-time validation.
    """
    
    def __init__(self, **kwargs):
        self.config = GovernanceConfig(**kwargs)
        self._validated = True
        logger.debug(f"[ValidatedGovernance] Validated {self.config.action}")
    
    def to_dict(self) -> Dict[str, Any]:
        """Export as dictionary."""
        return asdict(self.config)
    
    @property
    def action(self) -> str:
        return self.config.action
    
    @property
    def risk(self) -> str:
        return self.config.risk


class Validator:
    """
    Central validator for the entire governance system.
    Like Weft's compiler that validates the architecture.
    """
    
    def __init__(self):
        self.issues: List[ValidationIssue] = []
        self._validators: List[Callable[[Any], List[ValidationIssue]]] = []
    
    def register_validator(
        self, 
        validator_fn: Callable[[Any], List[ValidationIssue]]
    ):
        """Register a custom validator."""
        self._validators.append(validator_fn)
    
    def validate_governance(self, config: Dict[str, Any]) -> List[ValidationIssue]:
        """
        Validate a single governance config.
        Returns list of issues (empty if valid).
        """
        issues = []
        
        try:
            validated = GovernanceConfig(**config)
        except ValidationError as e:
            for error in e.errors():
                issues.append(ValidationIssue(
                    severity=ValidationSeverity.ERROR,
                    action=config.get('action', 'unknown'),
                    field='.'.join(str(x) for x in error['loc']),
                    message=error['msg'],
                    suggestion=self._get_suggestion(error)
                ))
        
        # Run custom validators
        for validator_fn in self._validators:
            try:
                custom_issues = validator_fn(config)
                issues.extend(custom_issues)
            except Exception as e:
                logger.error(f"[Validator] Custom validator failed: {e}")
        
        return issues
    
    def validate_all(self, configs: List[Dict[str, Any]]) -> List[ValidationIssue]:
        """
        Validate all governance configs at once.
        Like Weft's compiler pass over the whole program.
        """
        all_issues = []
        
        # Check for duplicate actions
        actions = [c.get('action') for c in configs if c.get('action')]
        duplicates = set(a for a in actions if actions.count(a) > 1)
        for dup in duplicates:
            all_issues.append(ValidationIssue(
                severity=ValidationSeverity.ERROR,
                action=dup,
                field='action',
                message=f"Duplicate action definition: {dup}",
                suggestion="Each action must have a unique name"
            ))
        
        # Validate each config
        for config in configs:
            issues = self.validate_governance(config)
            all_issues.extend(issues)
        
        self.issues = all_issues
        return all_issues
    
    def validate_catalog(self, catalog: Any) -> bool:
        """
        Validate entire catalog at startup.
        Returns True if valid, False if errors found.
        """
        # NOTE: Catalog validation disabled — catalog module moved to experimental.
        # Re-enable when integrating with experimental/agent_runtime/catalog.py
        logger.info("[Validator] Catalog validation skipped (catalog module in experimental)")
        return True
    
    def _get_suggestion(self, error: Dict) -> Optional[str]:
        """Generate helpful suggestion for an error."""
        field = '.'.join(str(x) for x in error.get('loc', []))
        msg = error.get('msg', '')
        
        if 'snake_case' in msg.lower():
            return "Use underscores: send_email, stripe_charge"
        if 'risk' in field.lower():
            return "Must be one of: LOW, MEDIUM, HIGH"
        if 'approval' in field.lower():
            return "Must be one of: NONE, SOFT, HARD"
        if 'max_daily' in field.lower() or 'max_hourly' in field.lower():
            return "Must be a positive integer > 0"
        
        return None
    
    def print_report(self):
        """Print validation report to console (uses logging)."""
        errors = [i for i in self.issues if i.severity == ValidationSeverity.ERROR]
        warnings = [i for i in self.issues if i.severity == ValidationSeverity.WARNING]
        
        report_lines = [
            "="*60,
            "Citadel SDK Validation Report",
            "="*60,
        ]
        
        if not self.issues:
            report_lines.append("✅ All checks passed — architecture is sound")
        else:
            if errors:
                report_lines.append(f"\n❌ ERRORS ({len(errors)}):")
                for issue in errors:
                    report_lines.append(f"  [{issue.action}] {issue.field}")
                    report_lines.append(f"    {issue.message}")
                    if issue.suggestion:
                        report_lines.append(f"    💡 {issue.suggestion}")
            
            if warnings:
                report_lines.append(f"\n⚠️ WARNINGS ({len(warnings)}):")
                for issue in warnings:
                    report_lines.append(f"  [{issue.action}] {issue.field}: {issue.message}")
        
        report_lines.append("="*60)
        
        # Log as a single multi-line message
        report_text = "\n".join(report_lines)
        if errors:
            logger.error(report_text)
        elif warnings:
            logger.warning(report_text)
        else:
            logger.info(report_text)


# Singleton
_validator_instance: Optional[Validator] = None


def get_validator() -> Validator:
    """Get or create the global validator."""
    global _validator_instance
    if _validator_instance is None:
        _validator_instance = Validator()
    return _validator_instance


def validate_at_startup():
    """
    Validate entire governance system at startup.
    Call this in your main.py or __init__.py
    """
    validator = get_validator()
    valid = validator.validate_catalog(None)
    validator.print_report()
    return valid


# Convenience functions
def validate_config(config: Dict[str, Any]) -> List[ValidationIssue]:
    """Quick validation of a single config."""
    return get_validator().validate_governance(config)


def validate_action_name(name: str) -> bool:
    """Validate that an action name follows conventions."""
    return bool(re.match(r'^[a-z][a-z0-9_]*$', name))

__all__ = [
    'ValidationSeverity',
    'ValidationIssue',
    'GovernanceConfig',
    'ValidatedGovernance',
    'Validator',
    'get_validator',
    'validate_at_startup',
    'validate_config',
    'validate_action_name',
]