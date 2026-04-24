"""Tests for decision-centric governance architecture."""

import uuid
from datetime import datetime, timezone, timedelta

import pytest

from CITADEL.tokens import (
    CapabilityToken,
    DecisionScope,
    DecisionType,
    GovernanceDecision,
    KillSwitch,
    KillSwitchCheck,
    KillSwitchRecord,
    KillSwitchScope,
)


class TestGovernanceDecision:
    def test_decision_creation(self):
        """GovernanceDecision is first-class with all required fields."""
        d = GovernanceDecision(
            decision_id="gd_test_123",
            decision_type=DecisionType.ALLOW,
            tenant_id="tnt_1",
            actor_id="agent_1",
            action="file.read",
            scope=DecisionScope(actions=["file.read"], resources=["/tmp/*"]),
            reason="Policy match",
        )
        assert d.decision_id == "gd_test_123"
        assert d.decision_type == DecisionType.ALLOW
        assert d.is_active is True
        assert d.is_expired is False

    def test_expired_decision(self):
        """Decision with past expiry is not active."""
        d = GovernanceDecision(
            decision_id="gd_expired",
            decision_type=DecisionType.ALLOW,
            tenant_id="tnt_1",
            actor_id="agent_1",
            action="file.read",
            scope=DecisionScope(),
            expiry=datetime.now(timezone.utc) - timedelta(hours=1),
        )
        assert d.is_expired is True
        assert d.is_active is False

    def test_revoked_decision(self):
        """Revoked decision is not active even if not expired."""
        d = GovernanceDecision(
            decision_id="gd_revoked",
            decision_type=DecisionType.REVOKED,
            tenant_id="tnt_1",
            actor_id="agent_1",
            action="file.read",
            scope=DecisionScope(),
        )
        assert d.is_active is False

    def test_scope_coverage(self):
        """Scope correctly covers actions and resources."""
        scope = DecisionScope(
            actions=["file.read", "file.write"],
            resources=["/tmp/*", "/data/*"],
        )
        assert scope.covers("file.read") is True
        assert scope.covers("file.delete") is False
        assert scope.covers("file.read", "/tmp/test") is True
        assert scope.covers("file.read", "/etc/passwd") is False


class TestCapabilityToken:
    def test_token_derived_from_allow_decision(self):
        """Token can be derived from ALLOW decision."""
        decision = GovernanceDecision(
            decision_id="gd_allow_1",
            decision_type=DecisionType.ALLOW,
            tenant_id="tnt_1",
            actor_id="agent_1",
            action="file.read",
            scope=DecisionScope(actions=["file.read"]),
        )
        token = CapabilityToken.derive(decision)
        assert token.token_id.startswith("gt_cap_")
        assert token.decision_id == decision.decision_id
        assert token.scope_actions == ["file.read"]

    def test_token_not_derived_from_deny(self):
        """Cannot derive token from DENY decision."""
        decision = GovernanceDecision(
            decision_id="gd_deny_1",
            decision_type=DecisionType.DENY,
            tenant_id="tnt_1",
            actor_id="agent_1",
            action="file.delete",
            scope=DecisionScope(),
        )
        with pytest.raises(ValueError, match="Cannot derive token"):
            CapabilityToken.derive(decision)

    def test_token_chain_hash(self):
        """Token chain hash links to previous token."""
        decision = GovernanceDecision(
            decision_id="gd_allow_2",
            decision_type=DecisionType.ALLOW,
            tenant_id="tnt_1",
            actor_id="agent_1",
            action="file.read",
            scope=DecisionScope(),
        )
        token1 = CapabilityToken.derive(decision)
        token2 = CapabilityToken.derive(decision, previous_hash=token1.chain_hash)
        assert token2.chain_hash != token2.content_hash if hasattr(token2, 'content_hash') else True
        assert token2.chain_hash != token1.chain_hash


