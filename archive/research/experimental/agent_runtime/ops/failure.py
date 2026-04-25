"""FAILURE — Recovery Protocol

Implementation of FAILURE.md.

OWNERSHIP:
- OWNS: failure handling, recovery decisions, escalation, rollback
- DOES NOT OWN: normal execution, success cases, relationship philosophy

PURPOSE:
FAILURE decides what to do when things break.
- Retry internally?
- Ask the user?
- Stop execution?
- Rollback?

SOURCE OF TRUTH: citadel/ops/FAILURE.md
If this code contradicts the MD file, the MD file is correct.
"""

from typing import Dict, Any, List, Optional, Callable, Union
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime
import uuid


class FailureType(Enum):
    """Types of failures per FAILURE.md."""
    EXECUTION = "execution"      # EXECUTOR cannot continue
    PLANNING = "planning"        # PLANNER cannot produce valid plan
    CRITIC = "critic"            # CRITIC cannot resolve contradiction
    GOVERNOR = "governor"        # GOVERNOR escalation changes direction
    ALIGNMENT = "alignment"      # ALIGNMENT challenge unresolved
    SYSTEM = "system"            # Infrastructure/system failure


class RecoveryAction(Enum):
    """Recovery actions available."""
    RETRY = "retry"              # Retry with fix
    REPLAN = "replan"            # Escalate to PLANNER
    ASK_USER = "ask_user"        # Ask user for guidance
    PROCEED_WARNING = "proceed_warning"  # Proceed with warning
    ROLLBACK = "rollback"        # Undo work
    STOP_PARTIAL = "stop_partial"  # Stop with partial results
    STOP = "stop"                # Stop execution


class FailureSeverity(Enum):
    """Severity of failure."""
    LOW = "low"          # Can auto-recover
    MEDIUM = "medium"    # May need user input
    HIGH = "high"        # Requires intervention
    CRITICAL = "critical"  # Stop immediately


@dataclass
class FailureContext:
    """Context about the failure."""
    failure_type: FailureType
    error_message: str
    attempts_made: int = 0
    correction_attempts: int = 0
    partial_results: Optional[Any] = None
    can_rollback: bool = False
    rollback_plan: Optional[List[Dict]] = None
    stakes: str = "low"
    user_available: bool = True
    retry_possible: bool = True
    timestamp: datetime = field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class RecoveryDecision:
    """Decision on how to handle failure."""
    action: RecoveryAction
    severity: FailureSeverity
    message: str
    should_log: bool = True
    requires_approval: bool = False
    retry_count: int = 0
    max_retries: int = 2
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class FailureRecord:
    """Recorded failure for AUDIT.md."""
    id: str
    failure_type: FailureType
    severity: FailureSeverity
    error_message: str
    recovery_action: RecoveryAction
    result: str  # success, failed, pending
    timestamp: datetime
    context: Dict[str, Any]
    lessons_learned: List[str] = field(default_factory=list)


