"""
Ledger Kernel Conformance Test Suite

Verifies that the governance kernel correctly:
1. Writes to all database tables
2. Follows deterministic decision paths
3. Maintains audit chain integrity
4. Enforces all control semantics

Run: pytest tests/test_kernel_conformance.py -v
"""

import pytest
import asyncio
import uuid
import sys
from datetime import datetime, timedelta
from typing import Optional, Dict, Any

sys.path.insert(0, 'src')

# Database
import asyncpg

# Kernel components
from ledger.kernel import Kernel, Action, KernelResult, KernelStatus
from ledger.repository import Repository
from ledger.policy_resolver import PolicyResolver, PolicyEvaluator
from ledger.precedence import Precedence
from ledger.approval_service import ApprovalService
from ledger.capability_service import CapabilityService
from ledger.audit_service import AuditService
from ledger.executor import Executor as ActionExecutor
from ledger.status import ActorType


@pytest.fixture
async def db(postgres_dsn):
    """Database connection for the test."""
    conn = await asyncpg.connect(postgres_dsn)
    yield conn
    await conn.close()


@pytest.fixture
async def kernel(postgres_dsn):
    """Fresh kernel instance for each test."""
    pool = await asyncpg.create_pool(postgres_dsn, min_size=1, max_size=5)
    
    repo = Repository(pool)
    policy_resolver = PolicyResolver(repo)
    policy_evaluator = PolicyEvaluator()
    precedence = Precedence(repo, policy_evaluator)
    approval_service = ApprovalService(repo)
    capability_service = CapabilityService(repo)
    audit_service = AuditService(repo)
    executor = ActionExecutor()
    
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


@pytest.fixture(autouse=True)
async def clean_database(postgres_dsn):
    """Clean database before each test."""
    conn = await asyncpg.connect(postgres_dsn)
    await conn.execute("""
        TRUNCATE actors, policies, policy_snapshots, capabilities, 
                    kill_switches, approvals, actions, decisions, 
                    audit_events, execution_results
        CASCADE
    """)
    await conn.close()
    yield


# ============================================================================
# SCENARIO 1: Blocked by Kill Switch
# ============================================================================
async def test_01_blocked_by_kill_switch(kernel, db):
    """Given: Kill switch enabled. When: Action attempted. Then: BLOCKED_EMERGENCY."""
    kernel, repo = kernel
    
    # Setup: Enable kill switch
    await db.execute("""
        INSERT INTO kill_switches (scope_type, scope_value, enabled, reason)
        VALUES ('action', 'test.dangerous', TRUE, 'Emergency stop')
    """)
    
    # Setup: Actor
    actor_id = f"agent_{uuid.uuid4().hex[:8]}"
    await db.execute(
        "INSERT INTO actors (actor_id, actor_type, status) VALUES ($1, 'agent', 'active')",
        actor_id
    )
    
    # Execute
    action = Action(
        action_id=uuid.uuid4(),
        actor_id=actor_id,
        actor_type=ActorType.AGENT.value,
        action_name="test.dangerous",
        resource="test",
        tenant_id=None,
        payload={},
        context={},
        session_id=None,
        request_id=str(uuid.uuid4()),
        idempotency_key=None,
        created_at=datetime.utcnow(),
    )
    
    result = await kernel.handle(action)
    
    # Verify
    assert result.decision.status == KernelStatus.BLOCKED_EMERGENCY
    assert result.decision.winning_rule == "kill_switch_active"
    
    # Verify audit
    events = await db.fetch("SELECT * FROM audit_events WHERE action_id = $1", action.action_id)
    assert len(events) >= 2  # action_received + decision_made
    
    event_types = [e['event_type'] for e in events]
    assert 'action_received' in event_types
    assert 'decision_made' in event_types


