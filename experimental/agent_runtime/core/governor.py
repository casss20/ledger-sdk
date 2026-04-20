"""GOVERNOR – Strategic Oversight

Implementation of GOVERNOR.md.

This module monitors long-term patterns and protects the user's direction.
It operates above planning and execution.

OWNERSHIP:
- OWNS: escalation thresholds, direction protection, drift detection, intervention levels
- DOES NOT OWN: relationship philosophy, execution permission, safety rules, quality control

AUTHORITY:
Enforces and operationalizes the Intervention Rule from CONSTITUTION.md.
CONSTITUTION.md defines *when* intervention is required.
GOVERNOR defines *how strongly* to intervene and how escalation evolves.

SOURCE OF TRUTH: ledger/core/GOVERNOR.md
If this code contradicts the MD file, the MD file is correct.
"""

from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import json


class EscalationLevel(Enum):
    """Intervention escalation levels."""
    PASSIVE = 0      # Normal assistance
    SUGGESTION = 1   # Light guidance: "You may want to…"
    CORRECTION = 2   # Clear direction + strict mode
    INTERVENTION = 3 # Override softness, execution lock


@dataclass
class Pattern:
    """Detected pattern requiring intervention."""
    pattern_type: str  # "repeat_mistake", "procrastination", "overplanning", etc.
    first_seen: datetime
    last_seen: datetime
    count: int = 1
    context: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Intervention:
    """Record of an intervention."""
    level: EscalationLevel
    timestamp: datetime
    pattern: str
    message: str
    context: Dict[str, Any] = field(default_factory=dict)
    acknowledged: bool = False
    overridden: bool = False


class ExecutionLocked(Exception):
    """Raised when GOVERNOR has locked execution (Level 3)."""
    pass


