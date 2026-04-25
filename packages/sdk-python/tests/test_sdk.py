"""Tests for citadel-governance SDK.

Run: pytest tests/test_sdk.py -v
"""

import asyncio
import warnings

import httpx
import pytest
import respx

import citadel_governance as cg
from citadel_governance import (
    Agent,
    AgentIdentity,
    Approval,
    AuthenticationError,
    CitadelClient,
    CitadelError,
    CitadelResult,
    Conflict,
    DashboardStats,
    NotFound,
    Policy,
    RateLimitError,
    ServerError,
    TrustScore,
    ValidationError,
    ActionBlocked,
    ApprovalRequired,
    configure,
    execute,
    approve,
    create_agent,
    create_policy,
    delete_policy,
    get_action,
    get_agent,
    get_kill_switches,
    get_metrics_summary,
    get_stats,
    get_trust_score,
    list_agent_identities,
    list_agents,
    list_approvals,
    list_audit_events,
    list_policies,
    quarantine_agent,
    reject,
    request_capability,
    revoke_agent_identity,
    toggle_kill_switch,
    update_agent,
    update_policy,
    verify_audit,
)


@pytest.fixture
def client():
    return CitadelClient(base_url="https://api.citadelsdk.com", api_key="k")


# ---------------------------------------------------------------------------
# Actions
# ---------------------------------------------------------------------------

@respx.mock
def test_execute_success(client):
    route = respx.post("https://api.citadelsdk.com/v1/actions/execute").mock(
        return_value=httpx.Response(200, json={
            "action_id": "act-123",
            "status": "executed",
            "winning_rule": "auto_approve",
            "reason": "Within budget",
            "executed": True,
            "result": {"email_id": "msg-456"},
        })
    )
    result = asyncio.run(client.execute(action="email.send", resource="user:123"))
    assert result.status == "executed"
    assert result.result == {"email_id": "msg-456"}
    assert route.called


@respx.mock
def test_decide_dry_run(client):
    route = respx.post("https://api.citadelsdk.com/v1/actions/execute").mock(
        return_value=httpx.Response(200, json={
            "action_id": "act-789",
            "status": "dry_run",
            "winning_rule": "dry_run",
            "reason": "Dry run — policies evaluated but action not executed",
            "executed": False,
        })
    )
    result = asyncio.run(client.decide(action="db.write", resource="users"))
    assert result.status == "dry_run"
    assert result.executed is False
    sent = route.calls[0].request.content.decode()
    assert '"dry_run":' in sent


@respx.mock
def test_get_action(client):
    route = respx.get("https://api.citadelsdk.com/v1/actions/act-123").mock(
        return_value=httpx.Response(200, json={
            "action_id": "act-123",
            "actor_id": "test-agent",
            "action_name": "email.send",
            "resource": "user:123",
            "status": "executed",
            "winning_rule": "auto_approve",
            "reason": "OK",
            "executed": True,
        })
    )
    data = asyncio.run(client.get_action("act-123"))
    assert data["action_id"] == "act-123"
    assert route.called


# ---------------------------------------------------------------------------
# Approvals
# ---------------------------------------------------------------------------

@respx.mock
def test_list_approvals(client):
    route = respx.get("https://api.citadelsdk.com/v1/approvals").mock(
        return_value=httpx.Response(200, json={
            "approvals": [
                {"id": "app-1", "action": "email.send", "status": "pending"},
            ]
        })
    )
    approvals = asyncio.run(client.list_approvals())
    assert len(approvals) == 1
    assert approvals[0].id == "app-1"


@respx.mock
def test_approve(client):
    route = respx.post("https://api.citadelsdk.com/v1/approvals/app-1/approve").mock(
        return_value=httpx.Response(200, json={
            "id": "app-1",
            "action": "email.send",
            "status": "approved",
        })
    )
    approval = asyncio.run(client.approve("app-1", "admin@example.com"))
    assert approval.status == "approved"


