"""FOCUS — Anti-Distraction Bouncer

Implementation of FOCUS.md.

OWNERSHIP:
- OWNS: scope protection, task filtering, anti-distraction enforcement
- DOES NOT OWN: planning, execution quality, relationship philosophy

PURPOSE:
FOCUS keeps work on track.
- Blocks scope creep
- Deflects distractions
- Protects deep work from interruption
- Enforces the plan boundaries

DISTRACTION PATTERNS:
Watch for:
- User adds new tasks mid-work
- Scope expands without approval
- Shiny object syndrome
- "Just one more thing"
- Emergency requests that aren't emergencies

DEFENSE STRATEGIES:
1. Acknowledge: "That's a valid task."
2. Bound: "We'll queue that for after this work."
3. Protect: "Finishing current task first."

EMERGENCY OVERRIDE:
True emergencies exist:
- system down
- data loss imminent
- safety issue

SOURCE OF TRUTH: ledger/system/FOCUS.md
If this code contradicts the MD file, the MD file is correct.
"""

from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime
import uuid


class DistractionType(Enum):
    """Types of distractions per FOCUS.md."""
    NEW_TASK = "new_task"              # User adds task mid-work
    SCOPE_EXPANSION = "scope_expansion"  # Scope grows without approval
    SHINY_OBJECT = "shiny_object"      # Tangential interesting thing
    ONE_MORE_THING = "one_more_thing"  # Additional request
    FALSE_EMERGENCY = "false_emergency"  # Urgent but not emergency


class DefenseStrategy(Enum):
    """Defense strategies per FOCUS.md."""
    ACKNOWLEDGE = "acknowledge"    # Validate the item
    BOUND = "bound"                # Place it appropriately
    PROTECT = "protect"            # Return to current work


class FocusState(Enum):
    """Current focus state."""
    IDLE = "idle"
    FOCUSED = "focused"            # Normal work
    DEEP_WORK = "deep_work"        # Protected flow state
    INTERRUPTED = "interrupted"    # Recently distracted


@dataclass
class CurrentTask:
    """The current task being protected."""
    id: str
    description: str
    started_at: datetime
    priority: str
    plan_id: Optional[str] = None
    milestone_id: Optional[str] = None
    scope_boundaries: List[str] = field(default_factory=list)
    protected: bool = False  # Deep work mode


@dataclass
class Distraction:
    """A detected distraction attempt."""
    id: str
    type: DistractionType
    description: str
    detected_at: datetime
    context: str
    is_true_emergency: bool = False
    deflected: bool = False
    deflection_strategy: Optional[DefenseStrategy] = None
    user_response: Optional[str] = None
    queued_for_later: bool = False


@dataclass
class FocusContext:
    """Context for focus decisions."""
    current_task: Optional[CurrentTask] = None
    focus_state: FocusState = FocusState.IDLE
    recent_distractions: int = 0
    deep_work_minutes: int = 0
    user_stated_priority: str = ""


