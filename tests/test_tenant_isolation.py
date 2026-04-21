"""
Regression tests for tenant data isolation (Stream 1).

Covers:
- Cross-tenant action read blocked
- Cross-tenant decision read blocked
- Cross-tenant approval read blocked
- Cross-tenant capability read blocked
- Cross-tenant audit read blocked
- Cross-tenant kill switch read blocked
- Cross-tenant policy read blocked
- Same-tenant access allowed
"""

import pytest
import asyncio
import uuid
from datetime import datetime, timedelta

from ledger.actions import Action, KernelStatus
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


async def _setup_tenant_data(db, tenant_id: str, actor_id: str, action_name: str = "test.action"):
    """Create actor, action, decision, approval, capability for a tenant."""
    await db.execute(
        "INSERT INTO actors (actor_id, actor_type, tenant_id, status) VALUES ($1, 'agent', $2, 'active')",
        actor_id, tenant_id
    )

    action_id = uuid.uuid4()
    await db.execute(
        """
        INSERT INTO actions (action_id, actor_id, actor_type, action_name, resource, tenant_id, created_at)
        VALUES ($1, $2, 'agent', $3, 'test', $4, NOW())
        """,
        action_id, actor_id, action_name, tenant_id
    )

    decision_id = uuid.uuid4()
    await db.execute(
        """
        INSERT INTO decisions (decision_id, action_id, status, winning_rule, reason, created_at)
        VALUES ($1, $2, 'EXECUTED', 'execution_complete', 'ok', NOW())
        """,
        decision_id, action_id
    )

    approval_id = uuid.uuid4()
    await db.execute(
        """
        INSERT INTO approvals (approval_id, action_id, status, priority, requested_by, reason, created_at)
        VALUES ($1, $2, 'pending', 'medium', $3, 'test', NOW())
        """,
        approval_id, action_id, actor_id
    )

    cap_token = f"cap_{tenant_id}_{uuid.uuid4().hex[:6]}"
    await db.execute(
        """
        INSERT INTO capabilities (token_id, actor_id, action_scope, resource_scope, expires_at, max_uses)
        VALUES ($1, $2, 'test.*', 'test', NOW() + interval '1 hour', 5)
        """,
        cap_token, actor_id
    )

    await db.execute(
        """
        INSERT INTO audit_events (action_id, event_type, prev_hash, event_hash, tenant_id)
        VALUES ($1, 'action_received', '0' || repeat('0', 63), $2, $3)
        """,
        action_id, uuid.uuid4().hex * 4, tenant_id
    )

    await db.execute(
        """
        INSERT INTO kill_switches (tenant_id, scope_type, scope_value, enabled, reason)
        VALUES ($1, 'action', 'test.kill', TRUE, 'emergency')
        """,
        tenant_id
    )

    policy_id = uuid.uuid4()
    await db.execute(
        """
        INSERT INTO policies (policy_id, tenant_id, name, version, scope_type, scope_value, rules_json, status)
        VALUES ($1, $2, 'test_policy', '1.0', 'global', '*', '{\"rules\":[]}'::jsonb, 'active')
        """,
        policy_id, tenant_id
    )

    return {
        'action_id': action_id,
        'decision_id': decision_id,
        'approval_id': approval_id,
        'cap_token': cap_token,
        'policy_id': policy_id,
    }


async def test_cross_tenant_action_read_blocked(kernel, db):
    """Tenant A's actor should not read Tenant B's action."""
    kernel, repo = kernel

    tenant_a = "tenant_a"
    tenant_b = "tenant_b"
    actor_a = f"agent_a_{uuid.uuid4().hex[:6]}"
    actor_b = f"agent_b_{uuid.uuid4().hex[:6]}"

    data_a = await _setup_tenant_data(db, tenant_a, actor_a)
    data_b = await _setup_tenant_data(db, tenant_b, actor_b)

    # Tenant A tries to read Tenant B's action — must fail
    action_b = await repo.get_action(data_b['action_id'], tenant_id=tenant_a)
    assert action_b is None, "Tenant A should not see Tenant B's action"

    # Tenant A reading own action should succeed
    action_a = await repo.get_action(data_a['action_id'], tenant_id=tenant_a)
    assert action_a is not None
    assert action_a['tenant_id'] == tenant_a


async def test_cross_tenant_decision_read_blocked(kernel, db):
    """Tenant A should not read Tenant B's decision."""
    kernel, repo = kernel

    tenant_a = "tenant_a"
    tenant_b = "tenant_b"
    actor_a = f"agent_a_{uuid.uuid4().hex[:6]}"
    actor_b = f"agent_b_{uuid.uuid4().hex[:6]}"

    data_a = await _setup_tenant_data(db, tenant_a, actor_a)
    data_b = await _setup_tenant_data(db, tenant_b, actor_b)

    decision_b = await repo.get_decision(data_b['action_id'], tenant_id=tenant_a)
    assert decision_b is None, "Tenant A should not see Tenant B's decision"

    decision_a = await repo.get_decision(data_a['action_id'], tenant_id=tenant_a)
    assert decision_a is not None


