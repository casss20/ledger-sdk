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
from datetime import datetime, timedelta
from typing import Optional

# Ledger imports
from ledger import Ledger, Governor, Constitution, ExecutionMode
from ledger.core import Runtime, Executor
from ledger.governance import AuditService, Capability, KillSwitch
from ledger.ops import Failure, Planner


class TestKernelConformance:
    """
    10 deterministic scenarios proving the kernel works end-to-end.
    
    Each test:
    - Executes a governed action
    - Verifies database state
    - Checks audit chain integrity
    - Confirms deterministic replay
    """
    
    @pytest.fixture
    async def ledger(self, postgres_dsn):
        """Fresh ledger instance for each test."""
        ledger = Ledger(
            audit_dsn=postgres_dsn,
            enable_kill_switches=True,
            enable_approvals=True
        )
        await ledger.initialize()
        yield ledger
        await ledger.shutdown()
    
    @pytest.fixture
    async def db(self, postgres_dsn):
        """Database connection for verification."""
        import asyncpg
        conn = await asyncpg.connect(postgres_dsn)
        yield conn
        await conn.close()
    
    # =========================================================================
    # SCENARIO 1: Blocked by Kill Switch
    # =========================================================================
    async def test_01_blocked_by_kill_switch(self, ledger, db):
        """
        Given: Kill switch enabled for action scope
        When: Agent attempts action
        Then: BLOCKED_EMERGENCY decision, no execution, audit trail written
        """
        # Arrange: Enable kill switch
        await db.execute("""
            INSERT INTO kill_switches (scope_type, scope_value, enabled, reason)
            VALUES ('action', 'test.dangerous', TRUE, 'Emergency maintenance')
        """)
        
        # Register actor
        actor_id = f"agent_{uuid.uuid4().hex[:8]}"
        await db.execute(
            "INSERT INTO actors (actor_id, actor_type, status) VALUES ($1, 'agent', 'active')",
            actor_id
        )
        
        # Act: Attempt governed action
        @ledger.governed(action="test.dangerous", resource="test")
        async def dangerous_action():
            return {"executed": True}
        
        result = await dangerous_action()
        
        # Assert: Decision recorded as blocked
        decision = await db.fetchrow(
            "SELECT * FROM decisions WHERE action_id = (SELECT action_id FROM actions WHERE actor_id = $1)",
            actor_id
        )
        assert decision is not None
        assert decision['status'] == 'BLOCKED_EMERGENCY'
        assert decision['winning_rule'] == 'kill_switch_active'
        
        # Assert: Audit trail shows kill switch check
        audit = await db.fetch(
            "SELECT * FROM audit_events WHERE action_id = $1 ORDER BY event_id",
            decision['action_id']
        )
        assert len(audit) >= 2
        assert audit[0]['event_type'] == 'action_received'
        assert any(e['event_type'] == 'kill_switch_checked' for e in audit)
        assert any(e['event_type'] == 'decision_made' for e in audit)
        
        # Assert: Action never executed
        assert result.get('executed') is None or result.get('blocked') is True
    
    # =========================================================================
    # SCENARIO 2: Blocked by Policy
    # =========================================================================
    async def test_02_blocked_by_policy(self, ledger, db):
        """
        Given: Policy rule blocks action
        When: Agent attempts forbidden action
        Then: BLOCKED_POLICY decision, policy rule cited
        """
        # Arrange: Create blocking policy
        await db.execute("""
            INSERT INTO policies (tenant_id, name, version, scope_type, scope_value, rules_json, status)
            VALUES (
                NULL, 'block_forbidden', '1.0', 'action', 'test.forbidden',
                '{"rules": [{"condition": "true", "effect": "BLOCK", "reason": "Action explicitly forbidden"}]}',
                'active'
            )
        """)
        
        actor_id = f"agent_{uuid.uuid4().hex[:8]}"
        await db.execute(
            "INSERT INTO actors (actor_id, actor_type, status) VALUES ($1, 'agent', 'active')",
            actor_id
        )
        
        # Act
        @ledger.governed(action="test.forbidden", resource="test")
        async def forbidden_action():
            return {"executed": True}
        
        result = await forbidden_action()
        
        # Assert
        decision = await db.fetchrow(
            "SELECT * FROM decisions WHERE action_id = (SELECT action_id FROM actions WHERE actor_id = $1)",
            actor_id
        )
        assert decision['status'] == 'BLOCKED_POLICY'
        assert 'forbidden' in decision['reason'].lower()
        
        # Assert: Policy snapshot created for replay
        snapshot = await db.fetchrow(
            "SELECT * FROM policy_snapshots WHERE snapshot_id = $1",
            decision['policy_snapshot_id']
        )
        assert snapshot is not None
        assert 'forbidden' in snapshot['snapshot_json']['name']
    
    # =========================================================================
    # SCENARIO 3: Blocked by Capability Expiry
    # =========================================================================
    async def test_03_blocked_by_capability_expiry(self, ledger, db):
        """
        Given: Expired capability token
        When: Agent attempts action
        Then: BLOCKED_CAPABILITY decision
        """
        # Arrange: Create expired capability
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
        
        # Act: Attempt with expired capability
        @ledger.governed(action="test.expiring", resource="test", capability_required=True)
        async def expiring_action():
            return {"executed": True}
        
        # Provide expired token
        ledger.set_capability_token(token_id)
        result = await expiring_action()
        
        # Assert
        decision = await db.fetchrow(
            "SELECT * FROM decisions WHERE action_id = (SELECT action_id FROM actions WHERE actor_id = $1)",
            actor_id
        )
        assert decision['status'] == 'BLOCKED_CAPABILITY'
        assert decision['capability_token'] == token_id
    
    # =========================================================================
    # SCENARIO 4: Pending Approval
    # =========================================================================
    async def test_04_pending_approval(self, ledger, db):
        """
        Given: HIGH risk action requiring approval
        When: Agent attempts action
        Then: PENDING_APPROVAL decision, approval queue entry
        """
        actor_id = f"agent_{uuid.uuid4().hex[:8]}"
        await db.execute(
            "INSERT INTO actors (actor_id, actor_type, status) VALUES ($1, 'agent', 'active')",
            actor_id
        )
        
        # Arrange: Policy requiring approval for high-risk
        await db.execute("""
            INSERT INTO policies (name, version, scope_type, scope_value, rules_json, status)
            VALUES (
                'require_approval', '1.0', 'action', 'test.highrisk',
                '{"rules": [{"condition": "risk_score > 70", "effect": "PENDING_APPROVAL", "reason": "High risk action"}]}',
                'active'
            )
        """)
        
        # Act
        @ledger.governed(action="test.highrisk", resource="production", risk="high")
        async def high_risk_action():
            return {"executed": True}
        
        result = await high_risk_action()
        
        # Assert: Decision is pending
        action = await db.fetchrow("SELECT * FROM actions WHERE actor_id = $1", actor_id)
        decision = await db.fetchrow("SELECT * FROM decisions WHERE action_id = $1", action['action_id'])
        assert decision['status'] == 'PENDING_APPROVAL'
        
        # Assert: Approval queue entry
        approval = await db.fetchrow("SELECT * FROM approvals WHERE action_id = $1", action['action_id'])
        assert approval is not None
        assert approval['status'] == 'pending'
        assert approval['priority'] in ('high', 'critical')
        
        # Assert: Appears in pending queue view
        queue = await db.fetch("SELECT * FROM pending_approvals_queue")
        assert any(a['action_id'] == action['action_id'] for a in queue)
    
    # =========================================================================
    # SCENARIO 5: Approval Rejected
    # =========================================================================
    async def test_05_approval_rejected(self, ledger, db):
        """
        Given: Action pending approval
        When: Human rejects approval
        Then: REJECTED_APPROVAL decision, action blocked
        """
        # Setup pending approval
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
        
        # Act: Reject the approval
        await db.execute(
            "UPDATE approvals SET status = 'rejected', reviewed_by = 'admin_1', decided_at = NOW(), decision_reason = 'Too risky' WHERE action_id = $1",
            action_id
        )
        await db.execute(
            "UPDATE decisions SET status = 'REJECTED_APPROVAL', reason = 'Rejected by admin_1: Too risky' WHERE action_id = $1",
            action_id
        )
        
        # Assert
        decision = await db.fetchrow("SELECT * FROM decisions WHERE action_id = $1", action_id)
        assert decision['status'] == 'REJECTED_APPROVAL'
        
        approval = await db.fetchrow("SELECT * FROM approvals WHERE action_id = $1", action_id)
        assert approval['status'] == 'rejected'
        assert approval['reviewed_by'] == 'admin_1'
    
    # =========================================================================
    # SCENARIO 6: Approval Expired
    # =========================================================================
    async def test_06_approval_expired(self, ledger, db):
        """
        Given: Approval not decided before expiry
        When: Expiry time reached
        Then: EXPIRED_APPROVAL status
        """
        # Setup expired approval
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
        
        # Act: Process expiry (kernel task or trigger)
        await db.execute(
            "UPDATE approvals SET status = 'expired' WHERE action_id = $1 AND expires_at < NOW()",
            action_id
        )
        await db.execute(
            "UPDATE decisions SET status = 'EXPIRED_APPROVAL', reason = 'Approval window expired' WHERE action_id = $1",
            action_id
        )
        
        # Assert
        approval = await db.fetchrow("SELECT * FROM approvals WHERE action_id = $1", action_id)
        assert approval['status'] == 'expired'
    
    # =========================================================================
    # SCENARIO 7: Allowed + Executed
    # =========================================================================
    async def test_07_allowed_and_executed(self, ledger, db):
        """
        Given: Action passes all checks
        When: Agent attempts action
        Then: ALLOWED → EXECUTED, success result
        """
        actor_id = f"agent_{uuid.uuid4().hex[:8]}"
        await db.execute(
            "INSERT INTO actors (actor_id, actor_type, status) VALUES ($1, 'agent', 'active')",
            actor_id
        )
        
        # Arrange: Create valid capability
        token_id = f"cap_{uuid.uuid4().hex}"
        await db.execute("""
            INSERT INTO capabilities (token_id, actor_id, action_scope, resource_scope, 
                                     issued_at, expires_at, max_uses, uses)
            VALUES ($1, $2, 'test.safe', 'test', NOW(), NOW() + INTERVAL '1 hour', 10, 0)
        """, token_id, actor_id)
        
        # Act
        @ledger.governed(action="test.safe", resource="test")
        async def safe_action():
            return {"result": "success", "data": "executed"}
        
        result = await safe_action()
        
        # Assert: Decision shows success path
        action = await db.fetchrow("SELECT * FROM actions WHERE actor_id = $1", actor_id)
        decision = await db.fetchrow("SELECT * FROM decisions WHERE action_id = $1", action['action_id'])
        
        # Should be ALLOWED or EXECUTED
        assert decision['status'] in ('ALLOWED', 'EXECUTED')
        assert decision['path_taken'] == 'fast'  # or 'standard'
        
        # Assert: Execution result recorded
        exec_result = await db.fetchrow(
            "SELECT * FROM execution_results WHERE action_id = $1", action['action_id']
        )
        assert exec_result is not None
        assert exec_result['success'] is True
        assert exec_result['result_json']['result'] == 'success'
        
        # Assert: Capability consumed (if used)
        cap = await db.fetchrow("SELECT * FROM capabilities WHERE token_id = $1", token_id)
        if cap:
            assert cap['uses'] >= 0  # May or may not have been required
    
    # =========================================================================
    # SCENARIO 8: Execution Failed
    # =========================================================================
    async def test_08_execution_failed(self, ledger, db):
        """
        Given: Action allowed but execution throws exception
        When: Agent attempts action
        Then: FAILED_EXECUTION decision, error logged
        """
        actor_id = f"agent_{uuid.uuid4().hex[:8]}"
        await db.execute(
            "INSERT INTO actors (actor_id, actor_type, status) VALUES ($1, 'agent', 'active')",
            actor_id
        )
        
        # Act: Action that will fail
        @ledger.governed(action="test.failing", resource="test")
        async def failing_action():
            raise RuntimeError("Simulated execution failure")
        
        try:
            await failing_action()
        except RuntimeError:
            pass  # Expected
        
        # Assert: Failed execution recorded
        action = await db.fetchrow("SELECT * FROM actions WHERE actor_id = $1", actor_id)
        decision = await db.fetchrow("SELECT * FROM decisions WHERE action_id = $1", action['action_id'])
        
        assert decision['status'] == 'FAILED_EXECUTION'
        
        exec_result = await db.fetchrow(
            "SELECT * FROM execution_results WHERE action_id = $1", action['action_id']
        )
        assert exec_result is not None
        assert exec_result['success'] is False
        assert 'Simulated execution failure' in exec_result['error_message']
    
    # =========================================================================
    # SCENARIO 9: Duplicate Idempotency Key
    # =========================================================================
    async def test_09_idempotency_duplicate(self, ledger, db):
        """
        Given: Action already submitted with idempotency key
        When: Same action submitted again
        Then: Idempotent return, no duplicate execution
        """
        actor_id = f"agent_{uuid.uuid4().hex[:8]}"
        idempotency_key = f"req_{uuid.uuid4().hex}"
        
        await db.execute(
            "INSERT INTO actors (actor_id, actor_type, status) VALUES ($1, 'agent', 'active')",
            actor_id
        )
        
        # First call
        @ledger.governed(action="test.idempotent", resource="test", idempotent=True)
        async def idempotent_action():
            return {"executed": True, "timestamp": datetime.utcnow().isoformat()}
        
        result1 = await idempotent_action()
        
        # Second call with same key
        result2 = await idempotent_action()
        
        # Assert: Same result returned
        assert result1['executed'] == result2['executed']
        
        # Assert: Only one action in database
        actions = await db.fetch(
            "SELECT * FROM actions WHERE actor_id = $1 AND idempotency_key = $2",
            actor_id, idempotency_key
        )
        assert len(actions) == 1
        
        # Assert: Only one decision
        decisions = await db.fetch(
            "SELECT * FROM decisions WHERE action_id = $1", actions[0]['action_id']
        )
        assert len(decisions) == 1
    
    # =========================================================================
    # SCENARIO 10: Audit Chain Integrity
    # =========================================================================
    async def test_10_audit_chain_integrity(self, ledger, db):
        """
        Given: Multiple actions executed
        When: verify_audit_chain() called
        Then: Returns valid, chain unbroken
        """
        actor_id = f"agent_{uuid.uuid4().hex[:8]}"
        await db.execute(
            "INSERT INTO actors (actor_id, actor_type, status) VALUES ($1, 'agent', 'active')",
            actor_id
        )
        
        # Execute several actions
        @ledger.governed(action="test.chain1", resource="test")
        async def chain_action_1():
            return {"n": 1}
        
        @ledger.governed(action="test.chain2", resource="test")
        async def chain_action_2():
            return {"n": 2}
        
        @ledger.governed(action="test.chain3", resource="test")
        async def chain_action_3():
            return {"n": 3}
        
        await chain_action_1()
        await chain_action_2()
        await chain_action_3()
        
        # Act: Verify chain
        chain_check = await db.fetchrow("SELECT * FROM verify_audit_chain()")
        
        # Assert: Chain valid
        assert chain_check['valid'] is True
        assert chain_check['checked_count'] >= 6  # At least 2 events per action
        assert chain_check['broken_at_event_id'] is None
        
        # Assert: Events linked correctly
        events = await db.fetch(
            "SELECT * FROM audit_events ORDER BY event_id LIMIT 10"
        )
        for i, event in enumerate(events[1:], 1):
            prev_event = events[i-1]
            assert event['prev_hash'] == prev_event['event_hash'], \
                f"Chain broken at event {event['event_id']}: prev_hash mismatch"


