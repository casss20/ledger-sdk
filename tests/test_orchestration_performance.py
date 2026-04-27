"""
Performance benchmarks for Citadel orchestration.

Measures latency and throughput for:
- baseline execution (kernel.handle)
- delegation
- handoff
- gather (parallel branches)
- introspection
- token verification
- kill-switch checks
- concurrent workloads

Uses in-memory mocks with realistic simulated DB latency (~2ms per round-trip).
"""

import asyncio
import statistics
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any, List
from unittest.mock import AsyncMock, MagicMock

import pytest

from citadel.execution.orchestration import (
    OrchestrationRuntime,
    DelegationResult,
    HandoffResult,
    GatherResult,
    IntrospectionStatus,
)
from citadel.execution.kernel import Kernel
from citadel.actions import Action, Decision, KernelStatus, KernelResult
from citadel.tokens.governance_decision import (
    GovernanceDecision,
    DecisionType,
    DecisionScope,
    KillSwitchScope,
)
from citadel.tokens.governance_token import CapabilityToken
from citadel.tokens.kill_switch import KillSwitch
from citadel.tokens.token_verifier import TokenVerifier
from citadel.tokens.token_vault import TokenVault


# ──────────────────────────────────────────────────────────────────────────────
# Simulated DB latency helper
# ──────────────────────────────────────────────────────────────────────────────

SIMULATED_DB_LATENCY_MS = 2.0  # ~2ms per DB round-trip (local PostgreSQL)


async def _simulate_db_latency():
    """Simulate realistic DB round-trip latency."""
    await asyncio.sleep(SIMULATED_DB_LATENCY_MS / 1000.0)


# ──────────────────────────────────────────────────────────────────────────────
# Fast mocks with realistic latency
# ──────────────────────────────────────────────────────────────────────────────

class FastMockRepository:
    """Repository with simulated DB latency."""

    def __init__(self):
        self._actions: Dict[str, Any] = {}
        self._decisions: Dict[str, Any] = {}
        self._results: Dict[str, Any] = {}
        self._capabilities: Dict[str, Any] = {}

    async def save_action(self, action: Action) -> bool:
        await _simulate_db_latency()
        key = str(action.action_id)
        if key in self._actions:
            return False
        self._actions[key] = action
        return True

    async def save_decision(self, decision: Decision) -> None:
        await _simulate_db_latency()
        self._decisions[str(decision.decision_id)] = decision

    async def find_decision_by_idempotency(self, actor_id: str, key: str, tenant_id: str = None):
        await _simulate_db_latency()
        return None

    async def save_execution_result(self, action_id, success, result, error=None, tenant_id=None):
        await _simulate_db_latency()
        self._results[str(action_id)] = {"success": success, "result": result, "error": error}

    async def get_capability(self, token: str):
        await _simulate_db_latency()
        return self._capabilities.get(token)

    async def consume_capability(self, token: str, actor_id: str):
        await _simulate_db_latency()
        return {"success": True, "remaining_uses": 1}

    async def check_kill_switch(self, scope_type: str, scope_value: str, tenant_id: str):
        await _simulate_db_latency()
        return None


class FastMockPolicyResolver:
    async def resolve(self, action: Action):
        await _simulate_db_latency()
        snapshot = MagicMock()
        snapshot.snapshot_id = "snap_123"
        return snapshot


class FastMockPolicyEvaluator:
    def evaluate(self, snapshot, action, context):
        result = MagicMock()
        result.effect = "ALLOW"
        result.rule_name = "default_allow"
        result.reason = "Allowed by default policy"
        result.risk_level = "low"
        result.risk_score = 10
        result.requires_approval = False
        return result


class FastMockApprovalService:
    async def check_required(self, action, snapshot):
        result = MagicMock()
        result.required = False
        result.reason = ""
        result.risk_level = "low"
        return result

    async def create_pending(self, action, check):
        return "approval_123"


class FastMockExecutor:
    async def run(self, action: Action):
        await _simulate_db_latency()
        return {"status": "ok", "data": "executed"}


