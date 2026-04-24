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

import asyncpg
from citadel.actions import Action, KernelStatus, KernelResult
from citadel.execution.kernel import Kernel
from citadel.repository import Repository
from citadel.policy_resolver import PolicyResolver, PolicyEvaluator
from citadel.precedence import Precedence
from citadel.approval_service import ApprovalService
from citadel.capability_service import CapabilityService
from citadel.audit_service import AuditService
from citadel.execution.executor import Executor


@pytest.fixture
async def db(postgres_dsn, tenant_id):
    """Database connection with tenant context set."""
    conn = await asyncpg.connect(postgres_dsn)
    await conn.execute("SELECT set_tenant_context($1)", tenant_id)
    yield conn
    await conn.close()


@pytest.fixture
async def kernel(postgres_dsn, tenant_id):
    """Fresh kernel instance with tenant-scoped pool."""
    async def setup_tenant(conn):
        await conn.execute("SELECT set_tenant_context($1)", tenant_id)

    pool = await asyncpg.create_pool(postgres_dsn, min_size=1, max_size=10, setup=setup_tenant)

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


async def test_racing_idempotency_basic(kernel, db, tenant_id):
    """Given: 10 concurrent requests with same idempotency key. When: All execute.
    Then: Exactly 1 action persisted, all return same decision, zero exceptions."""
    kernel, repo = kernel

    actor_id = f"agent_{uuid.uuid4().hex[:8]}"
    idempotency_key = f"concurrent_{uuid.uuid4().hex}"

    await db.execute(
        "INSERT INTO actors (actor_id, actor_type, tenant_id, status) VALUES ($1, 'agent', $2, 'active')",
        actor_id, tenant_id
    )

    async def submit_action(idx: int) -> KernelResult:
        action = Action(
            action_id=uuid.uuid4(),
            actor_id=actor_id,
            actor_type='agent',
            action_name="test.idempotent_race",
            resource="test",
            tenant_id=tenant_id,
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


async def test_idempotency_without_key_allows_duplicates(kernel, db, tenant_id):
    """Given: 5 concurrent requests with NO idempotency key. When: All execute.
    Then: All 5 actions persisted (no constraint on NULL keys)."""
    kernel, repo = kernel

    actor_id = f"agent_{uuid.uuid4().hex[:8]}"

    await db.execute(
        "INSERT INTO actors (actor_id, actor_type, tenant_id, status) VALUES ($1, 'agent', $2, 'active')",
        actor_id, tenant_id
    )

    async def submit_action(idx: int) -> KernelResult:
        action = Action(
            action_id=uuid.uuid4(),
            actor_id=actor_id,
            actor_type='agent',
            action_name="test.no_idempotency",
            resource="test",
            tenant_id=tenant_id,
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


async def test_idempotency_different_actors_same_key(kernel, db, tenant_id):
    """Given: Different actors with same idempotency key. When: Both execute.
    Then: Both succeed (idempotency scoped to actor, not global)."""
    kernel, repo = kernel

    actor_1 = f"agent_{uuid.uuid4().hex[:8]}"
    actor_2 = f"agent_{uuid.uuid4().hex[:8]}"
    shared_key = "shared_key"

    await db.execute(
        "INSERT INTO actors (actor_id, actor_type, tenant_id, status) VALUES ($1, 'agent', $2, 'active')",
        actor_1, tenant_id
    )
    await db.execute(
        "INSERT INTO actors (actor_id, actor_type, tenant_id, status) VALUES ($1, 'agent', $2, 'active')",
        actor_2, tenant_id
    )

    action_1 = Action(
        action_id=uuid.uuid4(),
        actor_id=actor_1,
        actor_type='agent',
        action_name="test.shared_key",
        resource="test",
        tenant_id=tenant_id,
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
        tenant_id=tenant_id,
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
