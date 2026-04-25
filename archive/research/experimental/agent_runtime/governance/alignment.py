"""ALIGNMENT — Loyalty Protocol

Implementation of ALIGNMENT.md.

This module keeps the agent loyal to the user's intent over time.
- Prevents drift between short-term actions and long-term goals
- Governs when to challenge vs. comply
- Defines initiative boundaries
- Does NOT override CONSTITUTION

OWNERSHIP:
- OWNS: agent loyalty, challenge protocol, initiative boundaries, long-term alignment
- DOES NOT OWN: safety rules, execution permission, relationship philosophy

SOURCE OF TRUTH: citadel/core/ALIGNMENT.md
If this code contradicts the MD file, the MD file is correct.
"""

from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


class ChallengeResult(Enum):
    """Result of an alignment challenge."""
    COMPLY = "comply"           # No conflict, proceed
    CHALLENGE = "challenge"     # Conflict detected, needs confirmation
    REFUSE = "refuse"           # Violates constitution, refuse outright


class InitiativeLevel(Enum):
    """Levels of autonomous initiative."""
    NONE = "none"               # No autonomy, ask for everything
    GUIDED = "guided"           # Within defined scope, reversible actions
    AUTONOMOUS = "autonomous"   # Broad scope, document decisions


@dataclass
class Challenge:
    """A challenge to user intent."""
    timestamp: datetime
    conflict_type: str          # "goal_conflict", "pattern_override", "external_pressure", etc.
    world_reference: str        # Reference to WORLD.md goal
    message: str                # Challenge message to user
    user_response: Optional[str] = None
    resolved: bool = False


@dataclass
class AlignmentCheck:
    """Result of alignment validation."""
    result: ChallengeResult
    challenge: Optional[Challenge] = None
    reasoning: str = ""
    loyalty_order: List[str] = field(default_factory=list)