class TestKillSwitch:
    @pytest.fixture
    def audit_stub(self):
        class AuditStub:
            async def record(self, **kwargs):
                pass
        return AuditStub()

    @pytest.mark.asyncio
    async def test_trigger_agent_scope(self, audit_stub):
        """Kill switch at agent scope blocks that agent."""
        ks = KillSwitch(audit_stub)
        record = await ks.trigger(
            scope=KillSwitchScope.AGENT,
            target_id="agent_1",
            triggered_by="admin",
            triggered_by_type="human",
            reason="Anomalous behavior",
        )
        assert record.scope == KillSwitchScope.AGENT
        assert record.target_id == "agent_1"

    @pytest.mark.asyncio
    async def test_check_blocks_affected_agent(self, audit_stub):
        """Check returns active for agent under kill switch."""
        ks = KillSwitch(audit_stub)
        await ks.trigger(
            scope=KillSwitchScope.AGENT,
            target_id="agent_1",
            triggered_by="admin",
            triggered_by_type="human",
            reason="Test",
        )
        result = await ks.check(actor_id="agent_1", tenant_id="tnt_1")
        assert result.active is True
        assert result.record is not None

    @pytest.mark.asyncio
    async def test_check_allows_unaffected_agent(self, audit_stub):
        """Check returns inactive for agent not under kill switch."""
        ks = KillSwitch(audit_stub)
        await ks.trigger(
            scope=KillSwitchScope.AGENT,
            target_id="agent_1",
            triggered_by="admin",
            triggered_by_type="human",
            reason="Test",
        )
        result = await ks.check(actor_id="agent_2", tenant_id="tnt_1")
        assert result.active is False

    @pytest.mark.asyncio
    async def test_tenant_scope_blocks_all(self, audit_stub):
        """Tenant kill switch blocks all agents in tenant."""
        ks = KillSwitch(audit_stub)
        await ks.trigger(
            scope=KillSwitchScope.TENANT,
            target_id="tnt_1",
            triggered_by="admin",
            triggered_by_type="human",
            reason="Emergency",
        )
        result = await ks.check(actor_id="agent_99", tenant_id="tnt_1")
        assert result.active is True

    @pytest.mark.asyncio
    async def test_global_scope_blocks_everything(self, audit_stub):
        """Global kill switch blocks all agents everywhere."""
        ks = KillSwitch(audit_stub)
        await ks.trigger(
            scope=KillSwitchScope.GLOBAL,
            target_id="*",
            triggered_by="admin",
            triggered_by_type="human",
            reason="Critical",
        )
        result = await ks.check(actor_id="any_agent", tenant_id="any_tenant")
        assert result.active is True

    @pytest.mark.asyncio
    async def test_release_kill_switch(self, audit_stub):
        """Releasing kill switch allows operations again."""
        ks = KillSwitch(audit_stub)
        await ks.trigger(
            scope=KillSwitchScope.AGENT,
            target_id="agent_1",
            triggered_by="admin",
            triggered_by_type="human",
            reason="Test",
        )
        released = await ks.release(
            scope=KillSwitchScope.AGENT,
            target_id="agent_1",
            released_by="admin",
            reason="Resolved",
        )
        assert released is True
        result = await ks.check(actor_id="agent_1", tenant_id="tnt_1")
        assert result.active is False


class TestDecisionScope:
    def test_scope_actions(self):
        """Scope covers listed actions."""
        scope = DecisionScope(actions=["read", "write"])
        assert scope.covers("read") is True
        assert scope.covers("delete") is False

    def test_scope_resources(self):
        """Scope covers listed resources."""
        scope = DecisionScope(actions=["read"], resources=["/tmp/*"])
        assert scope.covers("read", "/tmp/*") is True
        assert scope.covers("read", "/etc/*") is False

    def test_empty_scope_allows_nothing(self):
        """Empty scope denies everything."""
        scope = DecisionScope()
        assert scope.covers("anything") is False