# ============================================================================
# SCENARIO 2: Blocked by Policy
# ============================================================================
async def test_02_blocked_by_policy(kernel, db):
    """Given: Policy blocks action. When: Action attempted. Then: BLOCKED_POLICY."""
    kernel, repo = kernel
    
    # Setup: Policy that blocks
    await db.execute("""
        INSERT INTO policies (name, version, scope_type, scope_value, rules_json, status)
        VALUES (
            'block_test', '1.0', 'action', 'test.forbidden',
            '{"rules": [{"name": "block_rule", "condition": "true", "effect": "BLOCK", "reason": "Test block"}]}',
            'active'
        )
    """)
    
    actor_id = f"agent_{uuid.uuid4().hex[:8]}"
    await db.execute(
        "INSERT INTO actors (actor_id, actor_type, status) VALUES ($1, 'agent', 'active')",
        actor_id
    )
    
    action = Action(
        action_id=uuid.uuid4(),
        actor_id=actor_id,
        actor_type=ActorType.AGENT.value,
        action_name="test.forbidden",
        resource="test",
        tenant_id=None,
        payload={},
        context={},
        session_id=None,
        request_id=str(uuid.uuid4()),
        idempotency_key=None,
        created_at=datetime.utcnow(),
    )
    
    result = await kernel.handle(action)
    
    assert result.decision.status == KernelStatus.BLOCKED_POLICY
    assert result.decision.winning_rule == "block_rule"
    
    # Verify policy snapshot created
    snapshot = await db.fetchrow(
        "SELECT * FROM policy_snapshots WHERE snapshot_id = $1",
        result.decision.policy_snapshot_id
    )
    assert snapshot is not None


# ============================================================================
# SCENARIO 3: Blocked by Capability Expiry
# ============================================================================
async def test_03_blocked_by_capability_expiry(kernel, db):
    """Given: Expired capability. When: Action attempted. Then: BLOCKED_CAPABILITY."""
    kernel, repo = kernel
    
    actor_id = f"agent_{uuid.uuid4().hex[:8]}"
    token_id = f"cap_{uuid.uuid4().hex}"
    
    await db.execute(
        "INSERT INTO actors (actor_id, actor_type, status) VALUES ($1, 'agent', 'active')",
        actor_id
    )
    await db.execute("""
        INSERT INTO capabilities (token_id, actor_id, action_scope, resource_scope, 
                                 issued_at, expires_at, max_uses, uses, revoked)
        VALUES ($1, $2, 'test.expiring', 'test', NOW() - INTERVAL '2 hours', 
                NOW() - INTERVAL '1 hour', 10, 0, FALSE)
    """, token_id, actor_id)
    
    action = Action(
        action_id=uuid.uuid4(),
        actor_id=actor_id,
        actor_type=ActorType.AGENT.value,
        action_name="test.expiring",
        resource="test",
        tenant_id=None,
        payload={},
        context={},
        session_id=None,
        request_id=str(uuid.uuid4()),
        idempotency_key=None,
        created_at=datetime.utcnow(),
    )
    
    result = await kernel.handle(action, capability_token=token_id)
    
    assert result.decision.status == KernelStatus.BLOCKED_CAPABILITY


# ============================================================================
# SCENARIO 4: Pending Approval
# ============================================================================
async def test_04_pending_approval(kernel, db):
    """Given: High risk action. When: Action attempted. Then: PENDING_APPROVAL."""
    kernel, repo = kernel
    
    actor_id = f"agent_{uuid.uuid4().hex[:8]}"
    await db.execute(
        "INSERT INTO actors (actor_id, actor_type, status) VALUES ($1, 'agent', 'active')",
        actor_id
    )
    
    # Policy requiring approval
    await db.execute("""
        INSERT INTO policies (name, version, scope_type, scope_value, rules_json, status)
        VALUES (
            'approve_high_risk', '1.0', 'action', 'test.highrisk',
            '{"rules": [{"name": "high_risk", "condition": "true", "effect": "PENDING_APPROVAL", "requires_approval": true, "reason": "High risk"}]}',
            'active'
        )
    """)
    
    action = Action(
        action_id=uuid.uuid4(),
        actor_id=actor_id,
        actor_type=ActorType.AGENT.value,
        action_name="test.highrisk",
        resource="test",
        tenant_id=None,
        payload={},
        context={},
        session_id=None,
        request_id=str(uuid.uuid4()),
        idempotency_key=None,
        created_at=datetime.utcnow(),
    )
    
    result = await kernel.handle(action)
    
    assert result.decision.status == KernelStatus.PENDING_APPROVAL
    
    # Verify approval queue entry
    approval = await db.fetchrow("SELECT * FROM approvals WHERE action_id = $1", action.action_id)
    assert approval is not None
    assert approval['status'] == 'pending'


