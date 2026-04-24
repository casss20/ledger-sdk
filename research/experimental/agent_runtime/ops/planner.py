"""PLANNER â€” Planning & Architecture

Implementation of PLANNER.md.

OWNERSHIP:
- OWNS: structured planning, breaking work, architecture decisions, sequencing
- DOES NOT OWN: execution, real-time correction, relationship philosophy

PURPOSE:
PLANNER creates structure before EXECUTOR begins.
- Analyzes tasks before action
- Defines scope, milestones, and dependencies
- Provides a clear plan for EXECUTOR to follow
- CRITIC reviews the plan if stakes are high

SOURCE OF TRUTH: CITADEL/ops/PLANNER.md
If this code contradicts the MD file, the MD file is correct.
"""

from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime
import uuid


class PlanType(Enum):
    """Types of plans per PLANNER.md."""
    QUICK = "quick"       # Steps <= 3, verbal outline
    STANDARD = "standard"  # Steps 4-7, written outline
    DEEP = "deep"         # Steps > 7, high stakes, full document


class PlanStatus(Enum):
    """Plan lifecycle status."""
    DRAFT = "draft"
    PENDING_REVIEW = "pending_review"
    APPROVED = "approved"
    REJECTED = "rejected"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    ABORTED = "aborted"


@dataclass
class Milestone:
    """A checkpoint state in the plan."""
    id: str
    name: str
    description: str
    dependencies: List[str] = field(default_factory=list)
    deliverables: List[str] = field(default_factory=list)
    estimated_minutes: int = 10
    completed: bool = False
    completed_at: Optional[datetime] = None


@dataclass
class Risk:
    """A risk that could derail the plan."""
    id: str
    description: str
    likelihood: str  # low, medium, high
    impact: str      # low, medium, high
    mitigation: str
    owner: str = "executor"


@dataclass
class RollbackStep:
    """A step to undo work if needed."""
    id: str
    description: str
    trigger_condition: str
    action: str


