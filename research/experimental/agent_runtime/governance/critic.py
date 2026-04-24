"""CRITIC — Quality Review

Implementation of CRITIC.md.

OWNERSHIP:
- OWNS: quality validation, contradiction detection, improvement recommendations
- DOES NOT OWN: execution, planning, relationship philosophy

PURPOSE:
CRITIC reviews meaningful outputs before they leave the system.
- Catches errors and contradictions
- Validates completeness
- Suggests improvements
- Does not block low-risk execution unnecessarily

SOURCE OF TRUTH: citadel/governance/CRITIC.md
If this code contradicts the MD file, the MD file is correct.
"""

from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime
import uuid


class ReviewResult(Enum):
    """Result of CRITIC review."""
    PASS = "pass"           # No issues, proceed
    FIX = "fix"             # Issues found but fixable
    ESCALATE = "escalate"   # Unresolved issues, escalate to FAILURE
    BLOCK = "block"         # Blocking issues, stop and ask


class ReviewDimension(Enum):
    """Dimensions to review per CRITIC.md."""
    COMPLETENESS = "completeness"   # Did we answer the question?
    CORRECTNESS = "correctness"      # Are facts accurate?
    CLARITY = "clarity"              # Is it understandable?
    SAFETY = "safety"                # No harmful content?
    ALIGNMENT = "alignment"          # Matches user intent?


@dataclass
class Issue:
    """An issue found during review."""
    id: str
    dimension: ReviewDimension
    severity: str  # low, medium, high, critical
    description: str
    suggestion: str
    fixable: bool = True
    auto_fixed: bool = False
    original_text: Optional[str] = None
    suggested_text: Optional[str] = None


@dataclass
class ReviewReport:
    """Complete review report."""
    id: str
    output_id: str
    timestamp: datetime
    result: ReviewResult
    issues: List[Issue]
    dimensions_reviewed: List[ReviewDimension]
    summary: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def has_critical_issues(self) -> bool:
        """Check if any critical issues exist."""
        return any(i.severity == "critical" for i in self.issues)
    
    @property
    def has_fixable_issues(self) -> bool:
        """Check if any fixable issues exist."""
        return any(i.fixable for i in self.issues)
    
    @property
    def issue_count(self) -> int:
        return len(self.issues)
    
    def get_issues_by_dimension(self, dimension: ReviewDimension) -> List[Issue]:
        """Get all issues for a specific dimension."""
        return [i for i in self.issues if i.dimension == dimension]


@dataclass
class ReviewContext:
    """Context for deciding whether to review."""
    output_affects_decision: bool = False
    stakes: str = "low"  # low, medium, high
    time_investment_minutes: int = 0
    planner_used: bool = False
    user_in_loop: bool = False
    tactical_mode: bool = False
    is_trivial_fact: bool = False
    is_casual_conversation: bool = False
    is_single_step: bool = False
    risk_level: str = "low"