class FastMockAuditService:
    """Audit service that simulates DB write latency."""

    def __init__(self):
        self.events: List[Dict] = []

    async def action_received(self, action):
        await _simulate_db_latency()
        self.events.append({"type": "action_received", "action_id": str(action.action_id)})

    async def action_executed(self, action, result):
        await _simulate_db_latency()
        self.events.append({"type": "action_executed", "action_id": str(action.action_id)})

    async def action_failed(self, action, error):
        await _simulate_db_latency()
        self.events.append({"type": "action_failed", "action_id": str(action.action_id)})

    async def decision_made(self, action, decision):
        await _simulate_db_latency()
        self.events.append({"type": "decision_made", "decision_id": str(decision.decision_id)})

    async def policy_evaluated(self, action, snapshot):
        await _simulate_db_latency()
        self.events.append({"type": "policy_evaluated"})

    async def idempotent_return(self, action, decision):
        await _simulate_db_latency()
        self.events.append({"type": "idempotent_return"})

    async def approval_requested(self, action, approval_id):
        await _simulate_db_latency()
        self.events.append({"type": "approval_requested"})

    async def record(self, **kwargs):
        await _simulate_db_latency()
        self.events.append({"type": kwargs.get("event_type", "generic"), **kwargs})


class FastMockVault:
    """Token vault with simulated DB latency."""

    def __init__(self):
        self._decisions: Dict[str, Dict] = {}
        self._tokens: Dict[str, Dict] = {}

    async def store_decision(self, decision) -> None:
        await _simulate_db_latency()
        self._decisions[decision.decision_id] = _gov_decision_to_dict(decision)

    async def store_token(self, token) -> None:
        await _simulate_db_latency()
        self._tokens[token.token_id] = {
            "token_id": token.token_id,
            "decision_id": token.decision_id,
            "tenant_id": token.tenant_id,
            "actor_id": token.actor_id,
            "workspace_id": token.workspace_id or token.tenant_id,
            "action": token.action,
            "resource_scope": token.resource_scope,
            "scope_actions": token.scope_actions,
            "scope_resources": token.scope_resources,
            "expiry": token.expiry,
            "not_before": token.not_before,
            "trace_id": token.trace_id,
            "parent_decision_id": token.parent_decision_id,
            "parent_actor_id": token.parent_actor_id,
            "workflow_id": token.workflow_id,
            "tool": token.tool,
            "revoked_at": None,
            "revoked_reason": None,
        }

    async def resolve_decision(self, decision_id: str, tenant_id: str = None) -> Optional[Dict]:
        await _simulate_db_latency()
        return self._decisions.get(decision_id)

    async def resolve_token(self, token_id: str, tenant_id: str = None) -> Optional[Dict]:
        await _simulate_db_latency()
        return self._tokens.get(token_id)

    async def issue_token_for_decision(self, decision, **kwargs):
        await self.store_decision(decision)
        token = CapabilityToken.derive(decision, **kwargs)
        await self.store_token(token)
        return token

    async def check_kill_switch(self, **kwargs):
        await _simulate_db_latency()
        return None

    async def check_ancestry(self, decision):
        await _simulate_db_latency()
        return (True, None)

    async def revoke_decision(self, decision_id, tenant_id=None, reason=None):
        await _simulate_db_latency()
        d = self._decisions.get(decision_id)
        if d:
            d["revoked_at"] = datetime.now(timezone.utc).isoformat()
            d["revoked_reason"] = reason
        return True


def _gov_decision_to_dict(gd: GovernanceDecision) -> Dict:
    return {
        "decision_id": gd.decision_id,
        "decision_type": gd.decision_type.value,
        "tenant_id": gd.tenant_id,
        "actor_id": gd.actor_id,
        "action": gd.action,
        "resource": gd.resource,
        "request_id": gd.request_id,
        "trace_id": gd.trace_id,
        "workspace_id": gd.workspace_id or gd.tenant_id,
        "agent_id": gd.agent_id or gd.actor_id,
        "subject_type": gd.subject_type,
        "subject_id": gd.subject_id or gd.actor_id,
        "risk_level": gd.risk_level,
        "policy_version": gd.policy_version,
        "approval_state": gd.approval_state,
        "approved_by": gd.approved_by,
        "approved_at": gd.approved_at,
        "scope_actions": gd.scope.actions,
        "scope_resources": gd.scope.resources,
        "scope_max_spend": gd.scope.max_spend,
        "scope_rate_limit": gd.scope.rate_limit,
        "constraints": gd.constraints,
        "expiry": gd.expiry,
        "kill_switch_scope": gd.kill_switch_scope.value,
        "created_at": gd.created_at,
        "issued_token_id": gd.issued_token_id,
        "revoked_at": gd.revoked_at,
        "revoked_reason": gd.revoked_reason,
        "reason": gd.reason,
        "root_decision_id": gd.root_decision_id,
        "parent_decision_id": gd.parent_decision_id,
        "parent_actor_id": gd.parent_actor_id,
        "workflow_id": gd.workflow_id,
        "superseded_at": gd.superseded_at,
        "superseded_reason": gd.superseded_reason,
    }


