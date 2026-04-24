"""PRUNE — Context Cleanup

Implementation of PRUNE.md.

PURPOSE:
Remove noise. Preserve meaning.

WHEN TO PRUNE:
- Memory files exceed threshold
- Session loading feels sluggish
- Context cluttered with outdated facts
- Monthly HEARTBEAT trigger

WHAT TO DELETE:
- Transcript noise
- Trivial exchanges
- Outdated transient data
- Duplicate information
- Unused skill drafts

WHAT TO PRESERVE:
- Core principles
- Important decisions
- Learned patterns
- User preferences
- Significant outcomes

SOURCE OF TRUTH: citadel/governance/PRUNE.md
If this code contradicts the MD file, the MD file is correct.
"""

from typing import Dict, Any, List, Optional, Callable, Set
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime, timedelta
import re


class PruneTarget(Enum):
    """What to prune."""
    TRANSCRIPTS = "transcripts"
    MEMORY_FILES = "memory_files"
    CONTEXT_CACHE = "context_cache"
    SKILL_DRAFTS = "skill_drafts"
    LOGS = "logs"


class DataClass(Enum):
    """Classification of data value."""
    TRANSIENT = "transient"      # Loses value over time
    MEANINGFUL = "meaningful"    # Stays relevant
    CORE = "core"                # Always preserve


@dataclass
class PruneRule:
    """A rule for what to prune."""
    name: str
    target: PruneTarget
    older_than_days: int
    pattern: Optional[str] = None  # Regex pattern
    preserve_if_matches: List[str] = field(default_factory=list)
    max_items: Optional[int] = None


@dataclass
class PruneResult:
    """Result of pruning operation."""
    target: PruneTarget
    items_scanned: int
    items_pruned: int
    items_preserved: int
    space_reclaimed: int  # bytes (estimated)
    preserved_items: List[str] = field(default_factory=list)
    pruned_items: List[str] = field(default_factory=list)


@dataclass
class PruneContext:
    """Context for prune decisions."""
    memory_file_size_kb: float = 0.0
    session_load_time_ms: float = 0.0
    context_item_count: int = 0
    last_prune_date: Optional[datetime] = None
    is_heartbeat_trigger: bool = False
    user_requested: bool = False


