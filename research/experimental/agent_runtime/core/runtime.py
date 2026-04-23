"""RUNTIME — Operating Cycle

Implementation of RUNTIME.md.

Defines when Ledger's layers activate and how work moves through the system.

OWNERSHIP:
- OWNS: layer activation, execution paths, Fast Path rules
- DOES NOT OWN: safety rules, execution behavior, escalation, relationship

PURPOSE:
Ledger operates through selective activation. Some layers are always active,
some are conditional, some are periodic, some are event-driven.

This module prevents unnecessary overhead while preserving safety and alignment.

CORE PRINCIPLE:
Apply the minimum system necessary to produce a correct, aligned result.
Do not run heavy layers by default. Escalate only when stakes, complexity,
or drift justify it.

SOURCE OF TRUTH: ledger/core/RUNTIME.md
If this code contradicts the MD file, the MD file is correct.
"""

from typing import Dict, Any, List, Optional, Callable, Set
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime


class PathType(Enum):
    """Runtime path types."""
    FAST = "fast"           # Low-risk, factual, single-step
    STANDARD = "standard"   # Normal guided work
    STRUCTURED = "structured"  # Multi-step, strategic
    HIGH_RISK = "high_risk"    # Strategic, intervention-aware
    HEARTBEAT = "heartbeat"    # Proactive polling
    IDLE = "idle"           # Relationship learning


class Layer(Enum):
    """System layers that can be activated."""
    # Always active
    CONSTITUTION = "constitution"
    IDENTITY = "identity"
    
    # Conditional
    ALIGNMENT = "alignment"
    GOVERNOR = "governor"
    PLANNER = "planner"
    EXECUTOR = "executor"
    CRITIC = "critic"
    FAILURE = "failure"
    
    # Agents
    AGENTS = "agents"
    
    # Context
    WORLD = "world"
    USER = "user"
    MEMORY = "memory"
    
    # System
    FOCUS = "focus"
    OPPORTUNITY = "opportunity"
    PRUNE = "prune"
    ADAPTATION = "adaptation"
    HEARTBEAT = "heartbeat"
    AUDIT = "audit"
    SELF_MOD = "self_mod"


@dataclass
class RuntimeContext:
    """Context for runtime decisions."""
    task_description: str = ""
    risk_level: str = "low"  # low, medium, high
    estimated_steps: int = 1
    stakes: str = "low"  # low, medium, high
    is_strategic: bool = False
    is_open_ended: bool = False
    is_irreversible: bool = False
    estimated_time_minutes: int = 5
    user_explicit_plan: bool = False
    user_in_loop: bool = False
    personalization_needed: bool = False
    external_action: bool = False
    timestamp: datetime = field(default_factory=datetime.utcnow)
    
    # Query types
    is_factual: bool = False
    is_conversion: bool = False
    is_definition: bool = False
    is_lookup: bool = False
    
    # Mode
    tactical_mode: bool = False
    autonomy_mode: bool = False
    
    # State
    planner_used: bool = False
    steps_completed: int = 0


@dataclass
class RuntimeDecision:
    """Decision about which layers to activate."""
    path: PathType
    active_layers: Set[Layer]
    skip_layers: Set[Layer]
    re_check_interval: Optional[int] = None  # Steps before re-checking GOVERNOR
    requires_critic: bool = False
    requires_approval: bool = False