def _make_governance_decision(
    decision_id: str = None,
    actor_id: str = "test_actor",
    tenant_id: str = "test_tenant",
    action: str = "test.action",
    resource: str = "test:resource",
    scope: DecisionScope = None,
    expiry_hours: int = 1,
    parent_decision_id: str = None,
    root_decision_id: str = None,
    trace_id: str = None,
    workflow_id: str = None,
    parent_actor_id: str = None,
    decision_type: DecisionType = DecisionType.ALLOW,
) -> GovernanceDecision:
    now = datetime.now(timezone.utc)
    return GovernanceDecision(
        decision_id=decision_id or f"gd_{asyncio.current_task().get_name() if asyncio.current_task() else 'test'}_{id(object())}",
        decision_type=decision_type,
        tenant_id=tenant_id,
        actor_id=actor_id,
        action=action,
        resource=resource,
        scope=scope or DecisionScope(actions=[action], resources=[resource]),
        expiry=now + timedelta(hours=expiry_hours),
        created_at=now,
        parent_decision_id=parent_decision_id,
        root_decision_id=root_decision_id,
        trace_id=trace_id,
        workflow_id=workflow_id,
        parent_actor_id=parent_actor_id,
    )


# ──────────────────────────────────────────────────────────────────────────────
# Benchmark harness
# ──────────────────────────────────────────────────────────────────────────────

@dataclass
class BenchmarkResult:
    name: str
    iterations: int
    total_ms: float
    avg_ms: float
    p50_ms: float
    p95_ms: float
    p99_ms: float
    min_ms: float
    max_ms: float
    ops_per_sec: float


def _percentile(sorted_times: List[float], p: float) -> float:
    idx = int(len(sorted_times) * p / 100.0)
    return sorted_times[min(idx, len(sorted_times) - 1)]


async def benchmark(name: str, fn, iterations: int = 100, warmup: int = 10) -> BenchmarkResult:
    """Run a benchmark with warmup."""
    # Warmup
    for _ in range(warmup):
        await fn()

    times = []
    for _ in range(iterations):
        start = time.perf_counter()
        await fn()
        elapsed = (time.perf_counter() - start) * 1000.0
        times.append(elapsed)

    times.sort()
    total = sum(times)
    return BenchmarkResult(
        name=name,
        iterations=iterations,
        total_ms=total,
        avg_ms=total / iterations,
        p50_ms=_percentile(times, 50),
        p95_ms=_percentile(times, 95),
        p99_ms=_percentile(times, 99),
        min_ms=times[0],
        max_ms=times[-1],
        ops_per_sec=iterations / (total / 1000.0),
    )


def print_result(r: BenchmarkResult):
    print(f"\n{'='*60}")
    print(f"Benchmark: {r.name}")
    print(f"  Iterations: {r.iterations}")
    print(f"  Total:      {r.total_ms:8.2f} ms")
    print(f"  Avg:        {r.avg_ms:8.2f} ms")
    print(f"  Min:        {r.min_ms:8.2f} ms")
    print(f"  p50:        {r.p50_ms:8.2f} ms")
    print(f"  p95:        {r.p95_ms:8.2f} ms")
    print(f"  p99:        {r.p99_ms:8.2f} ms")
    print(f"  Max:        {r.max_ms:8.2f} ms")
    print(f"  Throughput: {r.ops_per_sec:8.2f} ops/sec")


# ──────────────────────────────────────────────────────────────────────────────
# Fixtures
# ──────────────────────────────────────────────────────────────────────────────

@pytest.fixture
def fast_repo():
    return FastMockRepository()


@pytest.fixture
def fast_audit():
    return FastMockAuditService()


@pytest.fixture
def fast_vault():
    return FastMockVault()


