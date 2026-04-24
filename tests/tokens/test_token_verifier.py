"""Tests for token verifier — resolves decisions, checks constraints."""

import pytest

from citadel.tokens import (
    CapabilityToken,
    DecisionScope,
    DecisionType,
    GovernanceDecision,
    KillSwitch,
    KillSwitchScope,
    TokenVerifier,
    VerificationResult,
)


class MockVault:
    """Mock token vault for testing."""

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
def kill_switch(audit_stub):
    return KillSwitch(audit_stub)


@pytest.fixture
def verifier(vault, kill_switch, audit_stub):
    return TokenVerifier(vault, kill_switch, audit_stub)


class TestTokenVerification:
    @pytest.mark.asyncio
    async def test_verify_valid_token(self, verifier, vault):
        """Valid token with active decision passes verification."""
        decision = GovernanceDecision(
            decision_id="gd_valid",
            decision_type=DecisionType.ALLOW,
            tenant_id="tnt_1",
            actor_id="agent_1",
            action="file.read",
            scope=DecisionScope(actions=["file.read"]),
        )
        token = CapabilityToken.derive(decision)

        vault.add_decision(decision)
        vault.add_token(token)

        result = await verifier.verify_token(token.token_id, "file.read")
        assert result.valid is True
        assert result.decision is not None
        assert result.decision.decision_id == "gd_valid"

    @pytest.mark.asyncio
    async def test_verify_token_not_found(self, verifier):
        """Unknown token returns invalid."""
        result = await verifier.verify_token("gt_cap_nonexistent", "file.read")
        assert result.valid is False
        assert result.reason == "token_not_found"

    @pytest.mark.asyncio
    async def test_verify_expired_decision(self, verifier, vault):
        """Token linked to expired decision is invalid."""
        from datetime import datetime, timezone, timedelta

        decision = GovernanceDecision(
            decision_id="gd_expired",
            decision_type=DecisionType.ALLOW,
            tenant_id="tnt_1",
            actor_id="agent_1",
            action="file.read",
            scope=DecisionScope(actions=["file.read"]),
            expiry=datetime.now(timezone.utc) - timedelta(hours=1),
        )
        token = CapabilityToken.derive(decision)

        vault.add_decision(decision)
        vault.add_token(token)

        result = await verifier.verify_token(token.token_id, "file.read")
        assert result.valid is False
        assert result.reason == "decision_expired"

    @pytest.mark.asyncio
    async def test_verify_revoked_decision(self, verifier, vault):
        """Token linked to revoked decision is invalid."""
        decision = GovernanceDecision(
            decision_id="gd_revoked",
            decision_type=DecisionType.ALLOW,
            tenant_id="tnt_1",
            actor_id="agent_1",
            action="file.read",
            scope=DecisionScope(actions=["file.read"]),
        )
        token = CapabilityToken.derive(decision)

        # Store as ALLOW first, then override vault entry to REVOKED
        vault.add_decision(decision)
        vault.add_token(token)
        vault._decisions["gd_revoked"]["decision_type"] = "revoked"

        result = await verifier.verify_token(token.token_id, "file.read")
        assert result.valid is False
        assert result.reason == "decision_revoked"

    @pytest.mark.asyncio
    async def test_verify_scope_mismatch(self, verifier, vault):
        """Token scope that doesn't cover action is invalid."""
        decision = GovernanceDecision(
            decision_id="gd_scope",
            decision_type=DecisionType.ALLOW,
            tenant_id="tnt_1",
            actor_id="agent_1",
            action="file.read",
            scope=DecisionScope(actions=["file.read"]),
        )
        token = CapabilityToken.derive(decision)

        vault.add_decision(decision)
        vault.add_token(token)

        result = await verifier.verify_token(token.token_id, "file.delete")
        assert result.valid is False
        assert result.reason == "scope_mismatch"

    @pytest.mark.asyncio
    async def test_verify_kill_switch_blocks(self, verifier, vault, kill_switch):
        """Active kill switch makes token invalid."""
        decision = GovernanceDecision(
            decision_id="gd_ks",
            decision_type=DecisionType.ALLOW,
            tenant_id="tnt_1",
            actor_id="agent_1",
            action="file.read",
            scope=DecisionScope(actions=["file.read"]),
        )
        token = CapabilityToken.derive(decision)

        vault.add_decision(decision)
        vault.add_token(token)

        await kill_switch.trigger(
            scope=KillSwitchScope.AGENT,
            target_id="agent_1",
            triggered_by="admin",
            triggered_by_type="human",
            reason="Test",
        )

        result = await verifier.verify_token(token.token_id, "file.read")
        assert result.valid is False
        assert result.reason == "kill_switch"


class TestDecisionVerification:
    @pytest.mark.asyncio
    async def test_verify_decision_directly(self, verifier):
        """Can verify a GovernanceDecision without token."""
        decision = GovernanceDecision(
            decision_id="gd_direct",
            decision_type=DecisionType.ALLOW,
            tenant_id="tnt_1",
            actor_id="agent_1",
            action="file.read",
            scope=DecisionScope(actions=["file.read"]),
        )

        result = await verifier.verify_decision(decision, "file.read")
        assert result.valid is True

    @pytest.mark.asyncio
    async def test_verify_decision_expired(self, verifier):
        """Expired decision fails direct verification."""
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

        result = await verifier.verify_decision(decision, "file.read")
        assert result.valid is False
        assert result.reason == "decision_expired"