class Runtime:
    """
    Runtime activation controller.
    
    Determines which layers run based on task characteristics.
    
    Usage:
        runtime = Runtime()
        
        context = RuntimeContext(
            task_description="Deploy production",
            risk_level="high",
            estimated_steps=5,
            stakes="high",
            is_irreversible=True
        )
        
        decision = runtime.decide(context)
        # decision.path = PathType.HIGH_RISK
        # decision.active_layers = {CONSTITUTION, ALIGNMENT, GOVERNOR, ...}
    """
    
    # Authority hierarchy for tie-breaking (higher wins)
    AUTHORITY_ORDER = [
        Layer.CONSTITUTION,  # 0: Highest
        Layer.SELF_MOD,
        Layer.ALIGNMENT,
        Layer.GOVERNOR,
        Layer.IDENTITY,
        Layer.PLANNER,
        Layer.EXECUTOR,
        Layer.CRITIC,
        Layer.FAILURE,
        Layer.ADAPTATION,
        Layer.PRUNE,
        Layer.WORLD,
        Layer.AGENTS,  # Assuming Layer enum has this
        Layer.MEMORY,
    ]
    
    def __init__(self):
        self._layer_instances: Dict[Layer, Any] = {}
        self._activation_hooks: Dict[Layer, List[Callable]] = {}
    
    def register_layer(self, layer: Layer, instance: Any):
        """Register a layer instance for activation."""
        self._layer_instances[layer] = instance
    
    def decide(self, context: RuntimeContext) -> RuntimeDecision:
        """
        Main entry point: decide which path and layers to activate.
        """
        # Determine path type
        path = self._determine_path(context)
        
        # Determine layers based on path
        active_layers = self._get_active_layers(path, context)
        
        # Check if critic needed
        requires_critic = self._requires_critic(context)
        if requires_critic:
            active_layers.add(Layer.CRITIC)
        
        # Check if approval needed
        requires_approval = self._requires_approval(context, path)
        
        # Calculate re-check interval for sustained execution
        re_check_interval = None
        if Layer.EXECUTOR in active_layers and Layer.GOVERNOR in active_layers:
            re_check_interval = 3  # Re-check after 3 steps
        
        # All layers minus active = skip
        all_layers = set(Layer)
        skip_layers = all_layers - active_layers
        
        return RuntimeDecision(
            path=path,
            active_layers=active_layers,
            skip_layers=skip_layers,
            re_check_interval=re_check_interval,
            requires_critic=requires_critic,
            requires_approval=requires_approval
        )
    
    def _determine_path(self, context: RuntimeContext) -> PathType:
        """Determine which runtime path to use."""
        
        # HEARTBEAT path
        if self._is_heartbeat(context):
            return PathType.HEARTBEAT
        
        # FAST path: low-risk, factual, obvious
        if self._qualifies_for_fast_path(context):
            return PathType.FAST
        
        # IDLE path: no active task, relationship learning
        if self._is_idle(context):
            return PathType.IDLE
        
        # HIGH_RISK path: strategic, intervention-aware
        if self._qualifies_for_high_risk_path(context):
            return PathType.HIGH_RISK
        
        # STRUCTURED path: multi-step, planning needed
        if self._qualifies_for_structured_path(context):
            return PathType.STRUCTURED
        
        # Default: STANDARD path
        return PathType.STANDARD
    
    def _is_heartbeat(self, context: RuntimeContext) -> bool:
        """Check if this is a heartbeat check."""
        return context.task_description.startswith("heartbeat:")
    
    def _is_idle(self, context: RuntimeContext) -> bool:
        """Check if system is idle (no active task)."""
        return context.task_description in ["", "idle", "check-in"] or \
               (not context.task_description and context.estimated_steps == 0)
    
    def _qualifies_for_fast_path(self, context: RuntimeContext) -> bool:
        """
        Fast Path criteria (from RUNTIME.md):
        - Low-risk
        - Factual, obvious, or single-step
        - No personalization needed
        - No planning needed
        - No strategic decision
        - No external action
        """
        checks = [
            context.risk_level == "low",
            not context.personalization_needed,
            not context.is_strategic,
            not context.external_action,
            context.estimated_steps <= 1,
            context.stakes == "low",
        ]
        
        # Additional: factual query types
        is_factual_query = any([
            context.is_factual,
            context.is_conversion,
            context.is_definition,
            context.is_lookup
        ])
        
        return all(checks) and is_factual_query
    
    def _qualifies_for_structured_path(self, context: RuntimeContext) -> bool:
        """
        Structured path criteria:
        - Steps > 3
        - Strategic or open-ended
        - Planning required
        """
        return any([
            context.estimated_steps > 3,
            context.is_strategic,
            context.is_open_ended,
            context.user_explicit_plan,
            context.estimated_time_minutes > 30
        ])
    
    def _qualifies_for_high_risk_path(self, context: RuntimeContext) -> bool:
        """
        High-risk path criteria:
        - High stakes
        - Irreversible
        - Strategic with intervention potential
        - Autonomy mode
        """
        return any([
            context.stakes == "high" and context.is_strategic,
            context.is_irreversible,
            context.autonomy_mode,
            context.risk_level == "high" and context.tactical_mode
        ])
    
    def _get_active_layers(self, path: PathType, context: RuntimeContext) -> Set[Layer]:
        """Get set of layers to activate for this path."""
        
        # Always active
        active = {Layer.CONSTITUTION, Layer.IDENTITY}
        
        if path == PathType.FAST:
            # FAST: CONSTITUTION → IDENTITY → EXECUTOR → output
            active.add(Layer.EXECUTOR)
            return active
        
        if path == PathType.IDLE:
            # IDLE: CONSTITUTION → IDENTITY → SOUL → output
            # (SOUL handled by IDENTITY layer)
            return active
        
        if path == PathType.STANDARD:
            # STANDARD: + WORLD/USER/MEMORY + EXECUTOR
            active.update([Layer.WORLD, Layer.USER, Layer.MEMORY, Layer.EXECUTOR])
            return active
        
        if path == PathType.STRUCTURED:
            # STRUCTURED: + FOCUS, OPPORTUNITY, PLANNER, EXECUTOR, CRITIC
            active.update([
                Layer.FOCUS, Layer.OPPORTUNITY, Layer.PLANNER,
                Layer.EXECUTOR, Layer.CRITIC
            ])
            return active
        
        if path == PathType.HIGH_RISK:
            # HIGH_RISK: + ALIGNMENT, GOVERNOR, FOCUS, OPPORTUNITY, PLANNER, EXECUTOR, CRITIC, FAILURE
            active.update([
                Layer.ALIGNMENT, Layer.GOVERNOR, Layer.FOCUS, Layer.OPPORTUNITY,
                Layer.PLANNER, Layer.EXECUTOR, Layer.CRITIC, Layer.FAILURE
            ])
            return active
        
        if path == PathType.HEARTBEAT:
            # HEARTBEAT: + HEARTBEAT, PRUNE (if threshold)
            active.add(Layer.HEARTBEAT)
            if self._prune_threshold_met(context):
                active.add(Layer.PRUNE)
            return active
        
        return active
    
    def _requires_critic(self, context: RuntimeContext) -> bool:
        """
        CRITIC activation criteria (from RUNTIME.md):
        - Output affects decision
        - Tactical mode
        - PLANNER was used
        - User in loop/spiral
        - Stakes: money, reputation, safety, or time > 2 hours
        """
        return any([
            context.tactical_mode,
            context.planner_used,
            context.user_in_loop,
            context.stakes in ["money", "reputation", "safety"],
            context.estimated_time_minutes > 120,
            context.is_strategic and context.stakes == "high"
        ])
    
    def _requires_approval(self, context: RuntimeContext, path: PathType) -> bool:
        """Check if explicit approval is required."""
        return path in [PathType.HIGH_RISK] or context.is_irreversible
    
    def _prune_threshold_met(self, context: RuntimeContext) -> bool:
        """Check if PRUNE threshold is met (placeholder)."""
        # This would check file sizes, context length, etc.
        return False
    
    def should_activate_planner(self, context: RuntimeContext) -> bool:
        """
        PLANNER activation criteria:
        - Steps > 3
        - Scope ambiguous
        - Multiple dependencies
        - Strategic/risk-bearing
        - Irreversible/costly/time > 30 min
        - User explicitly asks
        """
        return any([
            context.estimated_steps > 3,
            context.is_strategic,
            context.is_irreversible,
            context.estimated_time_minutes > 30,
            context.user_explicit_plan,
            context.is_open_ended and not context.is_factual
        ])
    
    def should_activate_alignment(self, context: RuntimeContext) -> bool:
        """
        ALIGNMENT activation criteria:
        - Acting as command layer
        - Long-term vs short-term conflict possible
        - Initiative/autonomy involved
        - Repeated override patterns
        """
        return any([
            context.autonomy_mode,
            context.is_strategic and context.stakes == "high",
            context.external_action and context.stakes == "high"
        ])
    
    def should_activate_governor(self, context: RuntimeContext) -> bool:
        """
        GOVERNOR activation criteria:
        - Repeated harmful patterns
        - Major decisions affecting direction
        - Drift, overload, self-sabotage
        - Command activity without interaction
        """
        return any([
            context.user_in_loop and context.stakes == "high",
            context.is_strategic and context.is_irreversible,
            context.tactical_mode and context.stakes == "high"
        ])
    
    def should_activate_adaptation(self, context: RuntimeContext) -> bool:
        """
        ADAPTATION activation criteria:
        - After repeated evidence (3+ instances)
        - Not from one-off events
        """
        # This would check pattern history
        return False
    
    def resolve_conflict(self, layer_a: Layer, layer_b: Layer) -> Layer:
        """
        Resolve conflict between two layers.
        Higher authority wins per AUTHORITY_ORDER.
        """
        try:
            idx_a = self.AUTHORITY_ORDER.index(layer_a)
            idx_b = self.AUTHORITY_ORDER.index(layer_b)
            return layer_a if idx_a < idx_b else layer_b
        except ValueError:
            # If not in authority list, prefer layer_a
            return layer_a
    
    def execute_with_runtime(self, context: RuntimeContext, 
                            layer_callbacks: Dict[Layer, Callable]) -> Any:
        """
        Execute task with proper layer activation.
        
        This is the main orchestration method.
        """
        decision = self.decide(context)
        
        # Always start with CONSTITUTION
        if Layer.CONSTITUTION in decision.active_layers:
            if Layer.CONSTITUTION in layer_callbacks:
                layer_callbacks[Layer.CONSTITUTION]()
        
        # Then IDENTITY
        if Layer.IDENTITY in decision.active_layers:
            if Layer.IDENTITY in layer_callbacks:
                layer_callbacks[Layer.IDENTITY]()
        
        # Context layers
        for layer in [Layer.WORLD, Layer.USER, Layer.MEMORY]:
            if layer in decision.active_layers and layer in layer_callbacks:
                layer_callbacks[layer]()
        
        # Strategic layers
        for layer in [Layer.FOCUS, Layer.OPPORTUNITY, Layer.ALIGNMENT, Layer.GOVERNOR]:
            if layer in decision.active_layers and layer in layer_callbacks:
                layer_callbacks[layer]()
        
        # Planning
        if Layer.PLANNER in decision.active_layers:
            if Layer.PLANNER in layer_callbacks:
                plan = layer_callbacks[Layer.PLANNER]()
                context.planner_used = True
        
        # Execution
        if Layer.EXECUTOR in decision.active_layers:
            if Layer.EXECUTOR in layer_callbacks:
                result = layer_callbacks[Layer.EXECUTOR]()
                context.steps_completed += 1
                
                # Re-check GOVERNOR after 3 steps
                if decision.re_check_interval and \
                   context.steps_completed % decision.re_check_interval == 0:
                    if Layer.GOVERNOR in layer_callbacks:
                        layer_callbacks[Layer.GOVERNOR]()
        
        # Quality check
        if decision.requires_critic and Layer.CRITIC in layer_callbacks:
            layer_callbacks[Layer.CRITIC]()
        
        return result if 'result' in locals() else None


# Singleton instance
def get_runtime() -> Runtime:
    """Get global Runtime instance."""
    return Runtime()