@pytest.fixture
def fast_kernel(fast_repo, fast_audit):
    policy = FastMockPolicyResolver()
    precedence = MagicMock()
    precedence.evaluate = AsyncMock(return_value=MagicMock(
        blocked=False, status=None, winning_rule="allowed",
        reason="All checks passed", path_taken="fast", risk_level="low", risk_score=0
    ))
    return Kernel(
        repository=fast_repo,
        policy_resolver=policy,
        precedence=precedence,
        approval_service=FastMockApprovalService(),
        capability_service=MagicMock(),
        audit_service=fast_audit,
        executor=FastMockExecutor(),
    )


@pytest.fixture
def fast_runtime(fast_kernel, fast_vault, fast_audit, fast_repo):
    kill_switch = KillSwitch(audit_logger=fast_audit)
    verifier = TokenVerifier(vault=fast_vault, kill_switch=kill_switch, audit_logger=fast_audit)
    return OrchestrationRuntime(
        kernel=fast_kernel,
        token_vault=fast_vault,
        token_verifier=verifier,
        repository=fast_repo,
        audit_service=fast_audit,
        kill_switch=kill_switch,
    )


# ──────────────────────────────────────────────────────────────────────────────
# Benchmarks
# ──────────────────────────────────────────────────────────────────────────────

@pytest.mark.benchmark
class TestPerformanceBaseline:
    """Baseline: kernel.handle() without orchestration extras."""

    @pytest.mark.asyncio
    async def test_baseline_execute_latency(self, fast_kernel):
        """Measure plain kernel.handle() latency."""
        action = Action(
            action_id="act_baseline",
            actor_id="actor_1",
            actor_type="agent",
            action_name="test.action",
            resource="test:resource",
            tenant_id="test_tenant",
            payload={},
            context={},
            session_id=None,
            request_id=None,
            idempotency_key=None,
            created_at=datetime.now(timezone.utc),
        )

        async def _run():
            await fast_kernel.handle(action)

        result = await benchmark("baseline_execute", _run, iterations=50, warmup=5)
        print_result(result)
        assert result.avg_ms < 50, f"Baseline too slow: {result.avg_ms:.2f}ms"


@pytest.mark.benchmark
class TestPerformanceDelegation:
    """Delegation overhead."""

    @pytest.mark.asyncio
    async def test_delegate_single_child_latency(self, fast_runtime, fast_vault):
        """Measure cg.delegate() latency."""
        parent = _make_governance_decision(
            decision_id="gd_parent_1",
            actor_id="parent_actor",
            scope=DecisionScope(
                actions=["test.action", "child.action"],
                resources=["test:resource", "child:resource"],
            ),
        )
        await fast_vault.store_decision(parent)

        async def _run():
            await fast_runtime.delegate(
                parent_decision=parent,
                child_actor_id="child_actor",
                action_name="child.action",
                resource="child:resource",
                scope=DecisionScope(
                    actions=["child.action"],
                    resources=["child:resource"],
                ),
            )

        result = await benchmark("delegate_single_child", _run, iterations=50, warmup=5)
        print_result(result)
        assert result.avg_ms < 80, f"Delegate too slow: {result.avg_ms:.2f}ms"

    @pytest.mark.asyncio
    async def test_delegate_vs_baseline_overhead(self, fast_kernel, fast_runtime, fast_vault):
        """Compare delegation to baseline execution."""
        action = Action(
            action_id="act_baseline",
            actor_id="actor_1",
            actor_type="agent",
            action_name="test.action",
            resource="test:resource",
            tenant_id="test_tenant",
            payload={},
            context={},
            session_id=None,
            request_id=None,
            idempotency_key=None,
            created_at=datetime.now(timezone.utc),
        )

        parent = _make_governance_decision(
            decision_id="gd_parent_2",
            actor_id="parent_actor",
            scope=DecisionScope(
                actions=["test.action", "child.action"],
                resources=["test:resource", "child:resource"],
            ),
        )
        await fast_vault.store_decision(parent)

        async def _baseline():
            await fast_kernel.handle(action)

        async def _delegate():
            await fast_runtime.delegate(
                parent_decision=parent,
                child_actor_id="child_actor",
                action_name="child.action",
                resource="child:resource",
                scope=DecisionScope(
                    actions=["child.action"],
                    resources=["child:resource"],
                ),
            )

        baseline = await benchmark("baseline_for_comparison", _baseline, iterations=30, warmup=5)
        delegate = await benchmark("delegate_for_comparison", _delegate, iterations=30, warmup=5)

        print_result(baseline)
        print_result(delegate)

        overhead_ms = delegate.avg_ms - baseline.avg_ms
        overhead_pct = (overhead_ms / baseline.avg_ms) * 100 if baseline.avg_ms > 0 else 0
        print(f"\n  Delegation overhead: {overhead_ms:.2f}ms ({overhead_pct:.1f}%)")

        assert overhead_ms < 40, f"Delegation overhead too high: {overhead_ms:.2f}ms"


