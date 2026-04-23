"""
Regression tests for capability race under concurrency (Issue 2).

Covers:
- Racing consumption: multiple concurrent requests with limited-use capability
- Exhaustion guardrail: exhausted capability stays exhausted under concurrent load
- Consumption-before-execution semantic: even failed executions consume a use
"""

import pytest
import asyncio
import uuid
from datetime import datetime

import asyncpg
from ledger.actions import Action, KernelStatus
from ledger.execution.kernel import Kernel
from ledger.repository import Repository
from ledger.policy_resolver import PolicyResolver, PolicyEvaluator
from ledger.precedence import Precedence
from ledger.approval_service import ApprovalService
from ledger.capability_service import CapabilityService
from ledger.audit_service import AuditService
from ledger.execution.executor import Executor


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


async def test_racing_capability_consumption_basic(kernel, db, tenant_id):
    """Given: 5 concurrent requests with max_uses=3. When: All execute. Then: Exactly 3 succeed."""
    kernel, repo = kernel

    actor_id = f"agent_{uuid.uuid4().hex[:8]}"
    token_id = f"cap_{uuid.uuid4().hex[:8]}"
    max_uses = 3

    await db.execute(
        "INSERT INTO actors (actor_id, actor_type, tenant_id, status) VALUES ($1, 'agent', $2, 'active')",
        actor_id, tenant_id
    )
    await db.execute(
        """
        INSERT INTO capabilities (token_id, actor_id, tenant_id, action_scope, resource_scope, expires_at, max_uses)
        VALUES ($1, $2, $3, 'test.*', 'test', NOW() + interval '1 hour', $4)
        """,
        token_id, actor_id, tenant_id, max_uses
    )

    async def submit_action(idx: int):
        action = Action(
            action_id=uuid.uuid4(),
            actor_id=actor_id,
            actor_type='agent',
            action_name="test.race",
            resource="test",
            tenant_id=tenant_id,
            payload={"idx": idx},
            context={},
            session_id=None,
            request_id=str(uuid.uuid4()),
            idempotency_key=None,
            created_at=datetime.now(),
        )
        return await kernel.handle(action, capability_token=token_id)

    results = await asyncio.gather(*[submit_action(i) for i in range(5)], return_exceptions=True)

    successes = sum(1 for r in results if isinstance(r, type(results[0])) and r.decision.status == KernelStatus.EXECUTED)
    failures = sum(1 for r in results if isinstance(r, type(results[0])) and r.decision.status == KernelStatus.BLOCKED_CAPABILITY)

    assert successes == max_uses, f"Expected {max_uses} successes, got {successes}"
    assert failures == 5 - max_uses, f"Expected {5 - max_uses} failures, got {failures}"


async def test_capability_exhausted_stays_exhausted(kernel, db, tenant_id):
    """Given: Capability already exhausted. When: 10 concurrent attempts. Then: All blocked."""
    kernel, repo = kernel

    actor_id = f"agent_{uuid.uuid4().hex[:8]}"
    token_id = f"cap_{uuid.uuid4().hex[:8]}"

    await db.execute(
        "INSERT INTO actors (actor_id, actor_type, tenant_id, status) VALUES ($1, 'agent', $2, 'active')",
        actor_id, tenant_id
    )
    await db.execute(
        """
        INSERT INTO capabilities (token_id, actor_id, tenant_id, action_scope, resource_scope, expires_at, max_uses, uses)
        VALUES ($1, $2, $3, 'test.*', 'test', NOW() + interval '1 hour', 2, 2)
        """,
        token_id, actor_id, tenant_id
    )

    async def submit_action(idx: int):
        action = Action(
            action_id=uuid.uuid4(),
            actor_id=actor_id,
            actor_type='agent',
            action_name="test.exhausted",
            resource="test",
            tenant_id=tenant_id,
            payload={"idx": idx},
            context={},
            session_id=None,
            request_id=str(uuid.uuid4()),
            idempotency_key=None,
            created_at=datetime.now(),
        )
        return await kernel.handle(action, capability_token=token_id)

    results = await asyncio.gather(*[submit_action(i) for i in range(10)], return_exceptions=True)

    blocked = sum(1 for r in results if isinstance(r, type(results[0])) and r.decision.status == KernelStatus.BLOCKED_CAPABILITY)
    assert blocked == 10, f"Expected all 10 blocked, got {blocked}"