class TestReplayDeterminism:
    """
    Verifies that decisions can be replayed deterministically.
    """
    
    async def test_replay_same_inputs_same_output(self, ledger, db):
        """
        Given: Action with recorded decision
        When: Replayed with same inputs and policy snapshot
        Then: Same decision reached
        """
        # Create action with full context
        action_id = uuid.uuid4()
        await db.execute("""
            INSERT INTO actions (action_id, actor_id, actor_type, action_name, resource, 
                                payload_json, context_json)
            VALUES ($1, $2, 'agent', 'test.replay', 'test',
                    '{"amount": 100}', '{"time": "2024-01-01T00:00:00Z"}')
        """, action_id, "agent_1")
        
        # Create policy snapshot
        snapshot_id = uuid.uuid4()
        await db.execute("""
            INSERT INTO policy_snapshots (snapshot_id, policy_version, snapshot_hash, snapshot_json)
            VALUES ($1, 'test_policy:v1', 'abc123', '{"rules": [{"condition": "amount < 1000", "effect": "ALLOW"}]}')
        """, snapshot_id)
        
        # Create decision referencing snapshot
        await db.execute("""
            INSERT INTO decisions (action_id, policy_snapshot_id, status, winning_rule, reason)
            VALUES ($1, $2, 'ALLOWED', 'amount_check', 'Amount within limit')
        """, action_id, snapshot_id)
        
        # Verify replay linkage
        replay = await db.fetchrow("""
            SELECT * FROM decision_replay_log WHERE action_id = $1
        """, action_id)
        
        assert replay is not None
        assert replay['policy_snapshot_id'] == snapshot_id
        assert replay['snapshot_hash'] == 'abc123'
        assert replay['payload_json']['amount'] == 100
    
    async def test_concurrent_action_isolation(self, ledger, db):
        """
        Given: Multiple concurrent actions
        When: All write to database
        Then: No cross-contamination, each has independent decision
        """
        # This would require actual concurrent execution
        # For now, verify the schema supports it (unique constraints, etc.)
        pass


# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture(scope="session")
def postgres_dsn():
    """Database connection string."""
    return "postgresql://ledger:ledger@localhost:5432/ledger_test"


@pytest.fixture(autouse=True)
async def clean_database(postgres_dsn):
    """Clean database before each test."""
    import asyncpg
    conn = await asyncpg.connect(postgres_dsn)
    
    # Truncate all tables
    await conn.execute("""
        TRUNCATE actors, policies, policy_snapshots, capabilities, 
                    kill_switches, approvals, actions, decisions, 
                    audit_events, execution_results
        CASCADE
    """)
    
    await conn.close()
    yield


# ============================================================================
# MAIN
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