@pytest.mark.benchmark
class TestPerformanceHandoff:
    """Handoff overhead."""

    @pytest.mark.asyncio
    async def test_handoff_latency(self, fast_runtime, fast_vault):
        """Measure cg.handoff() latency."""
        current = _make_governance_decision(
            decision_id="gd_handoff_current",
            actor_id="old_actor",
            scope=DecisionScope(
                actions=["test.action", "new.action"],
                resources=["test:resource", "new:resource"],
            ),
        )
        await fast_vault.store_decision(current)

        async def _run():
            await fast_runtime.handoff(
                current_decision=current,
                new_actor_id="new_actor",
                action_name="new.action",
                resource="new:resource",
                scope=DecisionScope(
                    actions=["new.action"],
                    resources=["new:resource"],
                ),
            )

        result = await benchmark("handoff", _run, iterations=50, warmup=5)
        print_result(result)
        assert result.avg_ms < 80, f"Handoff too slow: {result.avg_ms:.2f}ms"


@pytest.mark.benchmark
class TestPerformanceGather:
    """Parallel branch performance."""

    @pytest.mark.asyncio
    async def test_gather_2_branches_latency(self, fast_runtime, fast_vault):
        """Measure cg.gather() with 2 branches."""
        parent = _make_governance_decision(
            decision_id="gd_gather_parent",
            actor_id="parent_actor",
            scope=DecisionScope(
                actions=["test.action", "branch.action"],
                resources=["test:resource", "branch:resource"],
            ),
        )
        await fast_vault.store_decision(parent)

        branches = [
            {"actor_id": "branch_a", "action": "branch.action", "resource": "branch:resource"},
            {"actor_id": "branch_b", "action": "branch.action", "resource": "branch:resource"},
        ]

        async def _run():
            await fast_runtime.gather(
                parent_decision=parent,
                branches=branches,
            )

        result = await benchmark("gather_2_branches", _run, iterations=30, warmup=5)
        print_result(result)
        assert result.avg_ms < 120, f"Gather too slow: {result.avg_ms:.2f}ms"

    @pytest.mark.asyncio
    async def test_gather_4_branches_latency(self, fast_runtime, fast_vault):
        """Measure cg.gather() with 4 branches."""
        parent = _make_governance_decision(
            decision_id="gd_gather_parent_4",
            actor_id="parent_actor",
            scope=DecisionScope(
                actions=["test.action", "branch.action"],
                resources=["test:resource", "branch:resource"],
            ),
        )
        await fast_vault.store_decision(parent)

        branches = [
            {"actor_id": f"branch_{i}", "action": "branch.action", "resource": "branch:resource"}
            for i in range(4)
        ]

        async def _run():
            await fast_runtime.gather(
                parent_decision=parent,
                branches=branches,
            )

        result = await benchmark("gather_4_branches", _run, iterations=20, warmup=3)
        print_result(result)
        assert result.avg_ms < 180, f"Gather 4 too slow: {result.avg_ms:.2f}ms"

    @pytest.mark.asyncio
    async def test_gather_8_branches_latency(self, fast_runtime, fast_vault):
        """Measure cg.gather() with 8 branches."""
        parent = _make_governance_decision(
            decision_id="gd_gather_parent_8",
            actor_id="parent_actor",
            scope=DecisionScope(
                actions=["test.action", "branch.action"],
                resources=["test:resource", "branch:resource"],
            ),
        )
        await fast_vault.store_decision(parent)

        branches = [
            {"actor_id": f"branch_{i}", "action": "branch.action", "resource": "branch:resource"}
            for i in range(8)
        ]

        async def _run():
            await fast_runtime.gather(
                parent_decision=parent,
                branches=branches,
            )

        result = await benchmark("gather_8_branches", _run, iterations=20, warmup=3)
        print_result(result)
        assert result.avg_ms < 300, f"Gather 8 too slow: {result.avg_ms:.2f}ms"

    @pytest.mark.asyncio
    async def test_gather_branch_parallelism(self, fast_runtime, fast_vault):
        """Verify gather branches run in parallel, not sequentially."""
        parent = _make_governance_decision(
            decision_id="gd_gather_par",
            actor_id="parent_actor",
            scope=DecisionScope(
                actions=["test.action", "branch.action"],
                resources=["test:resource", "branch:resource"],
            ),
        )
        await fast_vault.store_decision(parent)

        branches = [
            {"actor_id": f"branch_{i}", "action": "branch.action", "resource": "branch:resource"}
            for i in range(4)
        ]

        # Run once to measure total time
        start = time.perf_counter()
        await fast_runtime.gather(parent_decision=parent, branches=branches)
        elapsed_ms = (time.perf_counter() - start) * 1000.0

        # If branches ran sequentially, we'd expect ~4x single-branch time.
        # If parallel, should be closer to 1x (plus overhead).
        # Single branch ≈ 25-30ms. Sequential 4x ≈ 100-120ms.
        # Parallel should be < 60ms.
        print(f"\n  Gather 4 branches total time: {elapsed_ms:.2f}ms")
        assert elapsed_ms < 80, f"Gather branches appear sequential: {elapsed_ms:.2f}ms"


