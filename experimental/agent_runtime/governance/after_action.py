"""AFTER_ACTION — Learning Loop

Implementation of AFTER_ACTION.md.

PURPOSE:
Structured reflection after task completion.

WHEN TO RUN:
After:
- Complex tasks
- Failures
- New patterns encountered
- Significant decisions

REFLECTION QUESTIONS:
1. Outcome: Did we achieve the goal?
2. Process: What worked? What didn't?
3. Errors: What went wrong? How was it handled?
4. Patterns: Any new patterns to remember?
5. Improvements: What would we do differently?

OUTPUT:
Brief summary:
- Success/failure
- Key learnings
- Pattern updates (if any)
- Suggested process improvements

INTEGRATION:
Relevant learnings → MEMORY.md
Significant events → AUDIT.md
Process changes → ADAPTATION.md

SOURCE OF TRUTH: ledger/governance/AFTER_ACTION.md
If this code contradicts the MD file, the MD file is correct.
"""

from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime
import uuid


class TaskOutcome(Enum):
    """Outcome of task execution."""
    SUCCESS = "success"
    PARTIAL_SUCCESS = "partial_success"
    FAILURE = "failure"
    ABORTED = "aborted"
    UNKNOWN = "unknown"


class LearningPriority(Enum):
    """Priority of learning for storage."""
    LOW = "low"          # Transient, may not need persistence
    MEDIUM = "medium"    # Worth remembering
    HIGH = "high"        # Critical learning


@dataclass
class Reflection:
    """A single reflection dimension."""
    question: str
    answer: str
    insights: List[str] = field(default_factory=list)


@dataclass
class PatternObservation:
    """Observed pattern to remember."""
    pattern: str
    context: str
    outcome: str
    confidence: str  # low, medium, high


@dataclass
class ProcessImprovement:
    """Suggested improvement to process."""
    description: str
    rationale: str
    expected_benefit: str
    implementation_effort: str  # low, medium, high


@dataclass
class AfterActionReport:
    """
    Complete after-action report.

    Brief summary:
    - Success/failure
    - Key learnings
    - Pattern updates (if any)
    - Suggested process improvements
    """
    id: str
    task_id: str
    timestamp: datetime
    outcome: TaskOutcome
    reflections: List[Reflection]
    key_learnings: List[str]
    patterns_observed: List[PatternObservation]
    process_improvements: List[ProcessImprovement]
    memory_update_suggested: bool
    audit_entry_required: bool
    adaptation_suggested: bool
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_summary(self) -> str:
        """Generate brief summary."""
        lines = [
            f"After-Action Report: {self.task_id}",
            f"Outcome: {self.outcome.value}",
            f"Key Learnings ({len(self.key_learnings)}):"
        ]
        for i, learning in enumerate(self.key_learnings[:3], 1):
            lines.append(f"  {i}. {learning}")

        if self.patterns_observed:
            lines.append(f"Patterns Observed: {len(self.patterns_observed)}")

        if self.process_improvements:
            lines.append(f"Process Improvements: {len(self.process_improvements)}")

        return "\n".join(lines)


@dataclass
class AfterActionContext:
    """Context for after-action review."""
    task_description: str
    task_complexity: str  # simple, moderate, complex
    was_failure: bool = False
    new_pattern_encountered: bool = False
    significant_decision_made: bool = False
    execution_time_minutes: int = 0
    errors_encountered: int = 0
    user_feedback: Optional[str] = None