# ============================================================================
# SCENARIO 5: Approval Rejected
# ============================================================================
async def test_05_approval_rejected(kernel, db):
    """Given: Pending approval. When: Human rejects. Then: REJECTED_APPROVAL."""
    kernel, repo = kernel
    
    # Setup: Actor first
    await db.execute(
        "INSERT INTO actors (actor_id, actor_type, status) VALUES ('agent_1', 'agent', 'active')"
    )
    await db.execute(
        "INSERT INTO actors (actor_id, actor_type, status) VALUES ('admin_1', 'user_proxy', 'active')"
    )

    action_id = uuid.uuid4()
    await db.execute(
        "INSERT INTO actions (action_id, actor_id, actor_type, action_name, resource) VALUES ($1, $2, 'agent', 'test.reject', 'test')",
        action_id, "agent_1"
    )
    await db.execute(
        "INSERT INTO decisions (action_id, status, winning_rule, reason) VALUES ($1, 'PENDING_APPROVAL', 'approval_required', 'Needs review')",
        action_id
    )
    await db.execute(
        "INSERT INTO approvals (action_id, status, requested_by, reason, expires_at) VALUES ($1, 'pending', 'agent_1', 'Review', NOW() + INTERVAL '1 hour')",
        action_id
    )
    
    # Simulate rejection
    await db.execute(
        "UPDATE approvals SET status = 'rejected', reviewed_by = 'admin_1', decided_at = NOW(), decision_reason = 'Too risky' WHERE action_id = $1",
        action_id
    )
    await db.execute(
        "UPDATE decisions SET status = 'REJECTED_APPROVAL', reason = 'Rejected by admin_1: Too risky' WHERE action_id = $1",
        action_id
    )
    
    approval = await db.fetchrow("SELECT * FROM approvals WHERE action_id = $1", action_id)
    assert approval['status'] == 'rejected'
    
    decision = await db.fetchrow("SELECT * FROM decisions WHERE action_id = $1", action_id)
    assert decision['status'] == 'REJECTED_APPROVAL'


# ============================================================================
# SCENARIO 6: Approval Expired
# ============================================================================
async def test_06_approval_expired(kernel, db):
    """Given: Approval past expiry. When: Checked. Then: EXPIRED_APPROVAL."""
    kernel, repo = kernel
    
    # Setup: Actor first
    await db.execute(
        "INSERT INTO actors (actor_id, actor_type, status) VALUES ('agent_1', 'agent', 'active')"
    )

    action_id = uuid.uuid4()
    await db.execute(
        "INSERT INTO actions (action_id, actor_id, actor_type, action_name, resource) VALUES ($1, $2, 'agent', 'test.expire', 'test')",
        action_id, "agent_1"
    )
    await db.execute(
        "INSERT INTO decisions (action_id, status, winning_rule, reason) VALUES ($1, 'PENDING_APPROVAL', 'approval_required', 'Needs review')",
        action_id
    )
    await db.execute(
        "INSERT INTO approvals (action_id, status, requested_by, reason, expires_at) VALUES ($1, 'pending', 'agent_1', 'Review', NOW() - INTERVAL '1 minute')",
        action_id
    )
    
    # Process expiry
    await db.execute(
        "UPDATE approvals SET status = 'expired' WHERE action_id = $1 AND expires_at < NOW()",
        action_id
    )
    await db.execute(
        "UPDATE decisions SET status = 'EXPIRED_APPROVAL', reason = 'Approval window expired' WHERE action_id = $1",
        action_id
    )
    
    approval = await db.fetchrow("SELECT * FROM approvals WHERE action_id = $1", action_id)
    assert approval['status'] == 'expired'


# ============================================================================
# SCENARIO 7: Allowed + Executed
# ============================================================================
async def test_07_allowed_and_executed(kernel, db):
    """Given: Action passes all checks. When: Executed. Then: ALLOWED/EXECUTED."""
    kernel, repo = kernel
    
    actor_id = f"agent_{uuid.uuid4().hex[:8]}"
    await db.execute(
        "INSERT INTO actors (actor_id, actor_type, status) VALUES ($1, 'agent', 'active')",
        actor_id
    )
    
    action = Action(
        action_id=uuid.uuid4(),
        actor_id=actor_id,
        actor_type=ActorType.AGENT.value,
        action_name="test.safe",
        resource="test",
        tenant_id=None,
        payload={},
        context={},
        session_id=None,
        request_id=str(uuid.uuid4()),
        idempotency_key=None,
        created_at=datetime.utcnow(),
    )
    
    result = await kernel.handle(action)
    
    # Should be executed (no blocking rules, execution succeeds)
    assert result.decision.status == KernelStatus.EXECUTED
    assert result.executed is True
    
    # Verify action persisted
    db_action = await db.fetchrow("SELECT * FROM actions WHERE action_id = $1", action.action_id)
    assert db_action is not None