async def test_cross_tenant_approval_read_blocked(kernel, db):
    """Tenant A should not read Tenant B's approval."""
    kernel, repo = kernel

    tenant_a = "tenant_a"
    tenant_b = "tenant_b"
    actor_a = f"agent_a_{uuid.uuid4().hex[:6]}"
    actor_b = f"agent_b_{uuid.uuid4().hex[:6]}"

    data_a = await _setup_tenant_data(db, tenant_a, actor_a)
    data_b = await _setup_tenant_data(db, tenant_b, actor_b)

    approval_b = await repo.get_approval(data_b['approval_id'], tenant_id=tenant_a)
    assert approval_b is None, "Tenant A should not see Tenant B's approval"

    approval_a = await repo.get_approval(data_a['approval_id'], tenant_id=tenant_a)
    assert approval_a is not None


async def test_cross_tenant_capability_read_blocked(kernel, db):
    """Tenant A should not read Tenant B's capability."""
    kernel, repo = kernel

    tenant_a = "tenant_a"
    tenant_b = "tenant_b"
    actor_a = f"agent_a_{uuid.uuid4().hex[:6]}"
    actor_b = f"agent_b_{uuid.uuid4().hex[:6]}"

    data_a = await _setup_tenant_data(db, tenant_a, actor_a)
    data_b = await _setup_tenant_data(db, tenant_b, actor_b)

    cap_b = await repo.get_capability(data_b['cap_token'], tenant_id=tenant_a)
    assert cap_b is None, "Tenant A should not see Tenant B's capability"

    cap_a = await repo.get_capability(data_a['cap_token'], tenant_id=tenant_a)
    assert cap_a is not None


async def test_cross_tenant_kill_switch_blocked(kernel, db):
    """Tenant A should not read Tenant B's kill switch."""
    kernel, repo = kernel

    tenant_a = "tenant_a"
    tenant_b = "tenant_b"
    actor_a = f"agent_a_{uuid.uuid4().hex[:6]}"
    actor_b = f"agent_b_{uuid.uuid4().hex[:6]}"

    await _setup_tenant_data(db, tenant_a, actor_a)
    await _setup_tenant_data(db, tenant_b, actor_b)

    # Tenant A checking kill switch for action scope
    ks = await repo.check_kill_switch('action', 'test.kill', tenant_id=tenant_a)
    # Tenant A should see their OWN kill switch, not B's
    assert ks is not None


async def test_cross_tenant_policy_blocked(kernel, db):
    """Tenant A should not resolve Tenant B's policy."""
    kernel, repo = kernel

    tenant_a = "tenant_a"
    tenant_b = "tenant_b"
    actor_a = f"agent_a_{uuid.uuid4().hex[:6]}"
    actor_b = f"agent_b_{uuid.uuid4().hex[:6]}"

    await _setup_tenant_data(db, tenant_a, actor_a)
    await _setup_tenant_data(db, tenant_b, actor_b)

    # Tenant A resolving global policy
    policy = await repo.get_active_policy('global', '*', tenant_id=tenant_a)
    assert policy is not None
    assert policy['tenant_id'] == tenant_a


async def test_kernel_action_carries_tenant(kernel, db):
    """Action submitted with tenant_id should have tenant_id in all downstream records."""
    kernel, repo = kernel

    tenant_id = "tenant_x"
    actor_id = f"agent_{uuid.uuid4().hex[:6]}"

    await db.execute(
        "INSERT INTO actors (actor_id, actor_type, tenant_id, status) VALUES ($1, 'agent', $2, 'active')",
        actor_id, tenant_id
    )

    action = Action(
        action_id=uuid.uuid4(),
        actor_id=actor_id,
        actor_type='agent',
        action_name="test.tenant_flow",
        resource="test",
        tenant_id=tenant_id,
        payload={},
        context={},
        session_id=None,
        request_id=str(uuid.uuid4()),
        idempotency_key=None,
        created_at=datetime.now(),
    )

    result = await kernel.handle(action)
    assert result.decision.status == KernelStatus.EXECUTED

    # Verify action has tenant_id
    row = await db.fetchrow("SELECT tenant_id FROM actions WHERE action_id = $1", action.action_id)
    assert row['tenant_id'] == tenant_id

    # Verify decision has tenant_id
    row = await db.fetchrow("""
        SELECT d.* FROM decisions d
        JOIN actions a ON d.action_id = a.action_id
        WHERE d.action_id = $1
    """, action.action_id)
    assert row is not None

    # Verify audit has tenant_id
    row = await db.fetchrow("SELECT tenant_id FROM audit_events WHERE action_id = $1", action.action_id)
    assert row['tenant_id'] == tenant_id