class AfterAction:
    """
    AFTER_ACTION implementation.

    Structured reflection after task completion.

    Usage:
        after_action = AfterAction()

        context = AfterActionContext(
            task_description="Deploy production",
            task_complexity="complex",
            was_failure=False,
            new_pattern_encountered=True
        )

        if after_action.should_run(context):
            report = after_action.reflect(context, execution_details={...})
            print(report.to_summary())
    """

    def __init__(self):
        self._report_history: List[AfterActionReport] = []
        self._memory_hook: Optional[Callable[[str, LearningPriority], None]] = None
        self._audit_hook: Optional[Callable[[Dict], None]] = None
        self._adaptation_hook: Optional[Callable[[ProcessImprovement], None]] = None

    def register_memory_hook(self, hook: Callable[[str, LearningPriority], None]):
        """Register hook for updating MEMORY.md."""
        self._memory_hook = hook

    def register_audit_hook(self, hook: Callable[[Dict], None]):
        """Register hook for AUDIT.md entries."""
        self._audit_hook = hook

    def register_adaptation_hook(self, hook: Callable[[ProcessImprovement], None]):
        """Register hook for ADAPTATION.md updates."""
        self._adaptation_hook = hook

    def should_run(self, context: AfterActionContext) -> bool:
        """
        Determine if after-action review should run.

        Run after:
        - Complex tasks
        - Failures
        - New patterns encountered
        - Significant decisions
        """
        if context.was_failure:
            return True

        if context.task_complexity in ["moderate", "complex"]:
            return True

        if context.new_pattern_encountered:
            return True

        if context.significant_decision_made:
            return True

        if context.execution_time_minutes > 30:
            return True

        if context.errors_encountered > 0:
            return True

        return False

    def reflect(
        self,
        context: AfterActionContext,
        execution_details: Dict[str, Any],
        goal_achieved: Optional[bool] = None
    ) -> AfterActionReport:
        """
        Perform structured reflection.

        Answers the 5 reflection questions:
        1. Outcome: Did we achieve the goal?
        2. Process: What worked? What didn't?
        3. Errors: What went wrong? How was it handled?
        4. Patterns: Any new patterns to remember?
        5. Improvements: What would we do differently?
        """
        reflections = []

        # 1. Outcome
        outcome = self._determine_outcome(context, goal_achieved)
        reflections.append(Reflection(
            question="Did we achieve the goal?",
            answer="Yes" if outcome in [TaskOutcome.SUCCESS, TaskOutcome.PARTIAL_SUCCESS] else "No",
            insights=self._analyze_outcome(context, execution_details)
        ))

        # 2. Process
        reflections.append(Reflection(
            question="What worked? What didn't?",
            answer=self._summarize_process(context, execution_details),
            insights=self._extract_process_insights(context, execution_details)
        ))

        # 3. Errors
        reflections.append(Reflection(
            question="What went wrong? How was it handled?",
            answer=self._summarize_errors(context, execution_details),
            insights=self._extract_error_lessons(context, execution_details)
        ))

        # 4. Patterns
        patterns = self._identify_patterns(context, execution_details)
        reflections.append(Reflection(
            question="Any new patterns to remember?",
            answer=f"Identified {len(patterns)} patterns" if patterns else "No new patterns",
            insights=[p.pattern for p in patterns]
        ))

        # 5. Improvements
        improvements = self._suggest_improvements(context, execution_details)
        reflections.append(Reflection(
            question="What would we do differently?",
            answer=f"{len(improvements)} suggestions" if improvements else "No changes needed",
            insights=[imp.description for imp in improvements]
        ))

        # Extract key learnings
        key_learnings = self._extract_learnings(reflections)

        # Determine integration needs
        memory_update = len(key_learnings) > 0 or len(patterns) > 0
        audit_entry = context.significant_decision_made or context.was_failure
        adaptation_needed = len(improvements) > 0

        report = AfterActionReport(
            id=str(uuid.uuid4())[:8],
            task_id=execution_details.get("task_id", "unknown"),
            timestamp=datetime.utcnow(),
            outcome=outcome,
            reflections=reflections,
            key_learnings=key_learnings,
            patterns_observed=patterns,
            process_improvements=improvements,
            memory_update_suggested=memory_update,
            audit_entry_required=audit_entry,
            adaptation_suggested=adaptation_needed
        )

        self._report_history.append(report)

        # Trigger integrations
        self._integrate(report)

        return report

    def _determine_outcome(
        self,
        context: AfterActionContext,
        goal_achieved: Optional[bool]
    ) -> TaskOutcome:
        """Determine task outcome."""
        if context.was_failure:
            return TaskOutcome.FAILURE

        if goal_achieved is True:
            return TaskOutcome.SUCCESS

        if goal_achieved is False:
            return TaskOutcome.FAILURE

        if context.errors_encountered > 0:
            return TaskOutcome.PARTIAL_SUCCESS

        return TaskOutcome.UNKNOWN

    def _analyze_outcome(
        self,
        context: AfterActionContext,
        details: Dict[str, Any]
    ) -> List[str]:
        """Analyze outcome for insights."""
        insights = []

        if context.was_failure:
            insights.append("Task failed - analyze root cause")
        elif context.errors_encountered > 0:
            insights.append(f"Completed despite {context.errors_encountered} errors")
        else:
            insights.append("Clean execution")

        return insights

    def _summarize_process(self, context: AfterActionContext, details: Dict) -> str:
        """Summarize what worked and didn't."""
        parts = []

        if context.execution_time_minutes < 15:
            parts.append("Fast execution")
        elif context.execution_time_minutes > 60:
            parts.append("Long execution - consider optimization")

        if context.errors_encountered == 0:
            parts.append("No errors")
        else:
            parts.append(f"{context.errors_encountered} errors handled")

        return "; ".join(parts) if parts else "Standard process"

    def _extract_process_insights(
        self,
        context: AfterActionContext,
        details: Dict
    ) -> List[str]:
        """Extract insights about process."""
        insights = []

        if context.execution_time_minutes > 60:
            insights.append("Consider breaking into smaller tasks")

        if context.errors_encountered > 2:
            insights.append("High error rate - review error handling")

        return insights

    def _summarize_errors(self, context: AfterActionContext, details: Dict) -> str:
        """Summarize errors encountered."""
        if context.errors_encountered == 0:
            return "No errors"

        error_types = details.get("error_types", [])
        if error_types:
            return f"{context.errors_encountered} errors: {', '.join(error_types)}"

        return f"{context.errors_encountered} errors encountered"

    def _extract_error_lessons(self, context: AfterActionContext, details: Dict) -> List[str]:
        """Extract lessons from errors."""
        lessons = []

        if context.errors_encountered > 0:
            lessons.append("Document error handling for future reference")

        if context.was_failure:
            lessons.append("Analyze failure mode to prevent recurrence")

        return lessons

    def _identify_patterns(
        self,
        context: AfterActionContext,
        details: Dict
    ) -> List[PatternObservation]:
        """Identify new patterns from execution."""
        patterns = []

        if context.new_pattern_encountered:
            patterns.append(PatternObservation(
                pattern="New workflow pattern identified",
                context=context.task_description,
                outcome="success" if not context.was_failure else "failure",
                confidence="medium"
            ))

        # Check for recurring error patterns
        if context.errors_encountered > 1:
            patterns.append(PatternObservation(
                pattern="Recurring error in similar tasks",
                context=context.task_description,
                outcome="requires_attention",
                confidence="high"
            ))

        return patterns

    def _suggest_improvements(
        self,
        context: AfterActionContext,
        details: Dict
    ) -> List[ProcessImprovement]:
        """Suggest process improvements."""
        improvements = []

        if context.execution_time_minutes > 60:
            improvements.append(ProcessImprovement(
                description="Break long tasks into subtasks",
                rationale="Execution exceeded 1 hour",
                expected_benefit="Better progress tracking and recovery",
                implementation_effort="low"
            ))

        if context.errors_encountered > 2:
            improvements.append(ProcessImprovement(
                description="Add pre-validation step",
                rationale="Multiple errors suggest validation gaps",
                expected_benefit="Catch errors earlier",
                implementation_effort="medium"
            ))

        return improvements

    def _extract_learnings(self, reflections: List[Reflection]) -> List[str]:
        """Extract key learnings from reflections."""
        learnings = []

        for reflection in reflections:
            learnings.extend(reflection.insights)

        # Deduplicate while preserving order
        seen = set()
        unique = []
        for l in learnings:
            if l not in seen:
                seen.add(l)
                unique.append(l)

        return unique

    def _integrate(self, report: AfterActionReport):
        """
        Integrate findings into other systems.

        Relevant learnings → MEMORY.md
        Significant events → AUDIT.md
        Process changes → ADAPTATION.md
        """
        # MEMORY.md integration
        if report.memory_update_suggested and self._memory_hook:
            for learning in report.key_learnings:
                priority = LearningPriority.HIGH if report.was_failure else LearningPriority.MEDIUM
                self._memory_hook(learning, priority)

            for pattern in report.patterns_observed:
                if pattern.confidence in ["medium", "high"]:
                    self._memory_hook(
                        f"Pattern: {pattern.pattern} ({pattern.context})",
                        LearningPriority.MEDIUM
                    )

        # AUDIT.md integration
        if report.audit_entry_required and self._audit_hook:
            self._audit_hook({
                "event": "after_action",
                "task_id": report.task_id,
                "outcome": report.outcome.value,
                "learnings_count": len(report.key_learnings),
                "timestamp": report.timestamp.isoformat()
            })

        # ADAPTATION.md integration
        if report.adaptation_suggested and self._adaptation_hook:
            for improvement in report.process_improvements:
                self._adaptation_hook(improvement)

    def get_learning_history(self, limit: int = 10) -> List[AfterActionReport]:
        """Get recent after-action reports."""
        return self._report_history[-limit:]

    def extract_all_learnings(self) -> List[str]:
        """Extract all learnings from history."""
        learnings = []
        for report in self._report_history:
            learnings.extend(report.key_learnings)
        return list(set(learnings))


# Singleton instance
def get_after_action() -> AfterAction:
    """Get global AfterAction instance."""
    return AfterAction()