@respx.mock
def test_reject(client):
    route = respx.post("https://api.citadelsdk.com/v1/approvals/app-1/reject").mock(
        return_value=httpx.Response(200, json={
            "id": "app-1",
            "action": "email.send",
            "status": "rejected",
        })
    )
    approval = asyncio.run(client.reject("app-1", "admin@example.com"))
    assert approval.status == "rejected"


# ---------------------------------------------------------------------------
# Agent Identities
# ---------------------------------------------------------------------------

@respx.mock
def test_register_agent_identity(client):
    route = respx.post("https://api.citadelsdk.com/api/agent-identities").mock(
        return_value=httpx.Response(200, json={
            "agent_id": "agent-1",
            "api_key": "ak_xxx",
            "secret_key": "sk_xxx",
            "public_key": "pk_xxx",
            "trust_score": 0.5,
            "trust_level": "low",
        })
    )
    identity = asyncio.run(client.register_agent_identity("agent-1", "Test Agent"))
    assert identity.agent_id == "agent-1"
    assert identity.api_key == "ak_xxx"


@respx.mock
def test_authenticate_agent(client):
    route = respx.post("https://api.citadelsdk.com/api/agent-identities/agent-1/authenticate").mock(
        return_value=httpx.Response(200, json={"authenticated": True})
    )
    data = asyncio.run(client.authenticate_agent("agent-1", "sk_xxx"))
    assert data["authenticated"] is True


@respx.mock
def test_revoke_agent_identity(client):
    route = respx.post("https://api.citadelsdk.com/api/agent-identities/agent-1/revoke").mock(
        return_value=httpx.Response(200, json={"revoked": True})
    )
    data = asyncio.run(client.revoke_agent_identity("agent-1"))
    assert data["revoked"] is True


@respx.mock
def test_get_trust_score(client):
    route = respx.get("https://api.citadelsdk.com/api/agent-identities/agent-1/trust").mock(
        return_value=httpx.Response(200, json={
            "agent_id": "agent-1",
            "score": 0.85,
            "level": "high",
            "factors": {},
        })
    )
    score = asyncio.run(client.get_trust_score("agent-1"))
    assert score.score == 0.85
    assert score.level == "high"


@respx.mock
def test_request_capability(client):
    route = respx.post("https://api.citadelsdk.com/api/agent-identities/agent-1/capability").mock(
        return_value=httpx.Response(200, json={"verified": True, "authorized": True, "token": "cap_xxx"})
    )
    data = asyncio.run(client.request_capability("agent-1", "db.write", "users"))
    assert data["token"] == "cap_xxx"


# ---------------------------------------------------------------------------
# Agents
# ---------------------------------------------------------------------------

@respx.mock
def test_list_agents(client):
    route = respx.get("https://api.citadelsdk.com/api/agents").mock(
        return_value=httpx.Response(200, json={
            "agents": [
                {"agent_id": "agent-1", "name": "Test", "status": "healthy"},
            ]
        })
    )
    agents = asyncio.run(client.list_agents())
    assert len(agents) == 1
    assert agents[0].agent_id == "agent-1"


@respx.mock
def test_quarantine_agent(client):
    route = respx.post("https://api.citadelsdk.com/api/agents/agent-1/quarantine").mock(
        return_value=httpx.Response(200, json={"agent_id": "agent-1", "status": "quarantined"})
    )
    agent = asyncio.run(client.quarantine_agent("agent-1"))
    assert agent.status == "quarantined"


# ---------------------------------------------------------------------------
# Policies
# ---------------------------------------------------------------------------

@respx.mock
def test_list_policies(client):
    route = respx.get("https://api.citadelsdk.com/api/policies").mock(
        return_value=httpx.Response(200, json={
            "policies": [
                {"id": "pol-1", "name": "SOC2 Access", "framework": "SOC2"},
            ]
        })
    )
    policies = asyncio.run(client.list_policies())
    assert len(policies) == 1
    assert policies[0].name == "SOC2 Access"


