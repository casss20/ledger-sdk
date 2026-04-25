"""OPPORTUNITY — Leverage Detection

Implementation of OPPORTUNITY.md.

PURPOSE:
Detect and surface opportunities for the user.

OPPORTUNITY TYPES:
Skills:
- New skills available
- Existing skills could be combined
- Skills gaps identified

Integrations:
- New tools connectable
- Workflows could be automated
- APIs available

Knowledge:
- New patterns learned
- Insights from past work
- Cross-domain applications

Time:
- Calendar gaps for deep work
- Tasks that could be delegated
- Automation candidates

SURFACING:
Bring opportunities to user when:
- Relevant to current context
- Actionable now
- Value exceeds effort

Do not:
- Interrupt focused work
- Surface every small thing
- Create FOMO

SOURCE OF TRUTH: citadel/ops/OPPORTUNITY.md
If this code contradicts the MD file, the MD file is correct.
"""

from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass, field
from enum import Enum, auto
from datetime import datetime
from collections import defaultdict
import uuid


class OpportunityType(Enum):
    """Types of opportunities per OPPORTUNITY.md."""
    SKILL = "skill"              # New/combined skills, gaps
    INTEGRATION = "integration"  # Tools, workflows, APIs
    KNOWLEDGE = "knowledge"      # Patterns, insights, cross-domain
    TIME = "time"                # Calendar gaps, delegation, automation


