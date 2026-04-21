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


async def test_audit_chain_integrity_under_load(kernel, db):
    """Given: 50 concurrent actions. When: All execute. Then: Audit chain valid."""
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
            action_name=f"test.load{idx % 5}",
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

    results = await asyncio.gather(*[submit_action(i) for i in range(50)], return_exceptions=True)

    valid_results = [r for r in results if isinstance(r, KernelResult)]
    assert len(valid_results) == 50, f"Expected 50 valid results, got {len(valid_results)}"

    chain_check = await db.fetchrow("SELECT * FROM verify_audit_chain()")
    assert chain_check['valid'] is True, f"Audit chain broken at event {chain_check.get('broken_at_event_id')}"


async def test_audit_chain_stress_iterations(kernel, db):
    """Stress: 10 iterations × 20 concurrent actions. Audit chain must stay valid."""
    kernel, repo = kernel

    actor_id = f"agent_{uuid.uuid4().hex[:8]}"

    await db.execute(
        "INSERT INTO actors (actor_id, actor_type, status) VALUES ($1, 'agent', 'active')",
        actor_id
    )

    for iteration in range(10):
        async def submit_action(idx: int) -> KernelResult:
            action = Action(
                action_id=uuid.uuid4(),
                actor_id=actor_id,
                actor_type='agent',
                action_name="test.stress_audit",
                resource="test",
                tenant_id=None,
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