@respx.mock
def test_create_policy(client):
    route = respx.post("https://api.citadelsdk.com/api/policies").mock(
        return_value=httpx.Response(200, json={
            "id": "pol-1",
            "name": "New Policy",
            "framework": "SOC2",
            "severity": "medium",
        })
    )
    policy = asyncio.run(client.create_policy("New Policy"))
    assert policy.id == "pol-1"


@respx.mock
def test_delete_policy(client):
    route = respx.delete("https://api.citadelsdk.com/api/policies/pol-1").mock(
        return_value=httpx.Response(200, json={"message": "Policy deleted"})
    )
    data = asyncio.run(client.delete_policy("pol-1"))
    assert data["message"] == "Policy deleted"


# ---------------------------------------------------------------------------
# Kill Switches
# ---------------------------------------------------------------------------

@respx.mock
def test_get_kill_switches(client):
    route = respx.get("https://api.citadelsdk.com/api/dashboard/stats").mock(
        return_value=httpx.Response(200, json={
            "pending_approvals": 0,
            "active_agents": 5,
            "risk_level": "low",
            "kill_switches_active": 1,
            "killswitches": {"stop_all": True},
            "recent_events_count": 10,
            "total_actions": 100,
            "approved_this_month": 50,
            "blocked_this_month": 5,
            "active_agents_24h": 3,
            "agent_identities": 2,
        })
    )
    switches = asyncio.run(client.get_kill_switches())
    assert switches["stop_all"] is True


@respx.mock
def test_toggle_kill_switch(client):
    route = respx.post("https://api.citadelsdk.com/api/dashboard/kill-switch").mock(
        return_value=httpx.Response(200, json={"switch": "stop_all", "active": True})
    )
    data = asyncio.run(client.toggle_kill_switch("stop_all", True))
    assert data["active"] is True


# ---------------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------------

@respx.mock
def test_get_stats(client):
    route = respx.get("https://api.citadelsdk.com/api/dashboard/stats").mock(
        return_value=httpx.Response(200, json={
            "pending_approvals": 2,
            "active_agents": 5,
            "risk_level": "medium",
            "kill_switches_active": 0,
            "killswitches": {},
            "recent_events_count": 10,
            "total_actions": 100,
            "approved_this_month": 50,
            "blocked_this_month": 5,
            "active_agents_24h": 3,
            "agent_identities": 2,
        })
    )
    stats = asyncio.run(client.get_stats())
    assert stats.risk_level == "medium"
    assert stats.pending_approvals == 2


@respx.mock
def test_get_metrics_summary(client):
    route = respx.get("https://api.citadelsdk.com/v1/metrics/summary").mock(
        return_value=httpx.Response(200, json={"total_actions": 100, "approval_rate": 0.95})
    )
    data = asyncio.run(client.get_metrics_summary())
    assert data["total_actions"] == 100


# ---------------------------------------------------------------------------
# Audit
# ---------------------------------------------------------------------------

@respx.mock
def test_verify_audit(client):
    route = respx.get("https://api.citadelsdk.com/v1/audit/verify").mock(
        return_value=httpx.Response(200, json={"valid": True})
    )
    data = asyncio.run(client.verify_audit())
    assert data["valid"] is True


@respx.mock
def test_list_audit_events(client):
    route = respx.get("https://api.citadelsdk.com/api/audit").mock(
        return_value=httpx.Response(200, json={
            "events": [{"id": "evt-1", "action": "email.send"}],
        })
    )
    events = asyncio.run(client.list_audit_events())
    assert len(events) == 1
    assert events[0]["id"] == "evt-1"


# ---------------------------------------------------------------------------
# Errors
# ---------------------------------------------------------------------------