@dataclass
class Plan:
    """
    A complete plan per PLANNER.md structure.
    
    Every plan defines:
    1. Goal â€” what success looks like
    2. Scope â€” what's in, what's out
    3. Milestones â€” 3-7 checkpoint states
    4. Dependencies â€” what must exist before each step
    5. Risks â€” what could go wrong
    6. Rollback â€” how to undo if needed
    """
    id: str
    goal: str
    scope_in: List[str]
    scope_out: List[str]
    milestones: List[Milestone]
    risks: List[Risk]
    rollback: List[RollbackStep]
    plan_type: PlanType
    status: PlanStatus = PlanStatus.DRAFT
    created_at: datetime = field(default_factory=datetime.utcnow)
    approved_at: Optional[datetime] = None
    requires_critic_review: bool = False
    critic_approved: Optional[bool] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def estimated_total_minutes(self) -> int:
        """Total estimated time for all milestones."""
        return sum(m.estimated_minutes for m in self.milestones)
    
    @property
    def completion_percentage(self) -> float:
        """Percentage of milestones completed."""
        if not self.milestones:
            return 0.0
        completed = sum(1 for m in self.milestones if m.completed)
        return (completed / len(self.milestones)) * 100
    
    def get_current_milestone(self) -> Optional[Milestone]:
        """Get the first uncompleted milestone."""
        for m in self.milestones:
            if not m.completed:
                return m
        return None
    
    def complete_milestone(self, milestone_id: str) -> bool:
        """Mark a milestone as completed."""
        for m in self.milestones:
            if m.id == milestone_id:
                m.completed = True
                m.completed_at = datetime.utcnow()
                return True
        return False
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize plan to dict."""
        return {
            "id": self.id,
            "goal": self.goal,
            "plan_type": self.plan_type.value,
            "status": self.status.value,
            "scope": {
                "in": self.scope_in,
                "out": self.scope_out
            },
            "milestones": [
                {
                    "id": m.id,
                    "name": m.name,
                    "completed": m.completed,
                    "estimated_minutes": m.estimated_minutes
                }
                for m in self.milestones
            ],
            "risks": [
                {
                    "id": r.id,
                    "description": r.description,
                    "likelihood": r.likelihood,
                    "impact": r.impact
                }
                for r in self.risks
            ],
            "estimated_total_minutes": self.estimated_total_minutes,
            "completion_percentage": self.completion_percentage,
            "requires_critic_review": self.requires_critic_review
        }


@dataclass
class PlanningContext:
    """Context for planning decisions."""
    task_description: str
    estimated_steps: int = 1
    stakes: str = "low"  # low, medium, high
    is_strategic: bool = False
    is_open_ended: bool = False
    is_irreversible: bool = False
    estimated_time_minutes: int = 5
    user_explicit_plan: bool = False
    dependencies: List[str] = field(default_factory=list)
    constraints: List[str] = field(default_factory=list)


class Planner:
    """
    PLANNER implementation.
    
    Creates structured plans before EXECUTOR begins.
    
    Usage:
        planner = Planner()
        
        context = PlanningContext(
            task_description="Deploy production database migration",
            estimated_steps=5,
            stakes="high",
            is_irreversible=True
        )
        
        plan = planner.create_plan(context)
        
        if plan.requires_critic_review:
            # Send to CRITIC
            pass
        
        if plan.plan_type == PlanType.DEEP:
            # Require user approval
            pass
    """
    
    def __init__(self):
        self._plans: Dict[str, Plan] = {}
        self._plan_hooks: Dict[str, Callable] = {}
        self._critic_hook: Optional[Callable[[Plan], bool]] = None
    
    def register_critic_hook(self, hook: Callable[[Plan], bool]):
        """Register CRITIC review hook. Returns True if plan approved."""
        self._critic_hook = hook
    
    def should_plan(self, context: PlanningContext) -> bool:
        """
        Determine if planning is required.
        
        Plan if ANY apply:
        - estimated steps > 3
        - scope remains ambiguous
        - multiple dependencies or systems
        - strategic, open-ended, or risk-bearing
        - irreversible, costly, or time > 30 minutes
        - user explicitly asks for a plan
        """
        return any([
            context.estimated_steps > 3,
            context.is_strategic,
            context.is_open_ended,
            context.is_irreversible,
            context.estimated_time_minutes > 30,
            context.user_explicit_plan,
            len(context.dependencies) > 2,
            context.stakes in ["high", "money", "reputation", "safety"]
        ])
    
    def determine_plan_type(self, context: PlanningContext) -> PlanType:
        """Determine what type of plan to create."""
        if context.estimated_steps <= 3:
            return PlanType.QUICK
        elif context.estimated_steps <= 7 and context.stakes != "high":
            return PlanType.STANDARD
        else:
            return PlanType.DEEP
    
    def create_plan(self, context: PlanningContext) -> Plan:
        """
        Create a plan from context.
        
        In production, this would use an LLM to generate the plan.
        Here we provide the structure and validation.
        """
        plan_type = self.determine_plan_type(context)
        plan_id = str(uuid.uuid4())[:8]
        
        # Generate structure based on plan type
        if plan_type == PlanType.QUICK:
            milestones = self._generate_quick_milestones(context)
            risks = []
            rollback = []
        elif plan_type == PlanType.STANDARD:
            milestones = self._generate_standard_milestones(context)
            risks = self._generate_risks(context)
            rollback = self._generate_rollback(context)
        else:  # DEEP
            milestones = self._generate_deep_milestones(context)
            risks = self._generate_risks(context)
            rollback = self._generate_rollback(context)
        
        plan = Plan(
            id=plan_id,
            goal=context.task_description,
            scope_in=self._define_scope_in(context),
            scope_out=self._define_scope_out(context),
            milestones=milestones,
            risks=risks,
            rollback=rollback,
            plan_type=plan_type,
            requires_critic_review=(plan_type == PlanType.DEEP or context.stakes == "high")
        )
        
        self._plans[plan_id] = plan
        
        # CRITIC review for high-stakes plans
        if plan.requires_critic_review and self._critic_hook:
            approved = self._critic_hook(plan)
            plan.critic_approved = approved
            plan.status = PlanStatus.APPROVED if approved else PlanStatus.REJECTED
        else:
            plan.status = PlanStatus.APPROVED
        
        return plan
    
    def _generate_quick_milestones(self, context: PlanningContext) -> List[Milestone]:
        """Generate 2-3 milestones for quick plans."""
        return [
            Milestone(
                id="m1",
                name="Understand",
                description="Clarify requirements and constraints",
                estimated_minutes=5
            ),
            Milestone(
                id="m2",
                name="Execute",
                description="Complete the task",
                dependencies=["m1"],
                estimated_minutes=context.estimated_time_minutes - 5
            )
        ]
    
    def _generate_standard_milestones(self, context: PlanningContext) -> List[Milestone]:
        """Generate 4-7 milestones for standard plans."""
        steps = min(context.estimated_steps, 7)
        milestones = []
        
        for i in range(steps):
            deps = [f"m{j}" for j in range(1, i + 1)] if i > 0 else []
            milestones.append(Milestone(
                id=f"m{i+1}",
                name=f"Step {i+1}",
                description=f"Complete step {i+1} of {steps}",
                dependencies=deps,
                estimated_minutes=context.estimated_time_minutes // steps
            ))
        
        return milestones
    
    def _generate_deep_milestones(self, context: PlanningContext) -> List[Milestone]:
        """Generate detailed milestones for deep plans."""
        # Deep plans have more structure
        base = self._generate_standard_milestones(context)
        
        # Add verification milestone
        base.append(Milestone(
            id="verify",
            name="Verify & Validate",
            description="Verify all steps completed correctly",
            dependencies=[f"m{len(base)}"],
            estimated_minutes=10
        ))
        
        return base
    
    def _generate_risks(self, context: PlanningContext) -> List[Risk]:
        """Generate risks based on context."""
        risks = []
        
        if context.is_irreversible:
            risks.append(Risk(
                id="r1",
                description="Action cannot be undone",
                likelihood="certain",
                impact="high",
                mitigation="Triple-check before proceeding; have rollback plan"
            ))
        
        if context.stakes == "high":
            risks.append(Risk(
                id="r2",
                description="High-stakes failure has significant consequences",
                likelihood="low",
                impact="high",
                mitigation="Break into smaller reversible steps; test in staging"
            ))
        
        if len(context.dependencies) > 2:
            risks.append(Risk(
                id="r3",
                description="Multiple dependencies increase failure points",
                likelihood="medium",
                impact="medium",
                mitigation="Verify each dependency before proceeding"
            ))
        
        return risks
    
    def _generate_rollback(self, context: PlanningContext) -> List[RollbackStep]:
        """Generate rollback steps."""
        if not context.is_irreversible:
            return []
        
        return [
            RollbackStep(
                id="rb1",
                description="Stop execution immediately",
                trigger_condition="Error detected or plan invalidated",
                action="Halt all operations, preserve state"
            ),
            RollbackStep(
                id="rb2",
                description="Revert changes",
                trigger_condition="Execution stopped",
                action="Apply rollback procedures for completed steps"
            )
        ]
    
    def _define_scope_in(self, context: PlanningContext) -> List[str]:
        """Define what's in scope."""
        scope = [context.task_description]
        if context.dependencies:
            scope.append(f"Dependencies: {', '.join(context.dependencies)}")
        return scope
    
    def _define_scope_out(self, context: PlanningContext) -> List[str]:
        """Define what's out of scope."""
        return [
            "Tasks not explicitly stated",
            "Scope expansion without approval",
            "Unrelated systems or components"
        ]
    
    def get_plan(self, plan_id: str) -> Optional[Plan]:
        """Retrieve a plan by ID."""
        return self._plans.get(plan_id)
    
    def approve_plan(self, plan_id: str) -> bool:
        """Mark a plan as approved."""
        plan = self._plans.get(plan_id)
        if plan and plan.status == PlanStatus.DRAFT:
            plan.status = PlanStatus.APPROVED
            plan.approved_at = datetime.utcnow()
            return True
        return False
    
    def reject_plan(self, plan_id: str, reason: str) -> bool:
        """Reject a plan."""
        plan = self._plans.get(plan_id)
        if plan:
            plan.status = PlanStatus.REJECTED
            plan.metadata["rejection_reason"] = reason
            return True
        return False
    
    def start_execution(self, plan_id: str) -> bool:
        """Mark plan as in progress."""
        plan = self._plans.get(plan_id)
        if plan and plan.status == PlanStatus.APPROVED:
            plan.status = PlanStatus.IN_PROGRESS
            return True
        return False
    
    def complete_plan(self, plan_id: str) -> bool:
        """Mark plan as completed."""
        plan = self._plans.get(plan_id)
        if plan and plan.status == PlanStatus.IN_PROGRESS:
            plan.status = PlanStatus.COMPLETED
            return True
        return False
    
    def abort_plan(self, plan_id: str, reason: str) -> bool:
        """Abort plan execution."""
        plan = self._plans.get(plan_id)
        if plan and plan.status in [PlanStatus.IN_PROGRESS, PlanStatus.APPROVED]:
            plan.status = PlanStatus.ABORTED
            plan.metadata["abort_reason"] = reason
            return True
        return False
    
    def handoff_to_executor(self, plan: Plan) -> Dict[str, Any]:
        """
        Create handoff package for EXECUTOR.
        
        PLANNER â†’ EXECUTOR:
        - approved plan
        - scope boundaries
        - known risks
        - rollback path
        """
        return {
            "plan_id": plan.id,
            "goal": plan.goal,
            "milestones": [m for m in plan.milestones],
            "scope_in": plan.scope_in,
            "scope_out": plan.scope_out,
            "risks": plan.risks,
            "rollback": plan.rollback,
            "instructions": {
                "follow_the_plan": True,
                "flag_scope_changes": True,
                "no_silent_replan": True
            }
        }
    
    def handle_planning_failure(self, context: PlanningContext) -> Dict[str, Any]:
        """
        Handle planning failure per FAILURE.md.
        
        Options:
        1. Reduce scope
        2. Gather more information
        3. Escalate to FAILURE.md
        """
        return {
            "failure": "planning",
            "recommendations": [
                "Reduce scope to core essentials",
                "Gather more information about dependencies",
                "Escalate to FAILURE layer for handling"
            ],
            "reduced_scope_context": PlanningContext(
                task_description=f"[REDUCED] {context.task_description}",
                estimated_steps=max(1, context.estimated_steps // 2),
                stakes=context.stakes,
                is_strategic=context.is_strategic
            )
        }


# Singleton instance
def get_planner() -> Planner:
    """Get global Planner instance."""
    return Planner()
