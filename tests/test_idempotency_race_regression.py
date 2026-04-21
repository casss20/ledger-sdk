"""
Regression tests for idempotency race under concurrency (Issue 2.5).

Covers:
- Racing idempotency: 10 concurrent requests with same idempotency key
- Exactly one action persisted, all return same decision
- Partial unique index: only non-null idempotency_keys are constrained
"""

import pytest
import asyncio
import uuid
from datetime import datetime

from ledger.actions import Action, KernelStatus, KernelResult
from ledger.execution.kernel import Kernel
from ledger.repository import Repository
from ledger.policy_resolver import PolicyResolver, PolicyEvaluator
from ledger.precedence import Precedence
from ledger.approval_service import ApprovalService
from ledger.capability_service import CapabilityService
from ledger.audit_service import AuditService
from ledger.execution.executor import Executor
import asyncpg


@pytest.fixture
async def postgres_dsn():
    return "postgresql://ledger:ledger@localhost:5432/ledger_test"


@pytest.fixture
async def db(postgres_dsn):
    conn = await asyncpg.connect(postgres_dsn)
    yield conn
    await conn.close()


@pytest.fixture(autouse=True)
async def clean_database(postgres_dsn):
    conn = await asyncpg.connect(postgres_dsn)
    await conn.execute("""
        TRUNCATE actors, policies, policy_snapshots, capabilities,
                    kill_switches, approvals, actions, decisions,
                    audit_events, execution_results
        CASCADE
    """)
    await conn.close()
    yield


@pytest.fixture
async def kernel(postgres_dsn):
    pool = await asyncpg.create_pool(postgres_dsn, min_size=1, max_size=10)

    repo = Repository(pool)
    policy_resolver = PolicyResolver(repo)
    policy_evaluator = PolicyEvaluator()
    precedence = Precedence(repo, policy_evaluator)
    approval_service = ApprovalService(repo)
    capability_service = CapabilityService(repo)
    audit_service = AuditService(repo)
    executor = Executor()

    kernel = Kernel(
        repository=repo,
        policy_resolver=policy_resolver,
        precedence=precedence,
        approval_service=approval_service,
        capability_service=capability_service,
        audit_service=audit_service,
        executor=executor,
    )

    yield kernel, repo

    await pool.close()


async def test_racing_idempotency_basic(kernel, db):
    """Given: 10 concurrent requests with same idempotency key. When: All execute.
    Then: Exactly 1 action persisted, all return same decision, zero exceptions."""
    kernel, repo = kernel

    actor_id = f"agent_{uuid.uuid4().hex[:8]}"
    idempotency_key = f"concurrent_{uuid.uuid4().hex}"

    await db.execute(
        "INSERT INTO actors (actor_id, actor_type, status) VALUES ($1, 'agent', 'active')",
        actor_id
    )

    async def submit_action(idx: int) -> KernelResult:
        action = Action(
            action_id=uuid.uuid4(),
            actor_id=actor_id,
            actor_type='agent',
            action_name="test.idempotent_race",
            resource="test",
            tenant_id=None,
            payload={"idx": idx},
            context={},
            session_id=None,
            request_id=str(uuid.uuid4()),
            idempotency_key=idempotency_key,
            created_at=datetime.now(),
        )
        return await kernel.handle(action)

    results = await asyncio.gather(*[submit_action(i) for i in range(10)], return_exceptions=True)

    # All should return valid KernelResult (no exceptions)
    valid_results = [r for r in results if isinstance(r, KernelResult)]
    assert len(valid_results) == 10, f"Expected 10 valid results, got {len(valid_results)} (exceptions: {[r for r in results if not isinstance(r, KernelResult)]})"

    # All should have the same decision status
    statuses = {r.decision.status for r in valid_results}
    assert len(statuses) == 1, f"Expected 1 unique status, got {statuses}"

    # Verify exactly ONE action in DB
    actions = await db.fetch(
        "SELECT * FROM actions WHERE actor_id = $1 AND idempotency_key = $2",
        actor_id, idempotency_key
    )
    assert len(actions) == 1, f"Expected 1 action, got {len(actions)}"


async def test_idempotency_without_key_allows_duplicates(kernel, db):
    """Given: 5 concurrent requests with NO idempotency key. When: All execute.
    Then: All 5 actions persisted (no constraint on NULL keys)."""
    kernel, repo = kernel

    actor_id = f"agent_{uuid.uuid4().hex[:8]}"

    await db.execute(
        "INSERT INTO actors (actor_id, actor_type, status) VALUES ($1, 'agent', 'active')",
        actor_id
    )

    async def submit_action(idx: int) -> KernelResult:
        action = Action(
            action_id=uuid.uuid4(),
            actor_id=actor_id,
            actor_type='agent',
            action_name="test.no_idempotency",
            resource="test",
            tenant_id=None,
            payload={"idx": idx},
            context={},
            session_id=None,
            request_id=str(uuid.uuid4()),
            idempotency_key=None,
            created_at=datetime.now(),
        )
        return await kernel.handle(action)

    results = await asyncio.gather(*[submit_action(i) for i in range(5)], return_exceptions=True)

    valid_results = [r for r in results if isinstance(r, KernelResult)]
    assert len(valid_results) == 5

    actions = await db.fetch(
        "SELECT * FROM actions WHERE actor_id = $1",
        actor_id
    )
    assert len(actions) == 5, f"Expected 5 actions without idempotency, got {len(actions)}"


async def test_idempotency_different_actors_same_key(kernel, db):
    """Given: Different actors with same idempotency key. When: Both execute.
    Then: Both succeed (idempotency scoped to actor, not global)."""
    kernel, repo = kernel

    actor_1 = f"agent_{uuid.uuid4().hex[:8]}"
    actor_2 = f"agent_{uuid.uuid4().hex[:8]}"
    shared_key = "shared_key"

    await db.execute(
        "INSERT INTO actors (actor_id, actor_type, status) VALUES ($1, 'agent', 'active')",
        actor_1
    )
    await db.execute(
        "INSERT INTO actors (actor_id, actor_type, status) VALUES ($1, 'agent', 'active')",
        actor_2
    )

    action_1 = Action(
        action_id=uuid.uuid4(),
        actor_id=actor_1,
        actor_type='agent',
        action_name="test.shared_key",
        resource="test",
        tenant_id=None,
        payload={},
        context={},
        session_id=None,
        request_id=str(uuid.uuid4()),
        idempotency_key=shared_key,
        created_at=datetime.now(),
    )
    action_2 = Action(
        action_id=uuid.uuid4(),
        actor_id=actor_2,
        actor_type='agent',
        action_name="test.shared_key",
        resource="test",
        tenant_id=None,
        payload={},
        context={},
        session_id=None,
        request_id=str(uuid.uuid4()),
        idempotency_key=shared_key,
        created_at=datetime.now(),
    )

    result_1 = await kernel.handle(action_1)
    result_2 = await kernel.handle(action_2)

    assert result_1.decision.status == KernelStatus.EXECUTED
    assert result_2.decision.status == KernelStatus.EXECUTED
