"""Orchestrator — High-level goal execution with governance.

The orchestrator sits above the kernel:
1. Takes a goal
2. Plans actions via planner
3. Sends each action through the governance kernel
4. Executes approved actions
5. Reviews results via critic
6. Maintains execution state
7. Cleans up via prune

All agent-runtime components (planner, critic, prune) are injected.
This lets the orchestrator work with either experimental modules
or production stubs.
"""

from typing import Any, Optional, Dict, List
from dataclasses import dataclass, field
from datetime import datetime

from citadel.actions import Action, KernelResult, KernelStatus
from citadel.execution.kernel import Kernel
from citadel.execution.executor import Executor


@dataclass
class OrchestratorState:
    """Mutable state tracking the orchestrator's progress toward a goal."""
    goal: str
    actions: List[Dict[str, Any]] = field(default_factory=list)
    blocks: List[Dict[str, Any]] = field(default_factory=list)
    pending_approvals: List[Dict[str, Any]] = field(default_factory=list)
    completed: bool = False
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class Plan:
    """A plan produced by the planner."""
    actions: List[Action]


class PlannerStub:
    """Minimal planner stub.

    Experimental agent_runtime planner can be injected instead.
    """
    async def plan(self, state: OrchestratorState) -> Plan:
        """Return an empty plan by default. Override for real planning."""
        return Plan(actions=[])


class CriticStub:
    """Minimal critic stub.

    Experimental agent_runtime critic can be injected instead.
    """
    async def review(
        self,
        state: OrchestratorState,
        action: Action,
        result: Any,
        governed: KernelResult,
    ) -> Dict[str, Any]:
        """Return a trivial review by default. Override for real review."""
        return {"passed": True, "notes": "No critic configured"}


class PruneStub:
    """Minimal prune stub.

    Experimental agent_runtime prune can be injected instead.
    """
    async def cleanup(self, state: OrchestratorState) -> None:
        """No-op by default. Override for real cleanup."""
        pass


def init_state(goal: str) -> OrchestratorState:
    """Initialize fresh state for a goal."""
    return OrchestratorState(goal=goal)


def complete(state: OrchestratorState) -> bool:
    """Check if the goal is complete.

    A goal is complete when there are no pending approvals
    and the last planner returned an empty action list.
    """
    return state.completed


def record_block(
    state: OrchestratorState,
    proposed_action: Action,
    governed: KernelResult,
) -> OrchestratorState:
    """Record a blocked action and return updated state."""
    state.blocks.append({
        "action_id": str(proposed_action.action_id),
        "action_name": proposed_action.action_name,
        "status": governed.decision.status.value,
        "reason": governed.decision.reason,
        "timestamp": datetime.utcnow().isoformat(),
    })
    state.updated_at = datetime.utcnow()
    return state


def record_pending_approval(
    state: OrchestratorState,
    proposed_action: Action,
    governed: KernelResult,
) -> OrchestratorState:
    """Record an action waiting for approval and return updated state."""
    state.pending_approvals.append({
        "action_id": str(proposed_action.action_id),
        "action_name": proposed_action.action_name,
        "status": governed.decision.status.value,
        "reason": governed.decision.reason,
        "timestamp": datetime.utcnow().isoformat(),
    })
    state.updated_at = datetime.utcnow()
    return state


def update_state(
    state: OrchestratorState,
    proposed_action: Action,
    result: Any,
    review: Dict[str, Any],
    governed: KernelResult,
) -> OrchestratorState:
    """Record a successfully executed action and return updated state."""
    state.actions.append({
        "action_id": str(proposed_action.action_id),
        "action_name": proposed_action.action_name,
        "result": result,
        "review": review,
        "status": governed.decision.status.value,
        "timestamp": datetime.utcnow().isoformat(),
    })
    state.updated_at = datetime.utcnow()
    return state


class Orchestrator:
    """High-level goal runner with full governance pipeline.

    Usage:
        orch = Orchestrator(kernel=my_kernel, executor=my_executor)
        final_state = await orch.run("Process all pending invoices")
    """

    def __init__(
        self,
        kernel: Kernel,
        executor: Executor,
        planner: Optional[Any] = None,
        critic: Optional[Any] = None,
        prune: Optional[Any] = None,
    ):
        self.kernel = kernel
        self.executor = executor
        self.planner = planner or PlannerStub()
        self.critic = critic or CriticStub()
        self.prune = prune or PruneStub()

    async def run(self, goal: str) -> OrchestratorState:
        """Execute a goal through the full governance pipeline.

        Steps:
        1. Init state
        2. While not complete:
           a. Plan next actions
           b. For each proposed action:
              i.  Run through kernel (governance)
              ii. If blocked → record and continue
              iii. If approval required → record and continue
              iv. Execute via executor
              v.  Review via critic
              vi. Update state
           c. Prune / cleanup
        3. Return final state
        """
        state = init_state(goal)

        while not complete(state):
            plan = await self.planner.plan(state)

            if not plan.actions:
                # Planner returned nothing — mark complete
                state.completed = True
                break

            for proposed_action in plan.actions:
                governed = await self.kernel.handle(proposed_action)

                if governed.decision.status in (
                    KernelStatus.BLOCKED_SCHEMA,
                    KernelStatus.BLOCKED_EMERGENCY,
                    KernelStatus.BLOCKED_CAPABILITY,
                    KernelStatus.BLOCKED_POLICY,
                    KernelStatus.RATE_LIMITED,
                ):
                    state = record_block(state, proposed_action, governed)
                    continue

                if governed.decision.status == KernelStatus.PENDING_APPROVAL:
                    state = record_pending_approval(state, proposed_action, governed)
                    continue

                # Execute the governed action
                result = await self.executor.execute(governed.action)

                # Review the outcome
                review = await self.critic.review(
                    state, proposed_action, result, governed
                )

                state = update_state(state, proposed_action, result, review, governed)

            await self.prune.cleanup(state)

        return state