class Focus:
    """
    FOCUS implementation.

    Anti-distraction bouncer.

    Usage:
        focus = Focus()

        # Set current task
        focus.enter_focus(
            task_id="deploy-123",
            description="Deploy production release",
            priority="high",
            protected=True  # Deep work mode
        )

        # Check incoming request
        if focus.is_distraction(new_request):
            response = focus.deflect(new_request)
            # "We'll queue that for after this work."
    """

    # Patterns indicating distractions
    DISTRACTION_INDICATORS = {
        DistractionType.NEW_TASK: [
            "also", "while you're at it", "can you also",
            "quick thing", "small request"
        ],
        DistractionType.SCOPE_EXPANSION: [
            "and also", "plus", "might as well", "since you're there",
            "expand this to", "include"
        ],
        DistractionType.SHINY_OBJECT: [
            "interesting idea", "saw this and thought", "just saw",
            "check this out", "you should look at"
        ],
        DistractionType.ONE_MORE_THING: [
            "one more thing", "last thing", "finally",
            "and another", "oh and"
        ],
        DistractionType.FALSE_EMERGENCY: [
            "urgent", "asap", "hurry", "quickly",
            "need this now"
        ]
    }

    # True emergency indicators (override FOCUS)
    EMERGENCY_INDICATORS = [
        "system down", "down", "outage",
        "data loss", "losing data", "corruption",
        "security breach", "attacked", "hacked",
        "safety", "danger", "injury", "medical"
    ]

    def __init__(self):
        self._current_task: Optional[CurrentTask] = None
        self._distraction_history: List[Distraction] = []
        self._deferred_queue: List[Dict[str, Any]] = []
        self._scope_change_callback: Optional[Callable[[str, str], bool]] = None

    def register_scope_change_callback(self, callback: Callable[[str, str], bool]):
        """Register callback for scope change approval. Returns True if approved."""
        self._scope_change_callback = callback

    def enter_focus(
        self,
        task_id: str,
        description: str,
        priority: str = "normal",
        plan_id: Optional[str] = None,
        scope_boundaries: Optional[List[str]] = None,
        protected: bool = False
    ) -> CurrentTask:
        """
        Enter focused work mode.

        If protected=True, enters DEEP_WORK state (minimal interruptions).
        """
        self._current_task = CurrentTask(
            id=task_id,
            description=description,
            started_at=datetime.utcnow(),
            priority=priority,
            plan_id=plan_id,
            scope_boundaries=scope_boundaries or [],
            protected=protected
        )

        return self._current_task

    def exit_focus(self, reason: str) -> Dict[str, Any]:
        """Exit focused work mode."""
        if not self._current_task:
            return {"exited": False, "reason": "no_active_task"}

        duration = (datetime.utcnow() - self._current_task.started_at).total_seconds() / 60

        result = {
            "exited": True,
            "task_id": self._current_task.id,
            "duration_minutes": duration,
            "reason": reason,
            "distractions_during": len([d for d in self._distraction_history
                                         if d.detected_at >= self._current_task.started_at]),
            "deferred_items": len(self._deferred_queue)
        }

        self._current_task = None
        return result

    def get_state(self) -> FocusState:
        """Get current focus state."""
        if not self._current_task:
            return FocusState.IDLE

        if self._current_task.protected:
            return FocusState.DEEP_WORK

        return FocusState.FOCUSED

    def is_distraction(self, request: str) -> bool:
        """
        Check if a request is a distraction from current work.

        First checks for true emergencies (not distractions).
        Then checks for distraction patterns.
        """
        # Check for true emergency (not a distraction)
        if self._is_true_emergency(request):
            return False  # Emergencies are not distractions

        # Check for distraction patterns
        for dtype, indicators in self.DISTRACTION_INDICATORS.items():
            for indicator in indicators:
                if indicator.lower() in request.lower():
                    return True

        # Check if scope expansion
        if self._current_task and self._is_scope_expansion(request):
            return True

        return False

    def _is_true_emergency(self, request: str) -> bool:
        """Check if request is a true emergency."""
        request_lower = request.lower()
        for indicator in self.EMERGENCY_INDICATORS:
            if indicator in request_lower:
                return True
        return False

    def _is_scope_expansion(self, request: str) -> bool:
        """Check if request expands current scope."""
        if not self._current_task:
            return False

        # Simple heuristic: request mentions things outside scope boundaries
        # In production, would use semantic analysis
        current_scope = " ".join(self._current_task.scope_boundaries).lower()
        request_lower = request.lower()

        # If request is about something entirely different
        # This is a simplified check
        return False  # Default to not scope expansion

    def classify_distraction(self, request: str) -> Optional[DistractionType]:
        """Classify the type of distraction."""
        for dtype, indicators in self.DISTRACTION_INDICATORS.items():
            for indicator in indicators:
                if indicator.lower() in request.lower():
                    return dtype
        return None

    def deflect(self, request: str, context: str = "") -> Dict[str, Any]:
        """
        Deflect a distraction using defense strategies.

        1. Acknowledge: "That's a valid task."
        2. Bound: "We'll queue that for after this work."
        3. Protect: "Finishing current task first."

        Returns deflection response.
        """
        if not self._current_task:
            return {"deflected": False, "reason": "no_active_task"}

        distraction_type = self.classify_distraction(request) or DistractionType.NEW_TASK

        # Check if true emergency (should not deflect)
        if self._is_true_emergency(request):
            distraction = Distraction(
                id=str(uuid.uuid4())[:8],
                type=distraction_type,
                description=request,
                detected_at=datetime.utcnow(),
                context=context,
                is_true_emergency=True,
                deflected=False
            )
            self._distraction_history.append(distraction)

            return {
                "deflected": False,
                "reason": "true_emergency",
                "message": "Emergency detected. Interrupting current work.",
                "current_task": self._current_task.description
            }

        # Apply defense strategy
        strategy = self._select_strategy(distraction_type)

        distraction = Distraction(
            id=str(uuid.uuid4())[:8],
            type=distraction_type,
            description=request,
            detected_at=datetime.utcnow(),
            context=context,
            deflected=True,
            deflection_strategy=strategy,
            queued_for_later=True
        )
        self._distraction_history.append(distraction)

        # Queue for later
        self._deferred_queue.append({
            "request": request,
            "context": context,
            "queued_at": datetime.utcnow(),
            "distraction_id": distraction.id
        })

        # Generate response
        message = self._generate_deflection_message(strategy, distraction_type)

        return {
            "deflected": True,
            "strategy": strategy.value,
            "distraction_type": distraction_type.value,
            "message": message,
            "current_task": self._current_task.description,
            "queued_for_later": True
        }

    def _select_strategy(self, distraction_type: DistractionType) -> DefenseStrategy:
        """Select defense strategy based on distraction type."""
        if distraction_type == DistractionType.SCOPE_EXPANSION:
            return DefenseStrategy.ACKNOWLEDGE  # Acknowledge then assess
        elif distraction_type == DistractionType.FALSE_EMERGENCY:
            return DefenseStrategy.ACKNOWLEDGE  # Acknowledge but verify
        else:
            return DefenseStrategy.BOUND  # Default: bound and queue

    def _generate_deflection_message(
        self,
        strategy: DefenseStrategy,
        distraction_type: DistractionType
    ) -> str:
        """Generate appropriate deflection message."""
        if not self._current_task:
            return "No active task."

        task_desc = self._current_task.description

        if strategy == DefenseStrategy.ACKNOWLEDGE:
            return f"That's a valid {distraction_type.value.replace('_', ' ')}. I'm currently working on '{task_desc}'. Let me finish this first, then we'll address your request."

        elif strategy == DefenseStrategy.BOUND:
            return f"I'll queue that for after '{task_desc}'. Currently focused on completing this work."

        elif strategy == DefenseStrategy.PROTECT:
            return f"Finishing '{task_desc}' first. Your request is queued for next."

        return f"Focusing on '{task_desc}' right now."

    def handle_scope_change(self, new_scope_request: str) -> Dict[str, Any]:
        """
        Handle scope change request.

        Per FOCUS.md:
        - Stop current execution
        - Assess impact
        - Require explicit replanning
        - Document the change

        Do not silently absorb new work.
        """
        if not self._current_task:
            return {"handled": False, "reason": "no_active_task"}

        # Require explicit approval
        if self._scope_change_callback:
            approved = self._scope_change_callback(
                self._current_task.id,
                new_scope_request
            )
        else:
            approved = False  # Default: reject without explicit approval

        if approved:
            # Document the change
            distraction = Distraction(
                id=str(uuid.uuid4())[:8],
                type=DistractionType.SCOPE_EXPANSION,
                description=f"SCOPE CHANGE APPROVED: {new_scope_request}",
                detected_at=datetime.utcnow(),
                context="explicit scope change request",
                deflected=False,  # Not deflected - approved
                user_response="approved"
            )
            self._distraction_history.append(distraction)

            return {
                "handled": True,
                "approved": True,
                "action": "replan_required",
                "message": "Scope change approved. Replanning required before continuing.",
                "previous_scope": self._current_task.scope_boundaries,
                "new_scope_request": new_scope_request
            }
        else:
            # Reject scope change
            return self.deflect(new_scope_request, "scope_change_rejected")

    def get_deferred_queue(self) -> List[Dict[str, Any]]:
        """Get items deferred for later."""
        return self._deferred_queue.copy()

    def clear_deferred_item(self, item_id: str) -> bool:
        """Mark deferred item as addressed."""
        for i, item in enumerate(self._deferred_queue):
            if item.get("distraction_id") == item_id:
                self._deferred_queue.pop(i)
                return True
        return False

    def get_stats(self) -> Dict[str, Any]:
        """Get focus statistics."""
        total_distractions = len(self._distraction_history)
        deflected = len([d for d in self._distraction_history if d.deflected])
        true_emergencies = len([d for d in self._distraction_history if d.is_true_emergency])

        by_type = {}
        for d in self._distraction_history:
            by_type[d.type.value] = by_type.get(d.type.value, 0) + 1

        return {
            "current_state": self.get_state().value,
            "current_task_id": self._current_task.id if self._current_task else None,
            "total_distractions_detected": total_distractions,
            "deflected": deflected,
            "true_emergencies": true_emergencies,
            "by_type": by_type,
            "deferred_queue_size": len(self._deferred_queue)
        }


# Singleton instance
def get_focus() -> Focus:
    """Get global Focus instance."""
    return Focus()