@respx.mock
def test_not_found_error(client):
    route = respx.get("https://api.citadelsdk.com/v1/actions/missing").mock(
        return_value=httpx.Response(404, json={"detail": "Not found"})
    )
    with pytest.raises(NotFound):
        asyncio.run(client.get_action("missing"))


@respx.mock
def test_conflict_error(client):
    route = respx.post("https://api.citadelsdk.com/api/policies").mock(
        return_value=httpx.Response(409, json={"detail": "Already exists"})
    )
    with pytest.raises(Conflict):
        asyncio.run(client.create_policy("Duplicate"))


# ---------------------------------------------------------------------------
# Decorators
# ---------------------------------------------------------------------------

@respx.mock
def test_guard_decorator_executed(client):
    route = respx.post("https://api.citadelsdk.com/v1/actions/execute").mock(
        return_value=httpx.Response(200, json={
            "action_id": "act-1",
            "status": "executed",
            "winning_rule": "allow",
            "reason": "OK",
            "executed": True,
        })
    )

    @client.guard(action="test.action", resource="res")
    async def my_func():
        return "success"

    result = asyncio.run(my_func())
    assert result == "success"
    assert route.called


@respx.mock
def test_guard_decorator_blocked(client):
    route = respx.post("https://api.citadelsdk.com/v1/actions/execute").mock(
        return_value=httpx.Response(200, json={
            "action_id": "act-1",
            "status": "blocked",
            "winning_rule": "deny",
            "reason": "Not allowed",
            "executed": False,
        })
    )

    @client.guard(action="test.action", resource="res")
    async def my_func():
        return "should not reach"

    with pytest.raises(ActionBlocked):
        asyncio.run(my_func())
    assert route.called


# ---------------------------------------------------------------------------
# Context Manager
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_context_manager():
    async with CitadelClient(base_url="https://api.citadelsdk.com", api_key="k") as client:
        assert client.api_key == "k"


# ---------------------------------------------------------------------------
# Module-level API
# ---------------------------------------------------------------------------

@respx.mock
def test_module_level_execute():
    configure(base_url="https://api.citadelsdk.com", api_key="k", actor_id="a")
    route = respx.post("https://api.citadelsdk.com/v1/actions/execute").mock(
        return_value=httpx.Response(200, json={
            "action_id": "act-1",
            "status": "executed",
            "winning_rule": "allow",
            "reason": "OK",
            "executed": True,
        })
    )
    result = asyncio.run(execute(action="test", resource="r"))
    assert result.status == "executed"
    assert route.called


# ---------------------------------------------------------------------------
# Retry Logic & New Error Classes
# ---------------------------------------------------------------------------

@respx.mock
def test_retry_on_rate_limit_with_retry_after(client):
    """Client should respect Retry-After header and retry on 429."""
    route = respx.post("https://api.citadelsdk.com/v1/actions/execute").mock(
        side_effect=[
            httpx.Response(429, json={"detail": "Too many requests"}, headers={"Retry-After": "0.05"}),
            httpx.Response(200, json={
                "action_id": "act-1",
                "status": "executed",
                "winning_rule": "allow",
                "reason": "OK",
                "executed": True,
            }),
        ]
    )
    result = asyncio.run(client.execute(action="test", resource="r"))
    assert result.status == "executed"
    assert route.call_count == 2


@respx.mock
def test_retry_on_server_error(client):
    """Client should retry on 500 and succeed when server recovers."""
    route = respx.post("https://api.citadelsdk.com/v1/actions/execute").mock(
        side_effect=[
            httpx.Response(500, json={"detail": "Internal error"}),
            httpx.Response(200, json={
                "action_id": "act-1",
                "status": "executed",
                "winning_rule": "allow",
                "reason": "OK",
                "executed": True,
            }),
        ]
    )
    result = asyncio.run(client.execute(action="test", resource="r"))
    assert result.status == "executed"
    assert route.call_count == 2


