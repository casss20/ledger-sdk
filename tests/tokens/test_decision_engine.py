"""Tests for decision engine — produces GovernanceDecisions."""

import pytest

from ledger.tokens import (
    DecisionEngine,
    DecisionType,
    KillSwitch,
    KillSwitchScope,
)


class MockPolicyBackend:
    """Mock policy backend for testing."""

    def __init__(self, allowed=True, reason="policy match"):
        self.allowed = allowed
        self.reason = reason

    async def evaluate(self, action: str, context: dict) -> dict:
        return {
            "allowed": self.allowed,
            "reason": self.reason,
            "scope": {"actions": [action], "resources": []},
            "constraints": {},
        }


class MockAudit:
    def __init__(self):
        self.events = []

    async def record(self, **kwargs):
        self.events.append(kwargs)


@pytest.fixture
def audit_stub():
    return MockAudit()


@pytest.fixture
def kill_switch(audit_stub):
    return KillSwitch(audit_stub)


class TestDecisionEngine:
    @pytest.mark.asyncio
    async def test_allow_decision(self, audit_stub, kill_switch):
        """Policy allowing action produces ALLOW decision."""
        policies = MockPolicyBackend(allowed=True)
        engine = DecisionEngine(policies, audit_stub, kill_switch)

        decision = await engine.decide(
            action="file.read",
            context={},
            tenant_id="tnt_1",
            actor_id="agent_1",
        )

        assert decision.decision_type == DecisionType.ALLOW
        assert decision.action == "file.read"
        assert decision.tenant_id == "tnt_1"
        assert decision.decision_id.startswith("gd_")
        assert decision.is_active is True

    @pytest.mark.asyncio
    async def test_deny_decision(self, audit_stub, kill_switch):
        """Policy denying action produces DENY decision."""
        policies = MockPolicyBackend(allowed=False, reason="Forbidden")
        engine = DecisionEngine(policies, audit_stub, kill_switch)

        decision = await engine.decide(
            action="file.delete",
            context={},
            tenant_id="tnt_1",
            actor_id="agent_1",
        )

        assert decision.decision_type == DecisionType.DENY
        assert decision.reason == "Forbidden"
        assert decision.is_active is False

    @pytest.mark.asyncio
    async def test_kill_switch_produces_deny(self, audit_stub, kill_switch):
        """Active kill switch produces DENY regardless of policy."""
        policies = MockPolicyBackend(allowed=True)
        engine = DecisionEngine(policies, audit_stub, kill_switch)

        await kill_switch.trigger(
            scope=KillSwitchScope.AGENT,
            target_id="agent_1",
            triggered_by="admin",
            triggered_by_type="human",
            reason="Emergency",
        )

        decision = await engine.decide(
            action="file.read",
            context={},
            tenant_id="tnt_1",
            actor_id="agent_1",
        )

        assert decision.decision_type == DecisionType.DENY
        assert "Kill switch active" in decision.reason

    @pytest.mark.asyncio
    async def test_decision_has_expiry(self, audit_stub, kill_switch):
        """ALLOW decisions have expiry based on TTL."""
        policies = MockPolicyBackend(allowed=True)
        engine = DecisionEngine(policies, audit_stub, kill_switch, default_ttl_seconds=3600)

        decision = await engine.decide(
            action="file.read",
            context={},
            tenant_id="tnt_1",
            actor_id="agent_1",
        )

        assert decision.expiry is not None
        assert decision.is_expired is False

    @pytest.mark.asyncio
    async def test_audit_records_decision(self, audit_stub, kill_switch):
        """Each decision is audited."""
        policies = MockPolicyBackend(allowed=True)
        engine = DecisionEngine(policies, audit_stub, kill_switch)

        await engine.decide(
            action="file.read",
            context={"request_id": "req_1"},
            tenant_id="tnt_1",
            actor_id="agent_1",
        )

        decision_events = [e for e in audit_stub.events if e.get("event_type") == "governance.decision"]
        assert len(decision_events) == 1
        assert decision_events[0]["data"]["action"] == "file.read"