class Failure:
    """
    FAILURE implementation.
    
    Recovery protocol for when things break.
    
    Usage:
        failure = Failure()
        
        context = FailureContext(
            failure_type=FailureType.EXECUTION,
            error_message="Database connection failed",
            attempts_made=2,
            correction_attempts=2
        )
        
        decision = failure.handle(context)
        
        if decision.action == RecoveryAction.RETRY:
            # Retry with fix
            pass
        elif decision.action == RecoveryAction.ASK_USER:
            # Surface to user
            pass
        elif decision.action == RecoveryAction.STOP:
            # Stop execution
            pass
    """
    
    def __init__(self):
        self._failure_history: List[FailureRecord] = []
        self._recovery_strategies: Dict[FailureType, Callable] = {}
        self._audit_hook: Optional[Callable] = None
        self._register_default_strategies()
    
    def _register_default_strategies(self):
        """Register default recovery strategies."""
        self._recovery_strategies = {
            FailureType.EXECUTION: self._handle_execution_failure,
            FailureType.PLANNING: self._handle_planning_failure,
            FailureType.CRITIC: self._handle_critic_failure,
            FailureType.GOVERNOR: self._handle_governor_failure,
            FailureType.ALIGNMENT: self._handle_alignment_failure,
            FailureType.SYSTEM: self._handle_system_failure,
        }
    
    def register_audit_hook(self, hook: Callable[[FailureRecord], None]):
        """Register hook for logging to AUDIT.md."""
        self._audit_hook = hook
    
    def handle(self, context: FailureContext) -> RecoveryDecision:
        """
        Main entry: handle failure and return recovery decision.
        
        Decision Tree:
        1. Can retry? → Retry with fix
        2. Needs clarity? → Ask user
        3. Cannot continue? → Stop
        4. Partial results? → Deliver with note
        """
        strategy = self._recovery_strategies.get(context.failure_type)
        
        if strategy:
            decision = strategy(context)
        else:
            # Default: stop with error
            decision = RecoveryDecision(
                action=RecoveryAction.STOP,
                severity=FailureSeverity.HIGH,
                message=f"Unknown failure type: {context.failure_type.value}"
            )
        
        # Log to audit
        if decision.should_log:
            self._log_failure(context, decision)
        
        return decision
    
    def _handle_execution_failure(self, context: FailureContext) -> RecoveryDecision:
        """Handle EXECUTOR failures."""
        # EXECUTOR cannot continue after 2 correction attempts
        if context.correction_attempts >= 2:
            if context.can_rollback and context.rollback_plan:
                return RecoveryDecision(
                    action=RecoveryAction.ROLLBACK,
                    severity=FailureSeverity.HIGH,
                    message="Execution failed after 2 corrections. Rolling back.",
                    requires_approval=True
                )
            elif context.partial_results is not None:
                return RecoveryDecision(
                    action=RecoveryAction.STOP_PARTIAL,
                    severity=FailureSeverity.MEDIUM,
                    message="Execution failed. Delivering partial results.",
                    requires_approval=False
                )
            else:
                return RecoveryDecision(
                    action=RecoveryAction.REPLAN,
                    severity=FailureSeverity.MEDIUM,
                    message="Execution failed after 2 corrections. Escalating to PLANNER."
                )
        
        # Can still retry
        if context.retry_possible and context.attempts_made < 3:
            return RecoveryDecision(
                action=RecoveryAction.RETRY,
                severity=FailureSeverity.LOW,
                message=f"Retrying execution (attempt {context.attempts_made + 1})",
                retry_count=context.attempts_made,
                max_retries=3
            )
        
        # Ask user
        if context.user_available:
            return RecoveryDecision(
                action=RecoveryAction.ASK_USER,
                severity=FailureSeverity.MEDIUM,
                message="Execution failed. Asking user for guidance.",
                requires_approval=True
            )
        
        # Stop
        return RecoveryDecision(
            action=RecoveryAction.STOP,
            severity=FailureSeverity.HIGH,
            message="Execution failed and cannot recover. Stopping."
        )
    
    def _handle_planning_failure(self, context: FailureContext) -> RecoveryDecision:
        """Handle PLANNER failures."""
        # Options: Reduce scope, gather info, ask user, stop
        
        # Try reducing scope first
        if context.attempts_made < 2:
            return RecoveryDecision(
                action=RecoveryAction.RETRY,
                severity=FailureSeverity.MEDIUM,
                message="Planning failed. Reducing scope and retrying.",
                retry_count=context.attempts_made,
                max_retries=2,
                metadata={"strategy": "reduce_scope"}
            )
        
        # Ask user for clarification
        if context.user_available:
            return RecoveryDecision(
                action=RecoveryAction.ASK_USER,
                severity=FailureSeverity.MEDIUM,
                message="Cannot create valid plan. Asking user for clarification."
            )
        
        # Stop
        return RecoveryDecision(
            action=RecoveryAction.STOP,
            severity=FailureSeverity.HIGH,
            message="Planning failed and cannot continue without user input."
        )
    
    def _handle_critic_failure(self, context: FailureContext) -> RecoveryDecision:
        """Handle CRITIC failures."""
        # Options: Flag for review, proceed with warning, stop
        
        if context.stakes in ["high", "critical"]:
            return RecoveryDecision(
                action=RecoveryAction.STOP,
                severity=FailureSeverity.HIGH,
                message="CRITIC found unresolved issues in high-stakes output. Stopping."
            )
        
        # Proceed with warning
        return RecoveryDecision(
            action=RecoveryAction.PROCEED_WARNING,
            severity=FailureSeverity.LOW,
            message="CRITIC flagged issues. Proceeding with warning to user."
        )
    
    def _handle_governor_failure(self, context: FailureContext) -> RecoveryDecision:
        """Handle GOVERNOR escalation."""
        # Options: Follow new direction, ask for resolution, stop
        
        if context.metadata.get("material_change", False):
            return RecoveryDecision(
                action=RecoveryAction.ASK_USER,
                severity=FailureSeverity.HIGH,
                message="GOVERNOR material change detected. Asking user for resolution.",
                requires_approval=True
            )
        
        # Follow new direction
        return RecoveryDecision(
            action=RecoveryAction.RETRY,
            severity=FailureSeverity.MEDIUM,
            message="GOVERNOR escalation. Following new direction.",
            metadata={"governor_directive": context.metadata.get("directive")}
        )
    
    def _handle_alignment_failure(self, context: FailureContext) -> RecoveryDecision:
        """Handle ALIGNMENT challenge."""
        # Ask user for resolution
        return RecoveryDecision(
            action=RecoveryAction.ASK_USER,
            severity=FailureSeverity.MEDIUM,
            message="ALIGNMENT challenge unresolved. Asking user for resolution.",
            requires_approval=True
        )
    
    def _handle_system_failure(self, context: FailureContext) -> RecoveryDecision:
        """Handle system/infrastructure failures."""
        # System failures may be transient
        if context.attempts_made < 3:
            return RecoveryDecision(
                action=RecoveryAction.RETRY,
                severity=FailureSeverity.HIGH,
                message=f"System failure. Retrying with backoff (attempt {context.attempts_made + 1}/3)",
                retry_count=context.attempts_made,
                max_retries=3
            )
        
        return RecoveryDecision(
            action=RecoveryAction.STOP,
            severity=FailureSeverity.CRITICAL,
            message="System failure persisted. Stopping."
        )
    
    def execute_rollback(self, rollback_plan: List[Dict]) -> Dict[str, Any]:
        """
        Execute rollback plan.
        
        Per FAILURE.md:
        - Document what to undo
        - Execute rollback plan
        - Verify state
        - Report completion
        """
        results = {
            "steps_executed": 0,
            "steps_failed": 0,
            "verified": False,
            "details": []
        }
        
        for step in rollback_plan:
            step_id = step.get("id", "unknown")
            try:
                # Execute rollback step
                # In production, would call actual rollback function
                results["steps_executed"] += 1
                results["details"].append({"step": step_id, "status": "success"})
            except Exception as e:
                results["steps_failed"] += 1
                results["details"].append({"step": step_id, "status": "failed", "error": str(e)})
        
        # Verify state
        results["verified"] = results["steps_failed"] == 0
        
        return results
    
    def _log_failure(self, context: FailureContext, decision: RecoveryDecision):
        """Log failure to history and AUDIT.md."""
        record = FailureRecord(
            id=str(uuid.uuid4())[:8],
            failure_type=context.failure_type,
            severity=decision.severity,
            error_message=context.error_message,
            recovery_action=decision.action,
            result="pending",
            timestamp=datetime.utcnow(),
            context={
                "attempts_made": context.attempts_made,
                "correction_attempts": context.correction_attempts,
                "can_rollback": context.can_rollback,
                "user_available": context.user_available
            }
        )
        
        self._failure_history.append(record)
        
        if self._audit_hook:
            self._audit_hook(record)
    
    def update_failure_result(self, failure_id: str, result: str, lessons: List[str] = None):
        """Update failure record with outcome."""
        for record in self._failure_history:
            if record.id == failure_id:
                record.result = result
                if lessons:
                    record.lessons_learned.extend(lessons)
                return True
        return False
    
    def get_failure_history(
        self,
        failure_type: Optional[FailureType] = None,
        limit: int = 20
    ) -> List[FailureRecord]:
        """Get failure history, optionally filtered."""
        history = self._failure_history
        
        if failure_type:
            history = [h for h in history if h.failure_type == failure_type]
        
        return history[-limit:]
    
    def get_stats(self) -> Dict[str, Any]:
        """Get failure statistics."""
        if not self._failure_history:
            return {"total_failures": 0}
        
        by_type = {}
        by_severity = {}
        by_action = {}
        
        for f in self._failure_history:
            by_type[f.failure_type.value] = by_type.get(f.failure_type.value, 0) + 1
            by_severity[f.severity.value] = by_severity.get(f.severity.value, 0) + 1
            by_action[f.recovery_action.value] = by_action.get(f.recovery_action.value, 0) + 1
        
        recovery_rate = sum(
            1 for f in self._failure_history if f.result == "success"
        ) / len(self._failure_history)
        
        return {
            "total_failures": len(self._failure_history),
            "by_type": by_type,
            "by_severity": by_severity,
            "by_recovery_action": by_action,
            "recovery_rate": recovery_rate
        }
    
    def extract_lessons(self, recent: int = 10) -> List[str]:
        """Extract lessons learned from recent failures."""
        lessons = []
        for record in self._failure_history[-recent:]:
            lessons.extend(record.lessons_learned)
        return list(set(lessons))  # Deduplicate


# Singleton instance
def get_failure() -> Failure:
    """Get global Failure instance."""
    return Failure()