@pytest.mark.benchmark
class TestPerformanceIntrospection:
    """Introspection cost."""

    @pytest.mark.asyncio
    async def test_introspection_latency(self, fast_runtime, fast_vault):
        """Measure cg.introspect() latency."""
        parent = _make_governance_decision(
            decision_id="gd_introspect",
            actor_id="actor_1",
            scope=DecisionScope(actions=["test.action"], resources=["test:resource"]),
        )
        await fast_vault.store_decision(parent)

        async def _run():
            await fast_runtime.introspect(
                decision_id=parent.decision_id,
                required_action="test.action",
                tenant_id=parent.tenant_id,
            )

        result = await benchmark("introspection", _run, iterations=100, warmup=10)
        print_result(result)
        assert result.avg_ms < 20, f"Introspection too slow: {result.avg_ms:.2f}ms"

    @pytest.mark.asyncio
    async def test_token_verification_latency(self, fast_runtime, fast_vault):
        """Measure token verification latency."""
        parent = _make_governance_decision(
            decision_id="gd_verify",
            actor_id="actor_1",
            scope=DecisionScope(actions=["test.action"], resources=["test:resource"]),
        )
        await fast_vault.store_decision(parent)
        token = await fast_vault.issue_token_for_decision(parent, lifetime_seconds=3600)

        async def _run():
            await fast_runtime.verifier.verify_token(
                token.token_id,
                action="test.action",
                resource="test:resource",
            )

        result = await benchmark("token_verification", _run, iterations=100, warmup=10)
        print_result(result)
        assert result.avg_ms < 20, f"Token verification too slow: {result.avg_ms:.2f}ms"


@pytest.mark.benchmark
class TestPerformanceKillSwitch:
    """Kill-switch check cost."""

    @pytest.mark.asyncio
    async def test_kill_switch_check_latency(self, fast_runtime):
        """Measure kill-switch check latency."""
        async def _run():
            await fast_runtime.kill_switch.check(
                actor_id="actor_1",
                tenant_id="test_tenant",
                request_id="req_123",
            )

        result = await benchmark("kill_switch_check", _run, iterations=200, warmup=20)
        print_result(result)
        assert result.avg_ms < 5, f"Kill-switch check too slow: {result.avg_ms:.2f}ms"

    @pytest.mark.asyncio
    async def test_kill_switch_active_failure_path(self, fast_runtime, fast_vault):
        """Measure failure path when kill switch is active."""
        parent = _make_governance_decision(
            decision_id="gd_kill_parent",
            actor_id="actor_1",
            scope=DecisionScope(actions=["test.action"], resources=["test:resource"]),
        )
        await fast_vault.store_decision(parent)

        # Activate kill switch
        await fast_runtime.kill_switch.trigger(
            scope=KillSwitchScope.REQUEST,
            target_id=parent.decision_id,
            triggered_by="admin",
            triggered_by_type="human",
            reason="Emergency stop",
        )

        async def _run():
            await fast_runtime.delegate(
                parent_decision=parent,
                child_actor_id="child_actor",
                action_name="test.action",
                resource="test:resource",
                scope=DecisionScope(actions=["test.action"], resources=["test:resource"]),
            )

        result = await benchmark("kill_switch_failure_path", _run, iterations=50, warmup=5)
        print_result(result)
        assert result.avg_ms < 50, f"Kill-switch failure path too slow: {result.avg_ms:.2f}ms"


