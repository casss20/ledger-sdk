"""Tests for execution middleware — Layer 2 enforcement."""

import pytest

from citadel.tokens import (
    CapabilityToken,
    DecisionScope,
    DecisionType,
    GovernanceDecision,
    ExecutionMiddleware,
    TokenVerifier,
    KillSwitch,
)


class MockVault:
    def __init__(self):
        self._tokens = {}
        self._decisions = {}

    async def resolve_token(self, token_id: str, **kwargs):
        return self._tokens.get(token_id)

    async def resolve_decision(self, decision_id: str, **kwargs):
        return self._decisions.get(decision_id)

    def add_token(self, token):
        self._tokens[token.token_id] = {
            "token_id": token.token_id,
            "decision_id": token.decision_id,
            "tenant_id": token.tenant_id,
            "actor_id": token.actor_id,
            "scope_actions": token.scope_actions,
            "scope_resources": token.scope_resources,
            "expiry": token.expiry.isoformat() if token.expiry else None,
        }

    def add_decision(self, decision):
        self._decisions[decision.decision_id] = {
            "decision_id": decision.decision_id,
            "decision_type": decision.decision_type.value,
            "tenant_id": decision.tenant_id,
            "actor_id": decision.actor_id,
            "action": decision.action,
            "scope_actions": decision.scope.actions,
            "scope_resources": decision.scope.resources,
            "expiry": decision.expiry.isoformat() if decision.expiry else None,
            "kill_switch_scope": decision.kill_switch_scope.value,
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
def vault():
    return MockVault()


@pytest.fixture
def middleware(vault, audit_stub):
    ks = KillSwitch(audit_stub)
    verifier = TokenVerifier(vault, ks, audit_stub)
    return ExecutionMiddleware(verifier, audit_stub)


class TestExecutionMiddleware:
    @pytest.mark.asyncio
    async def test_allow_with_valid_token(self, middleware, vault):
        """Valid token allows execution."""
        decision = GovernanceDecision(
            decision_id="gd_allow",
            decision_type=DecisionType.ALLOW,
            tenant_id="tnt_1",
            actor_id="agent_1",
            action="file.read",
            scope=DecisionScope(actions=["file.read"]),
        )
        token = CapabilityToken.derive(decision)
        vault.add_decision(decision)
        vault.add_token(token)

        result = await middleware.check(token.token_id, "file.read")
        assert result.valid is True
        assert result.decision.decision_id == "gd_allow"

    @pytest.mark.asyncio
    async def test_block_with_invalid_token(self, middleware):
        """Invalid token blocks execution."""
        result = await middleware.check("gt_cap_invalid", "file.read")
        assert result.valid is False
        assert result.reason == "token_not_found"

    @pytest.mark.asyncio
    async def test_allow_with_decision_directly(self, middleware):
        """Can pass GovernanceDecision directly instead of token."""
        decision = GovernanceDecision(
            decision_id="gd_direct",
            decision_type=DecisionType.ALLOW,
            tenant_id="tnt_1",
            actor_id="agent_1",
            action="file.read",
            scope=DecisionScope(actions=["file.read"]),
        )

        result = await middleware.check(decision, "file.read")
        assert result.valid is True

    @pytest.mark.asyncio
    async def test_block_expired_decision(self, middleware):
        """Expired decision blocks execution."""
        from datetime import datetime, timezone, timedelta

        decision = GovernanceDecision(
            decision_id="gd_exp",
            decision_type=DecisionType.ALLOW,
            tenant_id="tnt_1",
            actor_id="agent_1",
            action="file.read",
            scope=DecisionScope(actions=["file.read"]),
            expiry=datetime.now(timezone.utc) - timedelta(minutes=1),
        )

        result = await middleware.check(decision, "file.read")
        assert result.valid is False
        assert result.reason == "decision_expired"

    @pytest.mark.asyncio
    async def test_audit_blocked_execution(self, middleware, vault, audit_stub):
        """Blocked execution creates audit event."""
        result = await middleware.check("gt_cap_bad", "file.read")
        assert result.valid is False

        blocked_events = [e for e in audit_stub.events if e.get("event_type") == "execution.blocked"]
        assert len(blocked_events) == 1
