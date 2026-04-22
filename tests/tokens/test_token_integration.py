"""Integration tests: gt_ tokens connected to policy/audit/approval flows."""

import uuid

import pytest

from ledger.tokens import GovernanceToken, TokenType


class TestPolicyDecisionCreatesToken:
    def test_policy_evaluation_produces_token(self):
        """Policy decision creates a gt_ token with correct type."""
        trace = {
            "action": {"name": "file.write", "params": {"path": "/tmp/test"}},
            "policy_result": {"allowed": True},
            "policies_evaluated": ["p1", "p2"],
        }
        token = GovernanceToken.generate(
            token_type=TokenType.POLICY_DECISION,
            tenant_id="tnt_test",
            decision_trace=trace,
            agent_id="agent_123",
        )
        assert token.token_type == TokenType.POLICY_DECISION
        assert token.agent_id == "agent_123"
        assert token.decision_trace["policies_evaluated"] == ["p1", "p2"]


class TestApprovalCreatesToken:
    def test_approval_produces_token(self):
        """Human approval creates a gt_ token."""
        trace = {
            "action": "file.delete",
            "approved_by": "user@example.com",
            "approval_reason": "Cleanup task",
        }
        token = GovernanceToken.generate(
            token_type=TokenType.APPROVAL,
            tenant_id="tnt_test",
            decision_trace=trace,
        )
        assert token.token_type == TokenType.APPROVAL
        assert token.content_hash is not None


class TestAuditEventCreatesToken:
    def test_audit_event_produces_token(self):
        """Audit event creates a gt_ token."""
        trace = {
            "event_type": "action.executed",
            "action_id": "act_123",
            "outcome": "success",
        }
        token = GovernanceToken.generate(
            token_type=TokenType.AUDIT_EVENT,
            tenant_id="tnt_test",
            decision_trace=trace,
        )
        assert token.token_type == TokenType.AUDIT_EVENT
        assert token.token_id.startswith("gt_aud_")


class TestKillSwitchCreatesToken:
    def test_kill_switch_produces_token(self):
        """Kill switch activation creates a gt_ token."""
        trace = {
            "scope": "agent",
            "target_id": "agent_123",
            "triggered_by": "admin@example.com",
            "reason": "Anomalous behavior detected",
        }
        token = GovernanceToken.generate(
            token_type=TokenType.KILL_SWITCH,
            tenant_id="tnt_test",
            decision_trace=trace,
        )
        assert token.token_type == TokenType.KILL_SWITCH
        assert token.token_id.startswith("gt_kil_")


class TestTokensChainAcrossActions:
    def test_chain_links_multiple_actions(self):
        """Multiple tokens form a verifiable chain."""
        tenant = str(uuid.uuid4())

        # First action
        t1 = GovernanceToken.generate(
            token_type=TokenType.AUDIT_EVENT,
            tenant_id=tenant,
            decision_trace={"seq": 1},
        )

        # Second action links to first
        t2 = GovernanceToken.generate(
            token_type=TokenType.AUDIT_EVENT,
            tenant_id=tenant,
            decision_trace={"seq": 2},
            previous_hash=t1.chain_hash,
        )

        # Third action links to second
        t3 = GovernanceToken.generate(
            token_type=TokenType.POLICY_DECISION,
            tenant_id=tenant,
            decision_trace={"seq": 3},
            previous_hash=t2.chain_hash,
        )

        # Verify chain is different for each
        assert t1.chain_hash == t1.content_hash  # Genesis
        assert t2.chain_hash != t2.content_hash  # Has previous
        assert t3.chain_hash != t3.content_hash  # Has previous

        # Verify hashes are unique
        hashes = [t1.chain_hash, t2.chain_hash, t3.chain_hash]
        assert len(set(hashes)) == 3
