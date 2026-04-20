"""ADAPTATION — Behavioral Adjustment

Implementation of ADAPTATION.md.

PURPOSE:
Refine behavior based on observed patterns.

WHEN TO ADAPT:
After repeated evidence:
- Preference repeats
- Strategy repeatedly works/fails
- Response style needs tuning
- Outcomes justify change

Do not adapt from one-off events.

WHAT CAN ADAPT:
- Response length
- Depth of explanation
- Tone and style
- Planning approach
- Execution mode preferences

WHAT CANNOT ADAPT:
- Core rules (CONSTITUTION)
- Safety boundaries
- Protected file contents
- Governance thresholds

METHOD:
1. Observe pattern
2. Verify consistency
3. Suggest adjustment
4. Apply if confirmed
5. Log change

SOURCE OF TRUTH: ledger/ops/ADAPTATION.md
If this code contradicts the MD file, the MD file is correct.
"""

from typing import Dict, Any, List, Optional, Callable, Set
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime
from collections import defaultdict


class AdaptationType(Enum):
    """Types of behavioral adaptations."""
    RESPONSE_LENGTH = "response_length"
    EXPLANATION_DEPTH = "explanation_depth"
    TONE_STYLE = "tone_style"
    PLANNING_APPROACH = "planning_approach"
    EXECUTION_MODE = "execution_mode"


class AdaptationStatus(Enum):
    """Status of adaptation."""
    OBSERVED = "observed"      # Pattern detected
    VERIFIED = "verified"        # Consistency confirmed
    SUGGESTED = "suggested"      # Adjustment proposed
    APPLIED = "applied"          # Change active
    REJECTED = "rejected"        # Not applied


class ProtectedBoundary(Enum):
    """What cannot be adapted per ADAPTATION.md."""
    CONSTITUTION = "constitution"
    SAFETY = "safety"
    PROTECTED_FILES = "protected_files"
    GOVERNANCE = "governance"


@dataclass
class PatternObservation:
    """An observed pattern."""
    timestamp: datetime
    context: str
    observation: str
    outcome: str  # success, failure, neutral


@dataclass
class AdaptationCandidate:
    """A candidate adaptation."""
    id: str
    adaptation_type: AdaptationType
    pattern: str
    observations: List[PatternObservation]
    suggested_change: Dict[str, Any]
    confidence: float  # 0.0 to 1.0
    status: AdaptationStatus
    created_at: datetime
    applied_at: Optional[datetime] = None


@dataclass
class AdaptationConfig:
    """Current adaptation configuration."""
    response_length: str = "adaptive"  # short, medium, long, adaptive
    explanation_depth: str = "contextual"  # minimal, standard, deep, contextual
    tone_style: str = "professional"  # casual, professional, technical, friendly
    planning_approach: str = "auto"  # minimal, standard, thorough, auto
    execution_mode: str = "flow"  # flow, controlled, strict