async def test_consumption_before_execution_semantic(kernel, db, tenant_id):
    """Given: Capability with 1 use, action that fails in executor. When: Executed. Then: Use is consumed anyway."""
    kernel, repo = kernel

    actor_id = f"agent_{uuid.uuid4().hex[:8]}"
    token_id = f"cap_{uuid.uuid4().hex[:8]}"

    await db.execute(
        "INSERT INTO actors (actor_id, actor_type, tenant_id, status) VALUES ($1, 'agent', $2, 'active')",
        actor_id, tenant_id
    )
    await db.execute(
        """
        INSERT INTO capabilities (token_id, actor_id, tenant_id, action_scope, resource_scope, expires_at, max_uses)
        VALUES ($1, $2, $3, 'fail.*', 'test', NOW() + interval '1 hour', 1)
        """,
        token_id, actor_id, tenant_id
    )

    action = Action(
        action_id=uuid.uuid4(),
        actor_id=actor_id,
        actor_type='agent',
        action_name="fail.action",
        resource="test",
        tenant_id=tenant_id,
        payload={},
        context={},
        session_id=None,
        request_id=str(uuid.uuid4()),
        idempotency_key=None,
        created_at=datetime.now(),
    )

    result = await kernel.handle(action, capability_token=token_id)
    cap = await db.fetchrow("SELECT * FROM capabilities WHERE token_id = $1", token_id)
    assert cap['uses'] == 1, f"Expected capability consumed (uses=1), got uses={cap['uses']}"


async def test_racing_capability_stress(kernel, db, tenant_id):
    """Stress: 100 iterations × 10 concurrent workers with max_uses=5. Zero double-consumption."""
    kernel, repo = kernel

    actor_id = f"agent_{uuid.uuid4().hex[:8]}"

    await db.execute(
        "INSERT INTO actors (actor_id, actor_type, tenant_id, status) VALUES ($1, 'agent', $2, 'active')",
        actor_id, tenant_id
    )

    ITERATIONS = 100
    WORKERS = 10
    MAX_USES = 5

    for iteration in range(ITERATIONS):
        token_id = f"cap_{iteration}_{uuid.uuid4().hex[:6]}"
        await db.execute(
            """
            INSERT INTO capabilities (token_id, actor_id, tenant_id, action_scope, resource_scope, expires_at, max_uses)
            VALUES ($1, $2, $3, 'test.*', 'test', NOW() + interval '1 hour', $4)
            """,
            token_id, actor_id, tenant_id, MAX_USES
        )

        async def submit_action(idx: int):
            action = Action(
                action_id=uuid.uuid4(),
                actor_id=actor_id,
                actor_type='agent',
                action_name="test.stress",
                resource="test",
                tenant_id=tenant_id,
                payload={"idx": idx},
                context={},
                session_id=None,
                request_id=str(uuid.uuid4()),
                idempotency_key=None,
                created_at=datetime.now(),
            )
            return await kernel.handle(action, capability_token=token_id)

        results = await asyncio.gather(*[submit_action(i) for i in range(WORKERS)], return_exceptions=True)

        successes = sum(1 for r in results if isinstance(r, type(results[0])) and r.decision.status == KernelStatus.EXECUTED)
        failures = sum(1 for r in results if isinstance(r, type(results[0])) and r.decision.status == KernelStatus.BLOCKED_CAPABILITY)

        assert successes == MAX_USES, f"Iteration {iteration}: Expected {MAX_USES} successes, got {successes}"
        assert failures == WORKERS - MAX_USES, f"Iteration {iteration}: Expected {WORKERS - MAX_USES} failures, got {failures}"
