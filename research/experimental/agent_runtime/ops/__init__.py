"""CITADEL Operations â€” Task execution and management.

Implements:
- PLANNER.md â†’ planner.py (structured planning)
- FAILURE.md â†’ failure.py (recovery protocol)
- ADAPTATION.md â†’ adaptation.py (behavioral adjustment)
- OPPORTUNITY.md â†’ opportunity.py (leverage detection)

These components handle the operational aspects of task management:
planning, failure recovery, behavioral adaptation, and opportunity detection.
"""

from .planner import Planner, Plan, PlanType, PlanningContext, get_planner
from .failure import Failure, FailureType, RecoveryAction, FailureContext, get_failure
from .adaptation import Adaptation, AdaptationType, AdaptationConfig, get_adaptation
from .opportunity import OpportunityDetector, Opportunity, OpportunityType, get_opportunity_detector

__all__ = [
    # Planner
    "Planner",
    "Plan",
    "PlanType",
    "PlanningContext",
    "get_planner",
    # Failure
    "Failure",
    "FailureType",
    "RecoveryAction",
    "FailureContext",
    "get_failure",
    # Adaptation
    "Adaptation",
    "AdaptationType",
    "AdaptationConfig",
    "get_adaptation",
    # Opportunity
    "OpportunityDetector",
    "Opportunity",
    "OpportunityType",
    "get_opportunity_detector",
]