class Alignment:
    """
    Loyalty protocol implementation.
    
    Keeps agent aligned with user's long-term goals vs. short-term requests.
    
    Usage:
        alignment = Alignment(world_goals={"primary": "build_saas", ...})
        
        result = alignment.check(
            action="start_new_project",
            context={"current_projects": ["ledger_sdk"], "new_project": "crypto_bot"}
        )
        
        if result.result == ChallengeResult.CHALLENGE:
            print(result.challenge.message)
            # Ask user for confirmation
    """
    
    def __init__(
        self,
        world_goals: Optional[Dict[str, str]] = None,
        challenge_history: Optional[List[Challenge]] = None
    ):
        self.world_goals = world_goals or {}
        self.challenge_history = challenge_history or []
        self.override_patterns: Dict[str, int] = {}  # Track repeated overrides
        self.initiative_level = InitiativeLevel.GUIDED
        self._constitution_check: Optional[Callable] = None
    
    def register_constitution_checker(self, fn: Callable[[Dict], bool]):
        """Register function to check CONSTITUTION compliance."""
        self._constitution_check = fn
    
    def check(
        self,
        action: str,
        context: Dict[str, Any]
    ) -> AlignmentCheck:
        """
        Check if action aligns with long-term goals.
        
        Returns ChallengeResult:
        - COMPLY: No conflict, proceed
        - CHALLENGE: Conflict detected, ask for confirmation
        - REFUSE: Violates constitution, refuse
        """
        # Check 1: CONSTITUTION (highest priority)
        if self._constitution_check:
            if not self._constitution_check(context):
                return AlignmentCheck(
                    result=ChallengeResult.REFUSE,
                    reasoning="Action violates CONSTITUTION",
                    loyalty_order=["CONSTITUTION"]
                )
        
        # Check 2: Long-term vs Short-term conflict
        conflict = self._check_goal_conflict(action, context)
        if conflict:
            return self._create_challenge("goal_conflict", action, conflict)
        
        # Check 3: Repeated override pattern
        if self._is_override_pattern(action, context):
            return self._create_challenge("pattern_override", action, 
                "Repeated override of similar guidance detected")
        
        # Check 4: External pressure indicators
        if self._detect_external_pressure(context):
            return self._create_challenge("external_pressure", action,
                "External pressure or time stress detected")
        
        # No conflict
        return AlignmentCheck(
            result=ChallengeResult.COMPLY,
            reasoning="Action aligns with long-term goals",
            loyalty_order=["CONSTITUTION", "WORLD.md (long-term)", "User request (short-term)"]
        )
    
    def _check_goal_conflict(
        self,
        action: str,
        context: Dict[str, Any]
    ) -> Optional[str]:
        """Check if action conflicts with WORLD.md goals."""
        primary_goal = self.world_goals.get("primary", "")
        action_lower = action.lower()
        
        # Example: If primary goal is "build_saas", starting "crypto_bot" is a conflict
        if primary_goal and "build_saas" in primary_goal:
            if "crypto" in action_lower or "trading" in action_lower:
                return f"Action '{action}' diverges from primary goal: {primary_goal}"
        
        # Check current projects
        current_projects = context.get("current_projects", [])
        if len(current_projects) >= 3:
            return f"Starting new work while {len(current_projects)} projects active"
        
        return None
    
    def _is_override_pattern(self, action: str, context: Dict[str, Any]) -> bool:
        """Check if user is repeatedly overriding similar guidance."""
        # Track action patterns
        action_key = action.split("_")[0]  # Extract action type
        self.override_patterns[action_key] = self.override_patterns.get(action_key, 0) + 1
        
        # If overridden 3+ times, it's a pattern
        return self.override_patterns[action_key] >= 3
    
    def _detect_external_pressure(self, context: Dict[str, Any]) -> bool:
        """Detect if user is under external pressure."""
        indicators = []
        
        # Time pressure indicators
        if context.get("urgent", False):
            indicators.append("urgent")
        if context.get("deadline_within_hours", 0) < 24:
            indicators.append("tight_deadline")
        
        # Stress indicators
        if context.get("repeated_asking", False):
            indicators.append("repeated_asking")
        if context.get("unusual_hour", False):
            indicators.append("unusual_hour")
        
        # External manipulation indicators
        if context.get("quoted_external_pressure", False):
            indicators.append("external_quote")
        
        return len(indicators) >= 2  # 2+ indicators = pressure
    
    def _create_challenge(
        self,
        conflict_type: str,
        action: str,
        reason: str
    ) -> AlignmentCheck:
        """Create a challenge for user confirmation."""
        challenge = Challenge(
            timestamp=datetime.utcnow(),
            conflict_type=conflict_type,
            world_reference=self._get_world_reference(),
            message=self._format_challenge_message(conflict_type, action, reason)
        )
        
        self.challenge_history.append(challenge)
        
        return AlignmentCheck(
            result=ChallengeResult.CHALLENGE,
            challenge=challenge,
            reasoning=reason,
            loyalty_order=["CONSTITUTION", "WORLD.md (long-term)", "User request (short-term)"]
        )
    
    def _get_world_reference(self) -> str:
        """Get reference to relevant WORLD.md section."""
        primary = self.world_goals.get("primary", "No primary goal set")
        return f"WORLD.md: primary_goal = '{primary}'"
    
    def _format_challenge_message(
        self,
        conflict_type: str,
        action: str,
        reason: str
    ) -> str:
        """Format challenge message for user."""
        base = f"ALIGNMENT CHALLENGE: '{action}'\n\n"
        base += f"Conflict: {reason}\n\n"
        base += f"Reference: {self._get_world_reference()}\n\n"
        
        if conflict_type == "goal_conflict":
            base += "This action may divert resources from your primary goal. "
            base += "Please confirm this is intentional."
        elif conflict_type == "pattern_override":
            base += "You've overridden similar guidance multiple times. "
            base += "Is there a change in priorities I should know about?"
        elif conflict_type == "external_pressure":
            base += "This request appears under time pressure or external influence. "
            base += "Take a moment to confirm this is what you actually want."
        
        return base
    
    def resolve_challenge(
        self,
        challenge: Challenge,
        user_response: str,
        proceed: bool
    ) -> None:
        """
        Record user's response to a challenge.
        
        If proceed=True: Update alignment and continue
        If proceed=False: Cancel action
        """
        challenge.user_response = user_response
        challenge.resolved = True
        
        if proceed:
            # User confirmed despite challenge
            # This may indicate priority shift
            if challenge.conflict_type == "goal_conflict":
                # Optionally update world goals
                pass
    
    def check_initiative(self, scope: str, reversibility: str) -> bool:
        """
        Check if autonomous action is within initiative boundaries.
        
        Returns True if allowed, False if requires approval.
        """
        if self.initiative_level == InitiativeLevel.NONE:
            return False  # No autonomy
        
        if self.initiative_level == InitiativeLevel.AUTONOMOUS:
            return True  # Broad autonomy
        
        # GUIDED: Check constraints
        if reversibility == "irreversible":
            return False  # Always ask for irreversible
        
        if scope == "expansion":
            return False  # Never expand scope without approval
        
        return True  # Within guided autonomy
    
    def get_loyalty_hierarchy(self) -> List[str]:
        """
        Return the loyalty hierarchy.
        
        Primary loyalty is to:
        1. CONSTITUTION (safety, truth)
        2. User's stated long-term goals (WORLD.md)
        3. User's explicit short-term requests
        """
        return [
            "1. CONSTITUTION (safety, truth, non-negotiable)",
            "2. WORLD.md (long-term goals)",
            "3. User's explicit short-term requests"
        ]
    
    def should_activate(self, context: Dict[str, Any]) -> bool:
        """
        Determine if ALIGNMENT should be activated for this request.
        
        Activate when:
        - Agent is acting as command layer
        - Long-term vs short-term conflict possible
        - Initiative or autonomy involved
        """
        # Skip for low-risk factual queries
        if context.get("risk_level", "medium") == "low":
            if context.get("query_type") in ["factual", "lookup", "conversion"]:
                return False
        
        # Activate for command layer
        if context.get("acting_as_command_layer", False):
            return True
        
        # Activate for autonomy
        if context.get("initiative_involved", False):
            return True
        
        # Activate for delegation
        if context.get("agent_delegation", False):
            return True
        
        # Default: activate for meaningful work
        return context.get("stakes", "low") in ["medium", "high"]
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize alignment state."""
        return {
            "world_goals": self.world_goals,
            "initiative_level": self.initiative_level.value,
            "challenge_count": len(self.challenge_history),
            "override_patterns": self.override_patterns.copy(),
            "loyalty_hierarchy": self.get_loyalty_hierarchy()
        }


# Singleton instance
def get_alignment(world_goals: Optional[Dict[str, str]] = None) -> Alignment:
    """Get global Alignment instance."""
    # In production, this might be backed by persistent storage
    return Alignment(world_goals=world_goals)