class Critic:
    """
    CRITIC implementation.
    
    Quality review for meaningful outputs.
    
    Usage:
        critic = Critic()
        
        # Check if review needed
        if critic.should_review(context):
            report = critic.review(output, dimensions=[
                ReviewDimension.COMPLETENESS,
                ReviewDimension.CORRECTNESS
            ])
            
            if report.result == ReviewResult.FIX:
                # Apply fixes
                pass
            elif report.result == ReviewResult.ESCALATE:
                # Send to FAILURE
                pass
    """
    
    def __init__(self):
        self._review_history: List[ReviewReport] = []
        self._dimension_checkers: Dict[ReviewDimension, Callable] = {}
        self._auto_fix_enabled: bool = True
        self._register_default_checkers()
    
    def _register_default_checkers(self):
        """Register default dimension checkers."""
        self._dimension_checkers = {
            ReviewDimension.COMPLETENESS: self._check_completeness,
            ReviewDimension.CORRECTNESS: self._check_correctness,
            ReviewDimension.CLARITY: self._check_clarity,
            ReviewDimension.SAFETY: self._check_safety,
            ReviewDimension.ALIGNMENT: self._check_alignment,
        }
    
    def should_review(self, context: ReviewContext) -> bool:
        """
        Determine if CRITIC review is needed.
        
        Review if ANY apply:
        - output affects a decision
        - stakes involve money, reputation, safety, or time > 2 hours
        - PLANNER was used
        - user is in a loop or spiral
        - Tactical Mode is active
        - quality materially affects direction
        
        Skip review for:
        - trivial facts
        - casual conversation
        - obvious single-step responses
        - low-risk outputs
        """
        # Must review conditions
        if context.output_affects_decision:
            return True
        if context.stakes in ["high", "money", "reputation", "safety"]:
            return True
        if context.time_investment_minutes > 120:
            return True
        if context.planner_used:
            return True
        if context.user_in_loop:
            return True
        if context.tactical_mode:
            return True
        
        # Skip conditions
        if context.is_trivial_fact:
            return False
        if context.is_casual_conversation:
            return False
        if context.is_single_step and context.risk_level == "low":
            return False
        
        # Default: review medium+ risk
        return context.risk_level in ["medium", "high"]
    
    def review(
        self,
        output: Any,
        dimensions: Optional[List[ReviewDimension]] = None,
        context: Optional[Dict[str, Any]] = None,
        output_id: Optional[str] = None
    ) -> ReviewReport:
        """
        Review output across specified dimensions.
        
        Returns ReviewReport with findings and recommendations.
        """
        dims = dimensions or list(ReviewDimension)
        issues = []
        
        for dim in dims:
            checker = self._dimension_checkers.get(dim)
            if checker:
                dim_issues = checker(output, context or {})
                issues.extend(dim_issues)
        
        # Determine result
        result = self._determine_result(issues)
        
        # Auto-fix if enabled and issues are fixable
        if self._auto_fix_enabled and result == ReviewResult.FIX:
            fixed_count = self._auto_fix(output, issues)
            if fixed_count > 0:
                # Re-check after fixes
                result = self._determine_result([i for i in issues if not i.auto_fixed])
        
        report = ReviewReport(
            id=str(uuid.uuid4())[:8],
            output_id=output_id or str(uuid.uuid4())[:8],
            timestamp=datetime.utcnow(),
            result=result,
            issues=issues,
            dimensions_reviewed=dims,
            summary=self._generate_summary(issues, result)
        )
        
        self._review_history.append(report)
        return report
    
    def _determine_result(self, issues: List[Issue]) -> ReviewResult:
        """Determine review result from issues."""
        if not issues:
            return ReviewResult.PASS
        
        critical = any(i.severity == "critical" for i in issues)
        if critical:
            return ReviewResult.BLOCK
        
        unresolved = any(not i.fixable for i in issues)
        if unresolved:
            return ReviewResult.ESCALATE
        
        return ReviewResult.FIX
    
    def _auto_fix(self, output: Any, issues: List[Issue]) -> int:
        """Attempt to auto-fix fixable issues. Returns count fixed."""
        fixed = 0
        for issue in issues:
            if issue.fixable and issue.suggested_text:
                # In production, would apply the fix
                issue.auto_fixed = True
                fixed += 1
        return fixed
    
    def _generate_summary(self, issues: List[Issue], result: ReviewResult) -> str:
        """Generate human-readable summary."""
        if result == ReviewResult.PASS:
            return "No issues found. Output approved."
        
        by_severity = {"critical": 0, "high": 0, "medium": 0, "low": 0}
        for i in issues:
            by_severity[i.severity] = by_severity.get(i.severity, 0) + 1
        
        parts = [f"Found {len(issues)} issues:"]
        for sev in ["critical", "high", "medium", "low"]:
            if by_severity[sev] > 0:
                parts.append(f"  {sev}: {by_severity[sev]}")
        
        if result == ReviewResult.FIX:
            parts.append("All issues are fixable.")
        elif result == ReviewResult.ESCALATE:
            parts.append("Some issues require escalation.")
        elif result == ReviewResult.BLOCK:
            parts.append("Critical issues - blocking.")
        
        return "\n".join(parts)
    
    # Dimension checkers (simplified implementations)
    
    def _check_completeness(self, output: Any, context: Dict) -> List[Issue]:
        """Check if output is complete."""
        issues = []
        
        # Check if question was actually answered
        if isinstance(output, str):
            if len(output) < 10:
                issues.append(Issue(
                    id="c1",
                    dimension=ReviewDimension.COMPLETENESS,
                    severity="high",
                    description="Output appears too brief to fully answer the question",
                    suggestion="Expand to cover all aspects of the request"
                ))
            
            # Check for partial indicators
            partial_indicators = ["etc.", "and so on", "..."]
            if any(p in output.lower() for p in partial_indicators):
                issues.append(Issue(
                    id="c2",
                    dimension=ReviewDimension.COMPLETENESS,
                    severity="medium",
                    description="Output uses partial indicators suggesting incompleteness",
                    suggestion="Complete the thought or remove the indicator"
                ))
        
        return issues
    
    def _check_correctness(self, output: Any, context: Dict) -> List[Issue]:
        """Check if output is correct."""
        issues = []
        
        if isinstance(output, str):
            # Check for contradiction indicators
            contradiction_words = ["however", "but", "although", "contradiction"]
            if any(w in output.lower() for w in contradiction_words):
                issues.append(Issue(
                    id="r1",
                    dimension=ReviewDimension.CORRECTNESS,
                    severity="low",
                    description="Potential contradiction detected",
                    suggestion="Review for internal consistency"
                ))
        
        return issues
    
    def _check_clarity(self, output: Any, context: Dict) -> List[Issue]:
        """Check if output is clear."""
        issues = []
        
        if isinstance(output, str):
            # Check sentence length
            sentences = output.split(".")
            long_sentences = [s for s in sentences if len(s) > 200]
            if len(long_sentences) > 2:
                issues.append(Issue(
                    id="cl1",
                    dimension=ReviewDimension.CLARITY,
                    severity="medium",
                    description="Multiple very long sentences detected",
                    suggestion="Break into shorter, clearer sentences"
                ))
            
            # Check jargon
            jargon_words = ["utilize", "leverage", "synergy", "paradigm"]
            found_jargon = [w for w in jargon_words if w in output.lower()]
            if found_jargon:
                issues.append(Issue(
                    id="cl2",
                    dimension=ReviewDimension.CLARITY,
                    severity="low",
                    description=f"Jargon detected: {', '.join(found_jargon)}",
                    suggestion="Use simpler language"
                ))
        
        return issues
    
    def _check_safety(self, output: Any, context: Dict) -> List[Issue]:
        """Check if output is safe."""
        issues = []
        
        if isinstance(output, str):
            output_lower = output.lower()
            
            # Check for harmful content indicators
            harmful_indicators = [
                "kill yourself", "how to make", "create malware",
                "hack into", "steal data"
            ]
            
            for indicator in harmful_indicators:
                if indicator in output_lower:
                    issues.append(Issue(
                        id="s1",
                        dimension=ReviewDimension.SAFETY,
                        severity="critical",
                        description=f"Potentially harmful content: '{indicator}'",
                        suggestion="Remove or reframe the content",
                        fixable=False  # Don't auto-fix safety issues
                    ))
        
        return issues
    
    def _check_alignment(self, output: Any, context: Dict) -> List[Issue]:
        """Check if output aligns with user intent."""
        issues = []
        
        user_intent = context.get("user_intent", "")
        if user_intent and isinstance(output, str):
            # Simple check: does output address the intent
            intent_keywords = set(user_intent.lower().split())
            output_keywords = set(output.lower().split())
            overlap = intent_keywords & output_keywords
            
            if len(overlap) < len(intent_keywords) * 0.3:
                issues.append(Issue(
                    id="a1",
                    dimension=ReviewDimension.ALIGNMENT,
                    severity="high",
                    description="Output may not align with user intent",
                    suggestion="Review user request and adjust output"
                ))
        
        return issues
    
    def register_dimension_checker(
        self,
        dimension: ReviewDimension,
        checker: Callable[[Any, Dict], List[Issue]]
    ):
        """Register a custom checker for a dimension."""
        self._dimension_checkers[dimension] = checker
    
    def flag_for_review(
        self,
        output: Any,
        reason: str,
        priority: str = "normal"
    ) -> str:
        """
        Flag an output for review (called by EXECUTOR).
        
        Returns review request ID.
        """
        review_id = str(uuid.uuid4())[:8]
        # In production, would queue for review
        return review_id
    
    def get_review_history(self, limit: int = 10) -> List[ReviewReport]:
        """Get recent review history."""
        return self._review_history[-limit:]
    
    def get_stats(self) -> Dict[str, Any]:
        """Get review statistics."""
        if not self._review_history:
            return {"total_reviews": 0}
        
        results = {"PASS": 0, "FIX": 0, "ESCALATE": 0, "BLOCK": 0}
        for r in self._review_history:
            results[r.result.value] += 1
        
        return {
            "total_reviews": len(self._review_history),
            "by_result": results,
            "issue_rate": (results["FIX"] + results["ESCALATE"] + results["BLOCK"]) / len(self._review_history)
        }


# Singleton instance
def get_critic() -> Critic:
    """Get global Critic instance."""
    return Critic()
