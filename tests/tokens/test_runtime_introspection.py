"""Decision-first capability issuance and runtime introspection tests."""

from datetime import datetime, timedelta, timezone

import pytest

from citadel.tokens import (
    CapabilityToken,
    DecisionScope,
    DecisionType,
    GovernanceDecision,
    TokenVerifier,
)


class MemoryVault:
    def __init__(self):
        self.decisions = {}
        self.tokens = {}
        self.kill_switch = None
        self.store_order = []
        self.fail_decision_store = False

    async def store_decision(self, decision):
        if self.fail_decision_store:
            raise RuntimeError("decision store failed")
        self.store_order.append("decision")
        self.decisions[decision.decision_id] = {
            "decision_id": decision.decision_id,
            "decision_type": decision.decision_type.value,
            "tenant_id": decision.tenant_id,
            "actor_id": decision.actor_id,
            "request_id": decision.request_id,
            "trace_id": decision.trace_id,
            "workspace_id": decision.workspace_id,
            "agent_id": decision.agent_id,
            "subject_type": decision.subject_type,
            "subject_id": decision.subject_id,
            "action": decision.action,
            "resource": decision.resource,
            "risk_level": decision.risk_level,
            "policy_version": decision.policy_version,
            "approval_state": decision.approval_state,
            "approved_by": decision.approved_by,
            "approved_at": decision.approved_at,
            "issued_token_id": decision.issued_token_id,
            "expires_at": decision.expiry,
            "revoked_at": decision.revoked_at,
            "revoked_reason": decision.revoked_reason,
            "scope_actions": decision.scope.actions,
            "scope_resources": decision.scope.resources,
            "constraints": decision.constraints,
            "expiry": decision.expiry,
            "kill_switch_scope": decision.kill_switch_scope.value,
            "created_at": decision.created_at,
            "reason": decision.reason,
        }

    async def store_token(self, token):
        self.store_order.append("token")
        self.tokens[token.token_id] = {
            "token_id": token.token_id,
            "decision_id": token.decision_id,
            "tenant_id": token.tenant_id,
            "actor_id": token.actor_id,
            "iss": token.iss,
            "subject": token.subject,
            "audience": token.audience,
            "workspace_id": token.workspace_id,
            "tool": token.tool,
            "action": token.action,
            "resource_scope": token.resource_scope,
            "risk_level": token.risk_level,
            "not_before": token.not_before,
            "trace_id": token.trace_id,
            "approval_ref": token.approval_ref,
            "revoked_at": token.revoked_at if hasattr(token, "revoked_at") else None,
            "revoked_reason": None,
            "scope_actions": token.scope_actions,
            "scope_resources": token.scope_resources,
            "expiry": token.expiry,
            "created_at": token.created_at,
            "chain_hash": token.chain_hash,
        }

    async def issue_token_for_decision(self, decision, **kwargs):
        await self.store_decision(decision)
        token = CapabilityToken.derive(decision, **kwargs)
        await self.store_token(token)
        self.decisions[decision.decision_id]["issued_token_id"] = token.token_id
        return token

    async def resolve_token(self, token_id, tenant_id=None):
        return self.tokens.get(token_id)

    async def resolve_decision(self, decision_id, tenant_id=None):
        return self.decisions.get(decision_id)

    async def check_kill_switch(self, **kwargs):
        return self.kill_switch


class MemoryAudit:
    def __init__(self):
        self.events = []

    async def record_token_verification(self, **kwargs):
        self.events.append({"event_type": "token.verification", **kwargs})


def decision(**overrides):
    defaults = dict(
        decision_id="gd_runtime_1",
        decision_type=DecisionType.ALLOW,
        tenant_id="ws_prod_01",
        workspace_id="ws_prod_01",
        actor_id="agent:payments-01",
        agent_id="agent:payments-01",
        subject_type="agent",
        subject_id="agent:payments-01",
        action="stripe.refund.create",
        resource="customer:2841",
        risk_level="critical",
        policy_version="policy_2026_04_24_7",
        approval_state="approved",
        approved_by="operator:admin",
        approved_at=datetime.now(timezone.utc),
        trace_id="trace_123",
        request_id="req_123",
        scope=DecisionScope(
            actions=["stripe.refund.create"],
            resources=["customer:2841"],
        ),
        constraints={"tool": "stripe"},
    )
    defaults.update(overrides)
    return GovernanceDecision(**defaults)