class OpportunityPriority(Enum):
    """Priority of opportunity."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


@dataclass
class Opportunity:
    """An identified opportunity."""
    id: str
    type: OpportunityType
    title: str
    description: str
    context_relevance: str
    value_estimate: str  # qualitative
    effort_estimate: str  # low, medium, high
    priority: OpportunityPriority
    actionable_now: bool
    created_at: datetime
    expires_at: Optional[datetime] = None
    surfaced_at: Optional[datetime] = None
    user_response: Optional[str] = None  # acknowledged, dismissed, acted
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class DetectionContext:
    """Context for opportunity detection."""
    current_task: str = ""
    recent_patterns: List[str] = field(default_factory=list)
    available_skills: List[str] = field(default_factory=list)
    connected_tools: List[str] = field(default_factory=list)
    calendar_gaps: List[Dict] = field(default_factory=list)
    user_focus_level: str = "normal"  # deep, normal, interrupted
    time_of_day: str = "work_hours"  # morning, work_hours, evening


class OpportunityDetector:
    """
    OPPORTUNITY implementation.

    Detects and surfaces opportunities for the user.

    Usage:
        detector = OpportunityDetector()

        # Detect opportunities
        context = DetectionContext(
            current_task="building_api",
            available_skills=["python", "postgres"],
            recent_patterns=["manual_data_entry"]
        )

        opportunities = detector.detect(context)

        # Surface high-value opportunities
        for opp in detector.filter_for_surfacing(opportunities):
            if detector.should_surface(opp, context):
                detector.surface(opp)
    """

    def __init__(self):
        self._opportunities: Dict[str, Opportunity] = {}
        self._detection_hooks: Dict[OpportunityType, List[Callable]] = defaultdict(list)
        self._surface_history: List[str] = []
        self._surface_hook: Optional[Callable[[Opportunity], bool]] = None
        self._register_default_detectors()

    def _register_default_detectors(self):
        """Register default opportunity detection methods."""
        self._detection_hooks[OpportunityType.SKILL] = [self._detect_skill_opportunities]
        self._detection_hooks[OpportunityType.INTEGRATION] = [self._detect_integration_opportunities]
        self._detection_hooks[OpportunityType.KNOWLEDGE] = [self._detect_knowledge_opportunities]
        self._detection_hooks[OpportunityType.TIME] = [self._detect_time_opportunities]

    def register_surface_hook(self, hook: Callable[[Opportunity], bool]):
        """Register hook for surfacing opportunities to user."""
        self._surface_hook = hook

    def detect(self, context: DetectionContext) -> List[Opportunity]:
        """
        Detect opportunities from context.

        Runs all registered detection hooks.
        """
        opportunities = []

        for opp_type, hooks in self._detection_hooks.items():
            for hook in hooks:
                detected = hook(context)
                opportunities.extend(detected)

        # Store opportunities
        for opp in opportunities:
            self._opportunities[opp.id] = opp

        return opportunities

    def _detect_skill_opportunities(self, context: DetectionContext) -> List[Opportunity]:
        """Detect skill-related opportunities."""
        opportunities = []
        available = set(context.available_skills)

        # Check for skill combinations
        if "python" in available and "postgres" in available:
            if "sqlalchemy" not in available:
                opportunities.append(Opportunity(
                    id=str(uuid.uuid4())[:8],
                    type=OpportunityType.SKILL,
                    title="Add SQLAlchemy skill",
                    description="You have Python and Postgres - SQLAlchemy would streamline database work",
                    context_relevance="Current task involves database operations",
                    value_estimate="high",
                    effort_estimate="low",
                    priority=OpportunityPriority.MEDIUM,
                    actionable_now=True,
                    created_at=datetime.utcnow()
                ))

        # Check for skill gaps
        if context.current_task == "building_api" and "fastapi" not in available:
            opportunities.append(Opportunity(
                id=str(uuid.uuid4())[:8],
                type=OpportunityType.SKILL,
                title="Learn FastAPI",
                description="Building APIs - FastAPI is modern, fast, and Python-native",
                context_relevance="Directly relevant to current API work",
                value_estimate="high",
                effort_estimate="medium",
                priority=OpportunityPriority.HIGH,
                actionable_now=True,
                created_at=datetime.utcnow()
            ))

        return opportunities

    def _detect_integration_opportunities(self, context: DetectionContext) -> List[Opportunity]:
        """Detect integration opportunities."""
        opportunities = []

        # Check for workflow automation
        if "manual_data_entry" in context.recent_patterns:
            opportunities.append(Opportunity(
                id=str(uuid.uuid4())[:8],
                type=OpportunityType.INTEGRATION,
                title="Automate data entry workflow",
                description="Pattern detected: manual data entry. This could be automated.",
                context_relevance="Recent work shows repetitive manual work",
                value_estimate="high",
                effort_estimate="medium",
                priority=OpportunityPriority.HIGH,
                actionable_now=True,
                created_at=datetime.utcnow()
            ))

        # Check for tool combinations
        tools = set(context.connected_tools)
        if "github" in tools and "slack" in tools:
            opportunities.append(Opportunity(
                id=str(uuid.uuid4())[:8],
                type=OpportunityType.INTEGRATION,
                title="GitHub → Slack notifications",
                description="Connect GitHub events to Slack for team visibility",
                context_relevance="Both tools already connected",
                value_estimate="medium",
                effort_estimate="low",
                priority=OpportunityPriority.LOW,
                actionable_now=True,
                created_at=datetime.utcnow()
            ))

        return opportunities

    def _detect_knowledge_opportunities(self, context: DetectionContext) -> List[Opportunity]:
        """Detect knowledge/pattern opportunities."""
        opportunities = []

        # Check for patterns that could be reused
        if len(context.recent_patterns) >= 3:
            opportunities.append(Opportunity(
                id=str(uuid.uuid4())[:8],
                type=OpportunityType.KNOWLEDGE,
                title="Document recurring patterns",
                description=f"{len(context.recent_patterns)} patterns detected - some may be reusable",
                context_relevance="Pattern density suggests reusable components",
                value_estimate="medium",
                effort_estimate="low",
                priority=OpportunityPriority.MEDIUM,
                actionable_now=False,  # Not urgent
                created_at=datetime.utcnow()
            ))

        return opportunities

    def _detect_time_opportunities(self, context: DetectionContext) -> List[Opportunity]:
        """Detect time/delegation opportunities."""
        opportunities = []

        # Calendar gaps for deep work
        for gap in context.calendar_gaps:
            if gap.get("duration_hours", 0) >= 2:
                opportunities.append(Opportunity(
                    id=str(uuid.uuid4())[:8],
                    type=OpportunityType.TIME,
                    title=f"{gap['duration_hours']}h deep work block available",
                    description=f"Calendar gap: {gap.get('start')} - {gap.get('end')}. Good for focused work.",
                    context_relevance="Free time aligns with productive hours",
                    value_estimate="high",
                    effort_estimate="low",
                    priority=OpportunityPriority.MEDIUM,
                    actionable_now=True,
                    created_at=datetime.utcnow()
                ))

        return opportunities

    def filter_for_surfacing(
        self,
        opportunities: List[Opportunity],
        context: DetectionContext
    ) -> List[Opportunity]:
        """
        Filter opportunities that should be surfaced.

        Criteria:
        - Relevant to current context
        - Actionable now
        - Value exceeds effort
        """
        filtered = []

        for opp in opportunities:
            # Skip if not actionable during deep focus
            if context.user_focus_level == "deep" and opp.priority != OpportunityPriority.URGENT:
                continue

            # Skip if low priority and not relevant
            if opp.priority == OpportunityPriority.LOW and not opp.actionable_now:
                continue

            # Check value vs effort
            if opp.effort_estimate == "high" and opp.value_estimate != "high":
                continue

            filtered.append(opp)

        # Sort by priority
        priority_order = {
            OpportunityPriority.URGENT: 0,
            OpportunityPriority.HIGH: 1,
            OpportunityPriority.MEDIUM: 2,
            OpportunityPriority.LOW: 3
        }

        return sorted(filtered, key=lambda o: priority_order.get(o.priority, 4))

    def should_surface(self, opportunity: Opportunity, context: DetectionContext) -> bool:
        """
        Determine if an opportunity should be surfaced now.

        Do not:
        - Interrupt focused work
        - Surface every small thing
        - Create FOMO
        """
        # Never interrupt deep focus unless urgent
        if context.user_focus_level == "deep":
            return opportunity.priority == OpportunityPriority.URGENT

        # Don't surface if already surfaced
        if opportunity.id in self._surface_history:
            return False

        # Don't surface if user dismissed it
        if opportunity.user_response == "dismissed":
            return False

        # Time-based rules
        if context.time_of_day == "evening" and opportunity.priority != OpportunityPriority.URGENT:
            return False  # Don't surface non-urgent in evening

        return True

    def surface(self, opportunity: Opportunity) -> bool:
        """
        Surface opportunity to user.

        Returns True if successfully surfaced.
        """
        if self._surface_hook:
            success = self._surface_hook(opportunity)
            if success:
                opportunity.surfaced_at = datetime.utcnow()
                self._surface_history.append(opportunity.id)
            return success

        return False

    def acknowledge(self, opportunity_id: str, response: str) -> bool:
        """Record user response to surfaced opportunity."""
        opp = self._opportunities.get(opportunity_id)
        if opp:
            opp.user_response = response
            return True
        return False

    def get_opportunities(
        self,
        type_filter: Optional[OpportunityType] = None,
        status_filter: Optional[str] = None
    ) -> List[Opportunity]:
        """Get opportunities, optionally filtered."""
        opps = list(self._opportunities.values())

        if type_filter:
            opps = [o for o in opps if o.type == type_filter]

        if status_filter:
            if status_filter == "surfaced":
                opps = [o for o in opps if o.surfaced_at is not None]
            elif status_filter == "pending":
                opps = [o for o in opps if o.surfaced_at is None]
            elif status_filter == "acted":
                opps = [o for o in opps if o.user_response == "acted"]

        return opps

    def get_stats(self) -> Dict[str, Any]:
        """Get opportunity statistics."""
        by_type = defaultdict(int)
        by_priority = defaultdict(int)
        acted_count = 0

        for opp in self._opportunities.values():
            by_type[opp.type.value] += 1
            by_priority[opp.priority.value] += 1
            if opp.user_response == "acted":
                acted_count += 1

        total = len(self._opportunities)
        conversion_rate = acted_count / total if total > 0 else 0

        return {
            "total_opportunities": total,
            "surfaced_count": len(self._surface_history),
            "acted_count": acted_count,
            "conversion_rate": round(conversion_rate, 2),
            "by_type": dict(by_type),
            "by_priority": dict(by_priority)
        }


# Singleton instance
def get_opportunity_detector() -> OpportunityDetector:
    """Get global OpportunityDetector instance."""
    return OpportunityDetector()