class Adaptation:
    """
    ADAPTATION implementation.

    Behavioral adjustment based on observed patterns.

    Usage:
        adaptation = Adaptation()

        # Record observation
        adaptation.observe(
            pattern="user_prefers_short_responses",
            context="summarize_request",
            outcome="success"
        )

        # Check for adaptations
        candidates = adaptation.identify_candidates()
        for c in candidates:
            if adaptation.verify(c):
                adaptation.apply(c)
    """

    # Minimum observations before suggesting adaptation
    MIN_OBSERVATIONS = 3

    # Confidence threshold for auto-application
    AUTO_APPLY_THRESHOLD = 0.8

    # Protected boundaries that cannot be adapted
    PROTECTED = {
        ProtectedBoundary.CONSTITUTION,
        ProtectedBoundary.SAFETY,
        ProtectedBoundary.PROTECTED_FILES,
        ProtectedBoundary.GOVERNANCE,
    }

    def __init__(self):
        self._observations: Dict[str, List[PatternObservation]] = defaultdict(list)
        self._candidates: Dict[str, AdaptationCandidate] = {}
        self._config = AdaptationConfig()
        self._adaptation_history: List[AdaptationCandidate] = []
        self._audit_hook: Optional[Callable[[Dict], None]] = None

    def register_audit_hook(self, hook: Callable[[Dict], None]):
        """Register hook for logging to AUDIT.md."""
        self._audit_hook = hook

    def observe(
        self,
        pattern: str,
        context: str,
        outcome: str
    ) -> None:
        """
        Record a pattern observation.

        After repeated evidence, adaptation may be suggested.
        """
        observation = PatternObservation(
            timestamp=datetime.utcnow(),
            context=context,
            observation=pattern,
            outcome=outcome
        )
        self._observations[pattern].append(observation)

        # Check if we have enough observations for this pattern
        if len(self._observations[pattern]) >= self.MIN_OBSERVATIONS:
            self._evaluate_for_adaptation(pattern)

    def _evaluate_for_adaptation(self, pattern: str) -> None:
        """Evaluate if a pattern warrants adaptation."""
        observations = self._observations[pattern]

        # Check consistency
        outcomes = [o.outcome for o in observations]
        success_rate = outcomes.count("success") / len(outcomes)
        failure_rate = outcomes.count("failure") / len(outcomes)

        # Determine adaptation type from pattern
        adaptation_type = self._classify_pattern(pattern)

        # Calculate confidence
        if success_rate > 0.7 or failure_rate > 0.7:
            confidence = min(0.5 + (max(success_rate, failure_rate) - 0.7), 0.95)
        else:
            confidence = 0.5

        # Generate suggested change
        suggested_change = self._generate_suggestion(pattern, observations, adaptation_type)

        candidate = AdaptationCandidate(
            id=f"adapt_{pattern}_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}",
            adaptation_type=adaptation_type,
            pattern=pattern,
            observations=observations[-5:],  # Last 5 observations
            suggested_change=suggested_change,
            confidence=confidence,
            status=AdaptationStatus.OBSERVED,
            created_at=datetime.utcnow()
        )

        self._candidates[candidate.id] = candidate

    def _classify_pattern(self, pattern: str) -> AdaptationType:
        """Classify pattern into adaptation type."""
        pattern_lower = pattern.lower()

        if any(w in pattern_lower for w in ["length", "short", "long", "brief", "concise"]):
            return AdaptationType.RESPONSE_LENGTH

        if any(w in pattern_lower for w in ["explain", "detail", "depth", "technical"]):
            return AdaptationType.EXPLANATION_DEPTH

        if any(w in pattern_lower for w in ["tone", "style", "voice", "formal", "casual"]):
            return AdaptationType.TONE_STYLE

        if any(w in pattern_lower for w in ["plan", "structure", "approach", "method"]):
            return AdaptationType.PLANNING_APPROACH

        if any(w in pattern_lower for w in ["execute", "mode", "flow", "strict"]):
            return AdaptationType.EXECUTION_MODE

        return AdaptationType.EXECUTION_MODE  # Default

    def _generate_suggestion(
        self,
        pattern: str,
        observations: List[PatternObservation],
        adaptation_type: AdaptationType
    ) -> Dict[str, Any]:
        """Generate suggested change based on pattern."""
        outcomes = [o.outcome for o in observations]
        success_rate = outcomes.count("success") / len(outcomes)

        if adaptation_type == AdaptationType.RESPONSE_LENGTH:
            if success_rate > 0.7 and "short" in pattern.lower():
                return {"response_length": "short"}
            elif success_rate > 0.7 and "long" in pattern.lower():
                return {"response_length": "long"}

        elif adaptation_type == AdaptationType.EXPLANATION_DEPTH:
            if success_rate > 0.7 and "detail" in pattern.lower():
                return {"explanation_depth": "deep"}
            elif success_rate > 0.7 and "brief" in pattern.lower():
                return {"explanation_depth": "minimal"}

        elif adaptation_type == AdaptationType.TONE_STYLE:
            if "casual" in pattern.lower():
                return {"tone_style": "casual"}
            elif "formal" in pattern.lower():
                return {"tone_style": "professional"}
            elif "technical" in pattern.lower():
                return {"tone_style": "technical"}

        return {"unknown": pattern}

    def verify(self, candidate_id: str) -> bool:
        """
        Verify consistency of observations.

        Returns True if pattern is consistent enough to adapt.
        """
        candidate = self._candidates.get(candidate_id)
        if not candidate:
            return False

        # Check minimum observations
        if len(candidate.observations) < self.MIN_OBSERVATIONS:
            return False

        # Check confidence threshold
        if candidate.confidence < 0.6:
            return False

        # Check for contradictory observations
        outcomes = [o.outcome for o in candidate.observations]
        if outcomes.count("success") > 0 and outcomes.count("failure") > 0:
            # Mixed outcomes - need more data
            if outcomes.count("success") / len(outcomes) < 0.6:
                return False

        candidate.status = AdaptationStatus.VERIFIED
        return True

    def apply(self, candidate_id: str) -> bool:
        """
        Apply adaptation.

        Cannot adapt protected boundaries.
        """
        candidate = self._candidates.get(candidate_id)
        if not candidate:
            return False

        # Verify not touching protected boundaries
        if self._is_protected(candidate):
            candidate.status = AdaptationStatus.REJECTED
            return False

        # Apply the change
        self._apply_config_change(candidate.suggested_change)

        candidate.status = AdaptationStatus.APPLIED
        candidate.applied_at = datetime.utcnow()
        self._adaptation_history.append(candidate)

        # Log to audit
        if self._audit_hook:
            self._audit_hook({
                "event": "adaptation_applied",
                "candidate_id": candidate_id,
                "adaptation_type": candidate.adaptation_type.value,
                "pattern": candidate.pattern,
                "change": candidate.suggested_change,
                "confidence": candidate.confidence,
                "timestamp": candidate.applied_at.isoformat()
            })

        return True

    def _is_protected(self, candidate: AdaptationCandidate) -> bool:
        """Check if candidate touches protected boundaries."""
        # Check if change affects constitution
        if ProtectedBoundary.CONSTITUTION in self.PROTECTED:
            if "constitution" in candidate.pattern.lower():
                return True

        # Check if change affects safety
        if ProtectedBoundary.SAFETY in self.PROTECTED:
            if any(w in candidate.pattern.lower() for w in ["safety", "danger", "risk", "harm"]):
                return True

        # Check if change affects governance
        if ProtectedBoundary.GOVERNANCE in self.PROTECTED:
            if any(w in candidate.pattern.lower() for w in ["governor", "rule", "threshold", "boundary"]):
                return True

        return False

    def _apply_config_change(self, change: Dict[str, Any]) -> None:
        """Apply configuration change."""
        for key, value in change.items():
            if hasattr(self._config, key):
                setattr(self._config, key, value)

    def identify_candidates(self) -> List[AdaptationCandidate]:
        """Get all adaptation candidates."""
        return list(self._candidates.values())

    def get_config(self) -> AdaptationConfig:
        """Get current adaptation configuration."""
        return self._config

    def get_adaptation_history(self, limit: int = 10) -> List[AdaptationCandidate]:
        """Get history of applied adaptations."""
        return self._adaptation_history[-limit:]

    def get_observation_stats(self) -> Dict[str, Any]:
        """Get statistics on observations."""
        stats = {}
        for pattern, observations in self._observations.items():
            outcomes = [o.outcome for o in observations]
            stats[pattern] = {
                "count": len(observations),
                "success_rate": outcomes.count("success") / len(outcomes) if outcomes else 0,
                "failure_rate": outcomes.count("failure") / len(outcomes) if outcomes else 0
            }
        return stats

    def should_auto_apply(self, candidate_id: str) -> bool:
        """Check if candidate meets auto-apply threshold."""
        candidate = self._candidates.get(candidate_id)
        if not candidate:
            return False

        return candidate.confidence >= self.AUTO_APPLY_THRESHOLD and not self._is_protected(candidate)


# Singleton instance
def get_adaptation() -> Adaptation:
    """Get global Adaptation instance."""
    return Adaptation()