@respx.mock
def test_rate_limit_error_raises_rate_limit_error(client):
    route = respx.post("https://api.citadelsdk.com/v1/actions/execute").mock(
        return_value=httpx.Response(429, json={"detail": "Rate limited"}, headers={"Retry-After": "5"})
    )
    with pytest.raises(RateLimitError) as exc:
        asyncio.run(client.execute(action="test", resource="r"))
    assert exc.value.status == 429
    assert exc.value.retry_after == 5.0


@respx.mock
def test_validation_error(client):
    route = respx.post("https://api.citadelsdk.com/v1/actions/execute").mock(
        return_value=httpx.Response(422, json={"detail": "Invalid payload"})
    )
    with pytest.raises(ValidationError) as exc:
        asyncio.run(client.execute(action="test", resource="r"))
    assert exc.value.status == 422


@respx.mock
def test_authentication_error(client):
    route = respx.post("https://api.citadelsdk.com/v1/actions/execute").mock(
        return_value=httpx.Response(401, json={"detail": "Unauthorized"})
    )
    with pytest.raises(AuthenticationError) as exc:
        asyncio.run(client.execute(action="test", resource="r"))
    assert exc.value.status == 401


@respx.mock
def test_server_error_raises_server_error(client):
    route = respx.post("https://api.citadelsdk.com/v1/actions/execute").mock(
        return_value=httpx.Response(503, json={"detail": "Service unavailable"})
    )
    with pytest.raises(ServerError) as exc:
        asyncio.run(client.execute(action="test", resource="r"))
    assert exc.value.status == 503


# ---------------------------------------------------------------------------
# Connection Configuration
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_client_with_custom_timeout():
    client = CitadelClient(base_url="https://api.citadelsdk.com", api_key="k", timeout=120.0)
    assert client._client.timeout.connect == 120.0
    await client.close()


def test_client_with_proxies():
    client = CitadelClient(
        base_url="https://api.citadelsdk.com",
        api_key="k",
        proxies={"https": "http://proxy.example.com:8080"},
    )
    # httpx stores proxy on the client; just verify creation succeeds
    assert client._client is not None
    asyncio.run(client.close())


def test_client_max_retries_default():
    client = CitadelClient(base_url="https://api.citadelsdk.com", api_key="k")
    assert client.max_retries == 3
    asyncio.run(client.close())


def test_client_max_retries_custom():
    client = CitadelClient(base_url="https://api.citadelsdk.com", api_key="k", max_retries=5)
    assert client.max_retries == 5
    asyncio.run(client.close())


# ---------------------------------------------------------------------------
# Legacy import deprecation warning
# ---------------------------------------------------------------------------

def test_legacy_import_emits_warning():
    """Verify the SDK shim emits DeprecationWarning when imported.
    
    In a real install (wheel), 'import citadel' resolves to the SDK shim.
    During dev, the backend package may shadow it, so we test the shim
    directly by manipulating sys.path.
    """
    import sys
    import importlib
    
    # Save original state
    orig_modules = set(sys.modules.keys())
    orig_path = sys.path.copy()
    
    try:
        # Remove any already-imported citadel modules
        for mod in list(sys.modules.keys()):
            if mod == "citadel" or mod.startswith("citadel."):
                del sys.modules[mod]
        
        # Ensure SDK packages/python path is first
        sdk_path = "/root/.openclaw/workspace/ledger-sdk/packages/sdk-python"
        if sdk_path in sys.path:
            sys.path.remove(sdk_path)
        sys.path.insert(0, sdk_path)
        
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            import citadel
            assert any(issubclass(warning.category, DeprecationWarning) for warning in w)
            assert citadel.__version__ == "0.2.0"
    finally:
        # Restore sys.path
        sys.path = orig_path
        # Remove any citadel modules we imported
        for mod in list(sys.modules.keys()):
            if mod == "citadel" or mod.startswith("citadel."):
                del sys.modules[mod]
