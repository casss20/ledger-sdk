"""
Regression tests for audit chain ordering race under concurrency (Issue 3).

Covers:
- Racing audit append: 50 concurrent actions all append audit events
- Hash chain integrity: verify_audit_chain() must return valid=True
- Stress: multiple iterations to catch rare races
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


async def test_audit_chain_integrity_under_load(kernel, db, tenant_id):
    """Given: 50 concurrent actions. When: All execute. Then: Audit chain valid."""
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
            action_name=f"test.load{idx % 5}",
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

    results = await asyncio.gather(*[submit_action(i) for i in range(50)], return_exceptions=True)

    valid_results = [r for r in results if isinstance(r, KernelResult)]
    assert len(valid_results) == 50, f"Expected 50 valid results, got {len(valid_results)}"

    chain_check = await db.fetchrow("SELECT * FROM verify_audit_chain()")
    assert chain_check['valid'] is True, f"Audit chain broken at event {chain_check.get('broken_at_event_id')}"


async def test_audit_chain_stress_iterations(kernel, db, tenant_id):
    """Stress: 10 iterations × 20 concurrent actions. Audit chain must stay valid."""
    kernel, repo = kernel

    actor_id = f"agent_{uuid.uuid4().hex[:8]}"

    await db.execute(
        "INSERT INTO actors (actor_id, actor_type, tenant_id, status) VALUES ($1, 'agent', $2, 'active')",
        actor_id, tenant_id
    )

    for iteration in range(10):
        async def submit_action(idx: int) -> KernelResult:
            action = Action(
                action_id=uuid.uuid4(),
                actor_id=actor_id,
                actor_type='agent',
                action_name="test.stress_audit",
                resource="test",
                tenant_id=tenant_id,
                payload={"iteration": iteration, "idx": idx},
                context={},
                session_id=None,
                request_id=str(uuid.uuid4()),
                idempotency_key=None,
                created_at=datetime.now(),
            )
            return await kernel.handle(action)

        results = await asyncio.gather(*[submit_action(i) for i in range(20)], return_exceptions=True)

        valid_results = [r for r in results if isinstance(r, KernelResult)]
        assert len(valid_results) == 20, f"Iteration {iteration}: Expected 20 valid results, got {len(valid_results)}"

        chain_check = await db.fetchrow("SELECT * FROM verify_audit_chain()")
        assert chain_check['valid'] is True, f"Iteration {iteration}: Audit chain broken at event {chain_check.get('broken_at_event_id')}"