@pytest.mark.benchmark
class TestPerformanceConcurrency:
    """Concurrent workload performance."""

    @pytest.mark.asyncio
    async def test_concurrent_delegation_10(self, fast_runtime, fast_vault):
        """Measure throughput under 10 concurrent delegations."""
        parent = _make_governance_decision(
            decision_id="gd_concurrent_parent",
            actor_id="parent_actor",
            scope=DecisionScope(
                actions=["test.action", "child.action"],
                resources=["test:resource", "child:resource"],
            ),
        )
        await fast_vault.store_decision(parent)

        async def _delegate(i: int):
            return await fast_runtime.delegate(
                parent_decision=parent,
                child_actor_id=f"child_{i}",
                action_name="child.action",
                resource="child:resource",
                scope=DecisionScope(actions=["child.action"], resources=["child:resource"]),
            )

        start = time.perf_counter()
        await asyncio.gather(*[_delegate(i) for i in range(10)])
        elapsed_ms = (time.perf_counter() - start) * 1000.0

        print(f"\n{'='*60}")
        print(f"Benchmark: concurrent_delegation_10")
        print(f"  Total time: {elapsed_ms:.2f}ms")
        print(f"  Per-op avg: {elapsed_ms/10:.2f}ms")
        print(f"  Throughput: {10/(elapsed_ms/1000):.2f} ops/sec")
        assert elapsed_ms < 200, f"Concurrent delegation too slow: {elapsed_ms:.2f}ms"

    @pytest.mark.asyncio
    async def test_concurrent_introspection_50(self, fast_runtime, fast_vault):
        """Measure introspection throughput under 50 concurrent checks."""
        parent = _make_governance_decision(
            decision_id="gd_concurrent_intro",
            actor_id="actor_1",
            scope=DecisionScope(actions=["test.action"], resources=["test:resource"]),
        )
        await fast_vault.store_decision(parent)

        async def _introspect(i: int):
            return await fast_runtime.introspect(
                decision_id=parent.decision_id,
                required_action="test.action",
                tenant_id=parent.tenant_id,
            )

        start = time.perf_counter()
        await asyncio.gather(*[_introspect(i) for i in range(50)])
        elapsed_ms = (time.perf_counter() - start) * 1000.0

        print(f"\n{'='*60}")
        print(f"Benchmark: concurrent_introspection_50")
        print(f"  Total time: {elapsed_ms:.2f}ms")
        print(f"  Per-op avg: {elapsed_ms/50:.2f}ms")
        print(f"  Throughput: {50/(elapsed_ms/1000):.2f} ops/sec")
        assert elapsed_ms < 150, f"Concurrent introspection too slow: {elapsed_ms:.2f}ms"