@pytest.mark.asyncio
async def test_decision_is_persisted_before_token_issuance():
    vault = MemoryVault()
    token = await vault.issue_token_for_decision(decision(), lifetime_seconds=120)

    assert vault.store_order == ["decision", "token"]
    assert token.decision_id == "gd_runtime_1"
    assert vault.decisions["gd_runtime_1"]["issued_token_id"] == token.token_id


@pytest.mark.asyncio
async def test_token_issuance_fails_if_decision_persistence_fails():
    vault = MemoryVault()
    vault.fail_decision_store = True

    with pytest.raises(RuntimeError):
        await vault.issue_token_for_decision(decision(), lifetime_seconds=120)

    assert vault.tokens == {}


async def introspect(vault, token_id, **overrides):
    audit = MemoryAudit()
    verifier = TokenVerifier(vault, audit_logger=audit)
    result = await verifier.introspect_token(
        token_id,
        overrides.get("action", "stripe.refund.create"),
        overrides.get("resource", "customer:2841"),
        overrides.get("workspace", "ws_prod_01"),
        {
            "tenant_id": "ws_prod_01",
            "workspace_id": overrides.get("workspace", "ws_prod_01"),
            "tool": "stripe",
        },
    )
    return result, audit


@pytest.mark.asyncio
async def test_introspection_active_for_valid_scoped_token():
    vault = MemoryVault()
    token = await vault.issue_token_for_decision(decision(), lifetime_seconds=120, tool="stripe")

    result, _ = await introspect(vault, token.token_id)

    assert result.active is True
    assert result.decision.decision_id == token.decision_id
    assert result.decision.policy_version == "policy_2026_04_24_7"
    assert result.decision.approval_state == "approved"


@pytest.mark.asyncio
async def test_introspection_inactive_for_expired_token():
    vault = MemoryVault()
    token = await vault.issue_token_for_decision(decision(), lifetime_seconds=120, tool="stripe")
    vault.tokens[token.token_id]["expiry"] = datetime.now(timezone.utc) - timedelta(seconds=1)

    result, _ = await introspect(vault, token.token_id)

    assert result.active is False
    assert result.reason == "token_expired"


@pytest.mark.asyncio
async def test_introspection_inactive_for_revoked_token():
    vault = MemoryVault()
    token = await vault.issue_token_for_decision(decision(), lifetime_seconds=120, tool="stripe")
    vault.tokens[token.token_id]["revoked_at"] = datetime.now(timezone.utc)

    result, _ = await introspect(vault, token.token_id)

    assert result.active is False
    assert result.reason == "token_revoked"


@pytest.mark.asyncio
async def test_introspection_inactive_after_kill_switch_activation():
    vault = MemoryVault()
    token = await vault.issue_token_for_decision(decision(), lifetime_seconds=120, tool="stripe")
    vault.kill_switch = {"scope_type": "tenant", "reason": "emergency stop"}

    result, _ = await introspect(vault, token.token_id)

    assert result.active is False
    assert result.reason == "kill_switch_active"
    assert result.kill_switch is True


@pytest.mark.asyncio
async def test_introspection_inactive_when_action_does_not_match():
    vault = MemoryVault()
    token = await vault.issue_token_for_decision(decision(), lifetime_seconds=120, tool="stripe")

    result, _ = await introspect(vault, token.token_id, action="stripe.charge.create")

    assert result.active is False
    assert result.reason == "scope_mismatch"


@pytest.mark.asyncio
async def test_introspection_inactive_when_resource_does_not_match():
    vault = MemoryVault()
    token = await vault.issue_token_for_decision(decision(), lifetime_seconds=120, tool="stripe")

    result, _ = await introspect(vault, token.token_id, resource="customer:9999")

    assert result.active is False
    assert result.reason == "scope_mismatch"


@pytest.mark.asyncio
async def test_introspection_inactive_when_workspace_does_not_match():
    vault = MemoryVault()
    token = await vault.issue_token_for_decision(decision(), lifetime_seconds=120, tool="stripe")

    result, _ = await introspect(vault, token.token_id, workspace="ws_other")

    assert result.active is False
    assert result.reason == "workspace_mismatch"


@pytest.mark.asyncio
async def test_audit_records_join_back_to_decision_id():
    vault = MemoryVault()
    token = await vault.issue_token_for_decision(decision(), lifetime_seconds=120, tool="stripe")

    result, audit = await introspect(vault, token.token_id)

    assert result.active is True
    assert audit.events[-1]["decision_id"] == "gd_runtime_1"
    assert audit.events[-1]["token_id"] == token.token_id