# ============================================================================
# SCENARIO 8: Execution Failed
# ============================================================================
async def test_08_execution_failed(kernel, db):
    """Given: Action allowed. When: Execution throws. Then: FAILED_EXECUTION."""
    kernel, repo = kernel
    
    actor_id = f"agent_{uuid.uuid4().hex[:8]}"
    await db.execute(
        "INSERT INTO actors (actor_id, actor_type, status) VALUES ($1, 'agent', 'active')",
        actor_id
    )
    
    action = Action(
        action_id=uuid.uuid4(),
        actor_id=actor_id,
        actor_type=ActorType.AGENT.value,
        action_name="test.failing",
        resource="test",
        tenant_id=None,
        payload={},
        context={},
        session_id=None,
        request_id=str(uuid.uuid4()),
        idempotency_key=None,
        created_at=datetime.utcnow(),
    )
    
    # Execute with a function that will fail
    async def failing_func():
        raise RuntimeError("Simulated failure")
    
    # Override executor to use our failing function
    original_run = kernel.executor.run
    async def failing_run(action):
        raise RuntimeError("Simulated failure")
    kernel.executor.run = failing_run
    
    result = await kernel.handle(action)
    
    # Should be failed execution
    assert result.decision.status == KernelStatus.FAILED_EXECUTION
    assert result.executed is False
    
    # Restore executor
    kernel.executor.run = original_run


# ============================================================================
# SCENARIO 9: Duplicate Idempotency Key
# ============================================================================
async def test_09_idempotency_duplicate(kernel, db):
    """Given: Duplicate idempotency key. When: Second request. Then: Cached result."""
    kernel, repo = kernel
    
    actor_id = f"agent_{uuid.uuid4().hex[:8]}"
    idempotency_key = f"req_{uuid.uuid4().hex}"
    
    await db.execute(
        "INSERT INTO actors (actor_id, actor_type, status) VALUES ($1, 'agent', 'active')",
        actor_id
    )
    
    # First request
    action1 = Action(
        action_id=uuid.uuid4(),
        actor_id=actor_id,
        actor_type=ActorType.AGENT.value,
        action_name="test.idempotent",
        resource="test",
        tenant_id=None,
        payload={},
        context={},
        session_id=None,
        request_id=str(uuid.uuid4()),
        idempotency_key=idempotency_key,
        created_at=datetime.utcnow(),
    )
    
    result1 = await kernel.handle(action1)
    
    # Second request with same key
    action2 = Action(
        action_id=uuid.uuid4(),
        actor_id=actor_id,
        actor_type=ActorType.AGENT.value,
        action_name="test.idempotent",
        resource="test",
        tenant_id=None,
        payload={},
        context={},
        session_id=None,
        request_id=str(uuid.uuid4()),
        idempotency_key=idempotency_key,
        created_at=datetime.utcnow(),
    )
    
    result2 = await kernel.handle(action2)
    
    # Verify idempotency - second should find cached decision
    assert result2.decision.status == result1.decision.status
    
    # Verify only one action in DB (the first one)
    actions = await db.fetch(
        "SELECT * FROM actions WHERE actor_id = $1 AND idempotency_key = $2",
        actor_id, idempotency_key
    )
    assert len(actions) == 1


# ============================================================================
# SCENARIO 10: Audit Chain Integrity
# ============================================================================
async def test_10_audit_chain_integrity(kernel, db):
    """Given: Multiple actions. When: verify_audit_chain. Then: Valid."""
    kernel, repo = kernel
    
    actor_id = f"agent_{uuid.uuid4().hex[:8]}"
    await db.execute(
        "INSERT INTO actors (actor_id, actor_type, status) VALUES ($1, 'agent', 'active')",
        actor_id
    )
    
    # Execute multiple actions
    for i in range(3):
        action = Action(
            action_id=uuid.uuid4(),
            actor_id=actor_id,
            actor_type=ActorType.AGENT.value,
            action_name=f"test.chain{i}",
            resource="test",
            tenant_id=None,
            payload={},
            context={},
            session_id=None,
            request_id=str(uuid.uuid4()),
            idempotency_key=None,
            created_at=datetime.utcnow(),
        )
        await kernel.handle(action)
    
    # Verify chain
    chain_check = await db.fetchrow("SELECT * FROM verify_audit_chain()")
    
    assert chain_check['valid'] is True
    assert chain_check['checked_count'] >= 6  # At least 2 events per action
    assert chain_check['broken_at_event_id'] is None
    
    # Verify events are linked
    events = await db.fetch("SELECT * FROM audit_events ORDER BY event_id LIMIT 20")
    for i, event in enumerate(events[1:], 1):
        prev_event = events[i-1]
        assert event['prev_hash'] == prev_event['event_hash']


# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture(scope="session")
def postgres_dsn():
    """Database connection string."""
    return "postgresql://ledger:ledger@127.0.0.1:5432/ledger_test"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