class Governor:
    """
    Strategic oversight layer.
    
    Tracks escalation, detects patterns, controls execution locks.
    Does NOT execute — only advises/locks.
    
    Usage:
        gov = Governor()
        
        # Check before executing
        level = gov.check_intervention(context={"action": "new_project", "current_projects": 5})
        
        if level == EscalationLevel.INTERVENTION:
            raise ExecutionLocked("Pattern detected: overcommitment")
        
        if level == EscalationLevel.CORRECTION:
            # Strict mode: require explicit confirmation
            await require_user_confirmation("This may be a distraction. Proceed?")
    """
    
    # Class constants
    MAX_LEVEL_3_REPEATS = 3  # Level 3 can repeat 3 times per pattern
    
    def __init__(self):
        self._escalation_level = EscalationLevel.PASSIVE
        self._locked = False
        self._lock_reason: Optional[str] = None
        self._patterns: Dict[str, Pattern] = {}
        self._interventions: List[Intervention] = []
        self._level_3_counts: Dict[str, int] = {}  # Track Level 3 per pattern
        self._paused_patterns: set = set()  # Patterns paused after 3x Level 3
        self._direction_check_fn: Optional[Callable] = None
        self._audit_log_fn: Optional[Callable] = None
    
    @property
    def escalation_level(self) -> EscalationLevel:
        """Current escalation level."""
        return self._escalation_level
    
    @property
    def locked(self) -> bool:
        """Is execution currently locked?"""
        return self._locked
    
    @property
    def lock_reason(self) -> Optional[str]:
        """Reason for current lock."""
        return self._lock_reason
    
    def register_audit_logger(self, fn: Callable[[str, Dict], None]):
        """Register function to log to AUDIT.md."""
        self._audit_log_fn = fn
    
    def register_direction_checker(self, fn: Callable[[Dict], bool]):
        """Register function to check direction against WORLD.md."""
        self._direction_check_fn = fn
    
    def check_intervention(self, context: Dict[str, Any]) -> EscalationLevel:
        """
        Check current intervention level for given context.
        
        This is the main entry point — EXECUTOR calls this before acting.
        """
        # Check if we're locked
        if self._locked:
            return EscalationLevel.INTERVENTION
        
        # Detect patterns
        detected_pattern = self._detect_pattern(context)
        
        if detected_pattern:
            return self._calculate_escalation(detected_pattern)
        
        # Check direction alignment
        if self._should_check_direction(context):
            if not self._check_direction(context):
                return EscalationLevel.CORRECTION
        
        # Default: passive
        return EscalationLevel.PASSIVE
    
    def _detect_pattern(self, context: Dict[str, Any]) -> Optional[str]:
        """Detect harmful patterns in context."""
        patterns_detected = []
        
        # Same mistake repetition
        if self._is_repeat_mistake(context):
            patterns_detected.append("repeat_mistake")
        
        # Procrastination loop
        if self._is_procrastination(context):
            patterns_detected.append("procrastination")
        
        # Overplanning without execution
        if self._is_overplanning(context):
            patterns_detected.append("overplanning")
        
        # Starting new work without finishing
        if self._is_new_without_finishing(context):
            patterns_detected.append("incomplete_pivot")
        
        # Ignoring previous advice
        if self._is_ignoring_advice(context):
            patterns_detected.append("ignored_advice")
        
        # Return most severe pattern
        if patterns_detected:
            return patterns_detected[0]  # Could prioritize by severity
        
        return None
    
    def _is_repeat_mistake(self, context: Dict) -> bool:
        """Check if user is repeating a known mistake."""
        action = context.get("action", "")
        history = context.get("action_history", [])
        
        # Count similar failed actions
        similar_failures = sum(1 for h in history if h.get("action") == action and h.get("failed"))
        return similar_failures >= 2
    
    def _is_procrastination(self, context: Dict) -> bool:
        """Check for procrastination loops."""
        # Pattern: planning without execution, repeated delays
        recent_actions = context.get("recent_actions", [])
        planning_count = sum(1 for a in recent_actions if "plan" in a.get("action", "").lower())
        execution_count = sum(1 for a in recent_actions if "execute" in a.get("action", "").lower())
        
        return planning_count > 3 and execution_count == 0
    
    def _is_overplanning(self, context: Dict) -> bool:
        """Check for analysis paralysis."""
        plan_versions = context.get("plan_versions", 0)
        return plan_versions > 3
    
    def _is_new_without_finishing(self, context: Dict) -> bool:
        """Check for starting new work without completing existing."""
        active_projects = context.get("active_projects", 0)
        incomplete_projects = context.get("incomplete_projects", [])
        
        return active_projects > 3 or len(incomplete_projects) > 2
    
    def _is_ignoring_advice(self, context: Dict) -> bool:
        """Check if previous advice was ignored."""
        advice_given = context.get("advice_given", [])
        advice_followed = context.get("advice_followed", [])
        
        return len(advice_given) > len(advice_followed) + 2
    
    def _calculate_escalation(self, pattern: str) -> EscalationLevel:
        """Calculate escalation level for a detected pattern."""
        # Check if pattern is paused (ignored 3x already)
        if pattern in self._paused_patterns:
            return EscalationLevel.PASSIVE
        
        # Get or create pattern record
        if pattern not in self._patterns:
            self._patterns[pattern] = Pattern(
                pattern_type=pattern,
                first_seen=datetime.utcnow(),
                last_seen=datetime.utcnow()
            )
        else:
            self._patterns[pattern].count += 1
            self._patterns[pattern].last_seen = datetime.utcnow()
        
        count = self._patterns[pattern].count
        
        # Calculate level based on frequency
        if count == 1:
            level = EscalationLevel.SUGGESTION
        elif count == 2:
            level = EscalationLevel.CORRECTION
        else:
            level = EscalationLevel.INTERVENTION
            
            # Track Level 3 count for this pattern
            self._level_3_counts[pattern] = self._level_3_counts.get(pattern, 0) + 1
            
            # Pause pattern after 3 Level 3s
            if self._level_3_counts[pattern] >= self.MAX_LEVEL_3_REPEATS:
                self._paused_patterns.add(pattern)
        
        self._escalation_level = level
        return level
    
    def _should_check_direction(self, context: Dict) -> bool:
        """Check if this action requires direction validation."""
        action = context.get("action", "")
        scope = context.get("scope", "")
        
        # Major decisions need direction check
        major_indicators = ["new_project", "major_decision", "scope_expansion", "pivot"]
        return any(ind in action.lower() or ind in scope.lower() for ind in major_indicators)
    
    def _check_direction(self, context: Dict) -> bool:
        """Check if action aligns with direction (WORLD.md)."""
        if self._direction_check_fn:
            return self._direction_check_fn(context)
        
        # Default: assume aligned if no checker registered
        return True
    
    def lock_execution(self, reason: str):
        """
        Lock execution (Level 3 intervention).
        
        EXECUTOR must respect this and refuse to generate work.
        """
        self._locked = True
        self._lock_reason = reason
        self._log_intervention(EscalationLevel.INTERVENTION, reason)
    
    def unlock_execution(self, reason: Optional[str] = None):
        """Unlock execution after pattern breaks."""
        self._locked = False
        self._lock_reason = None
        self._escalation_level = EscalationLevel.PASSIVE
    
    def require_confirmation(self, message: str) -> Dict[str, Any]:
        """
        Generate strict mode confirmation request (Level 2).
        
        EXECUTOR must present this and await explicit user confirmation.
        """
        self._log_intervention(EscalationLevel.CORRECTION, message)
        
        return {
            "level": "correction",
            "mode": "strict",
            "message": message,
            "requires_explicit_confirmation": True,
            "options": ["proceed", "cancel", "explain"]
        }
    
    def record_override(self, reason: str, user_command: str):
        """
        Record willful override of GOVERNOR warning.
        
        Per Willful Override Protocol:
        1. Yield immediately (already done by caller)
        2. Log to AUDIT
        3. Reset to Level 0
        """
        intervention = Intervention(
            level=EscalationLevel.INTERVENTION,
            timestamp=datetime.utcnow(),
            pattern="willful_override",
            message=f"User overrode GOVERNOR: {reason}",
            context={"user_command": user_command, "override_reason": reason},
            acknowledged=True,
            overridden=True
        )
        self._interventions.append(intervention)
        
        # Log to AUDIT
        if self._audit_log_fn:
            self._audit_log_fn("GOVERNOR_OVERRIDE", intervention.__dict__)
        
        # Reset
        self.unlock_execution()
        self._escalation_level = EscalationLevel.PASSIVE
    
    def de_escalate(self):
        """Reduce escalation level when pattern breaks."""
        current = self._escalation_level.value
        if current > 0:
            self._escalation_level = EscalationLevel(current - 1)
    
    def get_pattern_summary(self) -> Dict[str, Any]:
        """Summary of detected patterns for dashboard."""
        return {
            "active_patterns": len(self._patterns),
            "escalation_level": self._escalation_level.name,
            "locked": self._locked,
            "patterns": {
                name: {
                    "count": p.count,
                    "first_seen": p.first_seen.isoformat(),
                    "last_seen": p.last_seen.isoformat()
                }
                for name, p in self._patterns.items()
            },
            "paused_patterns": list(self._paused_patterns)
        }
    
    def _log_intervention(self, level: EscalationLevel, message: str):
        """Internal logging of intervention."""
        intervention = Intervention(
            level=level,
            timestamp=datetime.utcnow(),
            pattern="detected",
            message=message
        )
        self._interventions.append(intervention)


# Singleton instance
def get_governor() -> Governor:
    """Get the global Governor instance."""
    # In production, this might be backed by Redis for persistence
    return Governor()