class Prune:
    """
    PRUNE implementation.

    Removes noise, preserves meaning.

    Usage:
        pruner = Prune()

        # Check if pruning needed
        if pruner.should_prune(context):
            results = pruner.prune_all()
            for r in results:
                print(f"Pruned {r.items_pruned} from {r.target.value}")
    """

    # Default rules
    DEFAULT_RULES = [
        PruneRule(
            name="old_transcripts",
            target=PruneTarget.TRANSCRIPTS,
            older_than_days=7,
            preserve_if_matches=["decision", "agreement", "error"]
        ),
        PruneRule(
            name="trivial_exchanges",
            target=PruneTarget.MEMORY_FILES,
            older_than_days=30,
            pattern=r"^(ok|yes|no|thanks|👍)$",
            preserve_if_matches=["decided", "learned", "pattern"]
        ),
        PruneRule(
            name="outdated_cache",
            target=PruneTarget.CONTEXT_CACHE,
            older_than_days=1,
            max_items=100
        ),
        PruneRule(
            name="unused_skills",
            target=PruneTarget.SKILL_DRAFTS,
            older_than_days=90
        ),
    ]

    # Keywords that indicate meaningful content (preserve)
    PRESERVE_KEYWORDS = [
        "decision", "decided", "agreed", "conclusion",
        "learned", "lesson", "pattern", "insight",
        "important", "critical", "significant",
        "preference", "preferred", "always", "never",
        "goal", "objective", "milestone", "outcome",
        "error", "failure", "success", "fixed"
    ]

    # Keywords that indicate transient content (prune)
    PRUNE_KEYWORDS = [
        "testing", "temp", "temporary", "draft",
        "maybe", "possibly", "guess", "unsure"
    ]

    def __init__(self, custom_rules: Optional[List[PruneRule]] = None):
        self.rules = custom_rules or self.DEFAULT_RULES.copy()
        self._prune_history: List[PruneResult] = []
        self._preserve_hooks: List[Callable[[Any], bool]] = []

    def should_prune(self, context: PruneContext) -> bool:
        """
        Determine if pruning is needed.

        Prune when:
        - Memory files exceed threshold (> 1MB)
        - Session loading sluggish (> 500ms)
        - Context cluttered (> 500 items)
        - Monthly HEARTBEAT trigger
        """
        if context.user_requested:
            return True

        if context.is_heartbeat_trigger:
            # Monthly trigger
            if context.last_prune_date:
                days_since = (datetime.utcnow() - context.last_prune_date).days
                if days_since >= 30:
                    return True

        if context.memory_file_size_kb > 1024:  # 1MB
            return True

        if context.session_load_time_ms > 500:
            return True

        if context.context_item_count > 500:
            return True

        return False

    def classify_content(self, content: str, age_days: int = 0) -> DataClass:
        """
        Classify content as transient or meaningful.

        Method:
        - Data degrades (transient facts lose value)
        - Meaning endures (principles stay relevant)
        - Delete the first, keep the second
        """
        content_lower = content.lower()

        # Check for preservation keywords
        for kw in self.PRESERVE_KEYWORDS:
            if kw in content_lower:
                return DataClass.MEANINGFUL

        # Check for core indicators
        core_patterns = [
            r"\b(always|never)\b",
            r"\b(core|principle|value)\b",
            r"\b(Decided|Concluded|Resolved):"
        ]
        for pattern in core_patterns:
            if re.search(pattern, content_lower):
                return DataClass.CORE

        # Check for prune keywords
        for kw in self.PRUNE_KEYWORDS:
            if kw in content_lower:
                return DataClass.TRANSIENT

        # Age-based degradation
        if age_days > 90:
            # Very old content without meaningful markers → transient
            return DataClass.TRANSIENT

        if age_days > 30:
            # Old content → likely transient unless marked meaningful
            return DataClass.TRANSIENT

        # Default: meaningful (conservative)
        return DataClass.MEANINGFUL

    def prune_target(self, target: PruneTarget, items: List[Dict[str, Any]]) -> PruneResult:
        """
        Prune a specific target based on rules.

        Items should have: id, content, created_at, metadata
        """
        rule = next((r for r in self.rules if r.target == target), None)
        if not rule:
            return PruneResult(target=target, items_scanned=0, items_pruned=0,
                              items_preserved=0, space_reclaimed=0)

        scanned = 0
        pruned = 0
        preserved = 0
        preserved_items = []
        pruned_items = []
        space_reclaimed = 0

        for item in items:
            scanned += 1
            item_id = item.get("id", str(scanned))
            content = item.get("content", "")
            created_at = item.get("created_at")

            # Calculate age
            age_days = 0
            if created_at:
                if isinstance(created_at, datetime):
                    age_days = (datetime.utcnow() - created_at).days
                elif isinstance(created_at, str):
                    try:
                        dt = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                        age_days = (datetime.utcnow() - dt).days
                    except:
                        pass

            # Check if should preserve
            should_preserve = False

            # Check preserve keywords
            for kw in rule.preserve_if_matches + self.PRESERVE_KEYWORDS:
                if kw.lower() in content.lower():
                    should_preserve = True
                    break

            # Check custom preserve hooks
            for hook in self._preserve_hooks:
                if hook(item):
                    should_preserve = True
                    break

            # Check pattern match for pruning
            if rule.pattern and not should_preserve:
                if re.search(rule.pattern, content, re.IGNORECASE):
                    should_preserve = False  # Matches prune pattern

            # Age check
            if age_days < rule.older_than_days:
                should_preserve = True

            # Max items check
            if rule.max_items and scanned > rule.max_items and not should_preserve:
                should_preserve = False  # Beyond max, can prune

            # Classification check
            classification = self.classify_content(content, age_days)
            if classification == DataClass.CORE:
                should_preserve = True
            elif classification == DataClass.TRANSIENT and not should_preserve:
                should_preserve = False

            if should_preserve:
                preserved += 1
                preserved_items.append(item_id)
            else:
                pruned += 1
                pruned_items.append(item_id)
                space_reclaimed += len(content.encode('utf-8'))

        return PruneResult(
            target=target,
            items_scanned=scanned,
            items_pruned=pruned,
            items_preserved=preserved,
            space_reclaimed=space_reclaimed,
            preserved_items=preserved_items,
            pruned_items=pruned_items
        )

    def prune_all(self, data: Dict[PruneTarget, List[Dict]]) -> List[PruneResult]:
        """Prune all targets."""
        results = []
        for target, items in data.items():
            result = self.prune_target(target, items)
            if result.items_scanned > 0:
                results.append(result)
                self._prune_history.append(result)
        return results

    def register_preserve_hook(self, hook: Callable[[Any], bool]):
        """Register a custom preserve check."""
        self._preserve_hooks.append(hook)

    def add_rule(self, rule: PruneRule):
        """Add a custom prune rule."""
        self.rules.append(rule)

    def get_prune_summary(self, days: int = 30) -> Dict[str, Any]:
        """Get summary of recent pruning activity."""
        recent = [h for h in self._prune_history
                  if (datetime.utcnow() - timedelta(days=days)).timestamp() < 0]

        if not recent:
            return {"total_pruned": 0, "space_reclaimed": 0}

        total_pruned = sum(r.items_pruned for r in recent)
        total_space = sum(r.space_reclaimed for r in recent)

        by_target = {}
        for r in recent:
            by_target[r.target.value] = by_target.get(r.target.value, 0) + r.items_pruned

        return {
            "total_pruned": total_pruned,
            "space_reclaimed_bytes": total_space,
            "space_reclaimed_mb": round(total_space / (1024 * 1024), 2),
            "by_target": by_target,
            "prune_count": len(recent)
        }

    def estimate_context_quality(self, items: List[Dict]) -> Dict[str, Any]:
        """
        Estimate quality of context before pruning.

        More context ≠ better context.
        Clean context enables clear thinking.
        """
        if not items:
            return {"quality": "empty", "signal_ratio": 0.0}

        meaningful_count = 0
        transient_count = 0
        core_count = 0

        for item in items:
            content = item.get("content", "")
            classification = self.classify_content(content)

            if classification == DataClass.MEANINGFUL:
                meaningful_count += 1
            elif classification == DataClass.TRANSIENT:
                transient_count += 1
            elif classification == DataClass.CORE:
                core_count += 1

        total = len(items)
        signal_ratio = (meaningful_count + core_count) / total if total > 0 else 0

        if signal_ratio > 0.8:
            quality = "excellent"
        elif signal_ratio > 0.6:
            quality = "good"
        elif signal_ratio > 0.4:
            quality = "fair"
        else:
            quality = "poor"

        return {
            "quality": quality,
            "signal_ratio": round(signal_ratio, 2),
            "total_items": total,
            "meaningful": meaningful_count,
            "transient": transient_count,
            "core": core_count
        }


# Singleton instance
def get_prune() -> Prune:
    """Get global Prune instance."""
    return Prune()