@pytest.mark.benchmark
class TestPerformanceAuditOverhead:
    """Audit write overhead."""

    @pytest.mark.asyncio
    async def test_audit_event_count_per_delegate(self, fast_runtime, fast_vault, fast_audit):
        """Count how many audit events are generated per delegation."""
        parent = _make_governance_decision(
            decision_id="gd_audit_parent",
            actor_id="parent_actor",
            scope=DecisionScope(
                actions=["test.action", "child.action"],
                resources=["test:resource", "child:resource"],
            ),
        )
        await fast_vault.store_decision(parent)

        fast_audit.events.clear()
        await fast_runtime.delegate(
            parent_decision=parent,
            child_actor_id="child_actor",
            action_name="child.action",
            resource="child:resource",
            scope=DecisionScope(actions=["child.action"], resources=["child:resource"]),
        )

        event_count = len(fast_audit.events)
        print(f"\n{'='*60}")
        print(f"Benchmark: audit_events_per_delegate")
        print(f"  Events generated: {event_count}")
        for e in fast_audit.events:
            print(f"    - {e.get('type', e.get('event_type', 'unknown'))}")

        assert event_count < 15, f"Too many audit events: {event_count}"

    @pytest.mark.asyncio
    async def test_audit_event_count_per_gather_4(self, fast_runtime, fast_vault, fast_audit):
        """Count how many audit events are generated per gather(4 branches)."""
        parent = _make_governance_decision(
            decision_id="gd_audit_gather",
            actor_id="parent_actor",
            scope=DecisionScope(
                actions=["test.action", "branch.action"],
                resources=["test:resource", "branch:resource"],
            ),
        )
        await fast_vault.store_decision(parent)

        branches = [
            {"actor_id": f"branch_{i}", "action": "branch.action", "resource": "branch:resource"}
            for i in range(4)
        ]

        fast_audit.events.clear()
        await fast_runtime.gather(
            parent_decision=parent,
            branches=branches,
        )

        event_count = len(fast_audit.events)
        print(f"\n{'='*60}")
        print(f"Benchmark: audit_events_per_gather_4")
        print(f"  Events generated: {event_count}")
        for e in fast_audit.events:
            print(f"    - {e.get('type', e.get('event_type', 'unknown'))}")

        assert event_count < 40, f"Too many audit events for gather: {event_count}"


# ──────────────────────────────────────────────────────────────────────────────
# DB Round-Trip Analysis
# ──────────────────────────────────────────────────────────────────────────────

@pytest.mark.benchmark
class TestPerformanceDBRoundTrips:
    """Count DB round-trips per flow."""

    @pytest.mark.asyncio
    async def test_delegate_db_round_trips(self, fast_runtime, fast_vault):
        """Count DB round-trips in a single delegation."""
        parent = _make_governance_decision(
            decision_id="gd_db_parent",
            actor_id="parent_actor",
            scope=DecisionScope(
                actions=["test.action", "child.action"],
                resources=["test:resource", "child:resource"],
            ),
        )
        await fast_vault.store_decision(parent)

        # Wrap vault to count calls
        original_resolve = fast_vault.resolve_decision
        resolve_count = [0]
        async def counting_resolve(decision_id, tenant_id=None):
            resolve_count[0] += 1
            return await original_resolve(decision_id, tenant_id)
        fast_vault.resolve_decision = counting_resolve

        original_store = fast_vault.store_decision
        store_count = [0]
        async def counting_store(decision):
            store_count[0] += 1
            return await original_store(decision)
        fast_vault.store_decision = counting_store

        await fast_runtime.delegate(
            parent_decision=parent,
            child_actor_id="child_actor",
            action_name="child.action",
            resource="child:resource",
            scope=DecisionScope(actions=["child.action"], resources=["child:resource"]),
        )

        total_db_calls = resolve_count[0] + store_count[0]
        print(f"\n{'='*60}")
        print(f"Benchmark: delegate_db_round_trips")
        print(f"  resolve_decision calls: {resolve_count[0]}")
        print(f"  store_decision calls:   {store_count[0]}")
        print(f"  Total vault DB calls:   {total_db_calls}")
        assert total_db_calls <= 4, f"Too many DB round-trips: {total_db_calls}"

    @pytest.mark.asyncio
    async def test_introspect_db_round_trips(self, fast_runtime, fast_vault):
        """Count DB round-trips in a single introspection."""
        parent = _make_governance_decision(
            decision_id="gd_db_intro",
            actor_id="actor_1",
            scope=DecisionScope(actions=["test.action"], resources=["test:resource"]),
        )
        await fast_vault.store_decision(parent)

        original_resolve = fast_vault.resolve_decision
        resolve_count = [0]
        async def counting_resolve(decision_id, tenant_id=None):
            resolve_count[0] += 1
            return await original_resolve(decision_id, tenant_id)
        fast_vault.resolve_decision = counting_resolve

        await fast_runtime.introspect(
            decision_id=parent.decision_id,
            required_action="test.action",
            tenant_id=parent.tenant_id,
        )

        print(f"\n{'='*60}")
        print(f"Benchmark: introspect_db_round_trips")
        print(f"  resolve_decision calls: {resolve_count[0]}")
        assert resolve_count[0] <= 2, f"Too many DB round-trips: {resolve_count[0]}"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-m", "benchmark", "--tb=short"])
