"""
End-to-end tests for Governance REST API.

Covers:
  POST /v1/governance/decisions              — Create decision
  GET  /v1/governance/decisions/{id}         — Get decision
  POST /v1/governance/decisions/{id}/tokens  — Derive token
  GET  /v1/governance/tokens/{id}            — Get token
  POST /v1/governance/verify                 — Verify token/decision
  GET  /v1/governance/audit/verify           — Verify audit chain
  GET  /v1/governance/decisions/{id}/audit   — Get decision audit events
"""

import pytest
import uuid
import httpx
from httpx import ASGITransport

from citadel.api import create_app
from citadel.tokens import GovernanceDecision, DecisionType


# Test configuration overrides
import citadel.config
citadel.config.settings.require_auth = True
citadel.config.settings.api_keys = "test-key"
citadel.config.settings.database_url = "postgresql://citadel:citadel@localhost:5432/citadel_test"


@pytest.fixture
async def client(postgres_dsn):
    """Async HTTP client over ASGI."""
    app = create_app()
    # Override the pool to use the test DSN
    import asyncpg
    pool = await asyncpg.create_pool(postgres_dsn, min_size=1, max_size=2)
    app.state.db_pool = pool

    transport = ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        yield c

    await pool.close()


HEADERS = {
    "X-API-Key": "test-key",
    "X-Tenant-ID": "test_tenant_e2e",
}


class TestGovernanceAPI:
    @pytest.mark.asyncio
    async def test_create_decision(self, client):
        """Can create a governance decision via API."""
        resp = await client.post(
            "/v1/governance/decisions",
            headers=HEADERS,
            json={
                "decision_type": "allow",
                "actor_id": "agent_api_1",
                "action": "file.read",
                "scope_actions": ["file.read", "file.write"],
                "scope_resources": ["/data/*"],
                "constraints": {"max_size": 1024},
                "expiry_minutes": 60,
                "kill_switch_scope": "agent",
                "reason": "E2E test decision",
            },
        )
        assert resp.status_code == 201, resp.text
        data = resp.json()
        assert data["decision_type"] == "allow"
        assert data["actor_id"] == "agent_api_1"
        assert data["action"] == "file.read"
        assert data["scope_actions"] == ["file.read", "file.write"]
        assert data["tenant_id"] == "test_tenant_e2e"
        assert data["decision_id"].startswith("gd_")
        assert data["expiry"] is not None

    @pytest.mark.asyncio
    async def test_get_decision(self, client):
        """Can retrieve a decision by ID."""
        # Create
        create_resp = await client.post(
            "/v1/governance/decisions",
            headers=HEADERS,
            json={
                "decision_type": "allow",
                "actor_id": "agent_api_2",
                "action": "db.query",
                "scope_actions": ["db.query"],
                "reason": "get test",
            },
        )
        decision_id = create_resp.json()["decision_id"]

        # Get
        get_resp = await client.get(
            f"/v1/governance/decisions/{decision_id}",
            headers=HEADERS,
        )
        assert get_resp.status_code == 200
        data = get_resp.json()
        assert data["decision_id"] == decision_id
        assert data["actor_id"] == "agent_api_2"

    @pytest.mark.asyncio
    async def test_get_decision_not_found(self, client):
        """404 for non-existent decision."""
        resp = await client.get(
            "/v1/governance/decisions/gd_nonexistent_12345",
            headers=HEADERS,
        )
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_cross_tenant_decision_isolation(self, client):
        """Tenant A cannot read Tenant B's decision."""
        # Create as tenant A
        resp = await client.post(
            "/v1/governance/decisions",
            headers={**HEADERS, "X-Tenant-ID": "tenant_a"},
            json={
                "decision_type": "allow",
                "actor_id": "agent_a",
                "action": "file.read",
                "reason": "isolation test",
            },
        )
        decision_id = resp.json()["decision_id"]

        # Try to read as tenant B
        resp2 = await client.get(
            f"/v1/governance/decisions/{decision_id}",
            headers={**HEADERS, "X-Tenant-ID": "tenant_b"},
        )
        assert resp2.status_code == 404

    @pytest.mark.asyncio
    async def test_derive_token_from_decision(self, client):
        """Can derive a token from an ALLOW decision."""
        # Create decision
        resp = await client.post(
            "/v1/governance/decisions",
            headers=HEADERS,
            json={
                "decision_type": "allow",
                "actor_id": "agent_api_3",
                "action": "api.call",
                "scope_actions": ["api.call"],
                "reason": "token derivation test",
            },
        )
        decision_id = resp.json()["decision_id"]

        # Derive token
        token_resp = await client.post(
            f"/v1/governance/decisions/{decision_id}/tokens",
            headers=HEADERS,
            json={},
        )
        assert token_resp.status_code == 201, token_resp.text
        data = token_resp.json()
        assert data["token_id"].startswith("gt_cap_")
        assert data["decision_id"] == decision_id
        assert data["chain_hash"] is not None
        assert len(data["chain_hash"]) == 64

    @pytest.mark.asyncio
    async def test_deny_decision_cannot_derive_token(self, client):
        """DENY decisions cannot produce tokens."""
        resp = await client.post(
            "/v1/governance/decisions",
            headers=HEADERS,
            json={
                "decision_type": "deny",
                "actor_id": "agent_api_4",
                "action": "file.delete",
                "reason": "should not derive",
            },
        )
        decision_id = resp.json()["decision_id"]

        token_resp = await client.post(
            f"/v1/governance/decisions/{decision_id}/tokens",
            headers=HEADERS,
            json={},
        )
        assert token_resp.status_code == 400
        assert "deny" in token_resp.json()["detail"]

    @pytest.mark.asyncio
    async def test_get_token(self, client):
        """Can retrieve a token by ID."""
        # Create + derive
        resp = await client.post(
            "/v1/governance/decisions",
            headers=HEADERS,
            json={
                "decision_type": "allow",
                "actor_id": "agent_api_5",
                "action": "cache.clear",
                "reason": "token get test",
            },
        )
        decision_id = resp.json()["decision_id"]
        token_resp = await client.post(
            f"/v1/governance/decisions/{decision_id}/tokens",
            headers=HEADERS,
            json={},
        )
        token_id = token_resp.json()["token_id"]

        # Get token
        get_resp = await client.get(
            f"/v1/governance/tokens/{token_id}",
            headers=HEADERS,
        )
        assert get_resp.status_code == 200
        data = get_resp.json()
        assert data["token_id"] == token_id
        assert data["decision_id"] == decision_id

    @pytest.mark.asyncio
    async def test_verify_token(self, client):
        """Can verify a valid token via API."""
        # Create + derive
        resp = await client.post(
            "/v1/governance/decisions",
            headers=HEADERS,
            json={
                "decision_type": "allow",
                "actor_id": "agent_api_6",
                "action": "service.restart",
                "scope_actions": ["service.restart", "service.stop"],
                "reason": "verify test",
            },
        )
        decision_id = resp.json()["decision_id"]
        token_resp = await client.post(
            f"/v1/governance/decisions/{decision_id}/tokens",
            headers=HEADERS,
            json={},
        )
        token_id = token_resp.json()["token_id"]

        # Verify valid action
        verify_resp = await client.post(
            "/v1/governance/verify",
            headers=HEADERS,
            json={
                "credential": token_id,
                "action": "service.restart",
                "resource": "worker-1",
                "context": {"env": "prod"},
            },
        )
        assert verify_resp.status_code == 200
        data = verify_resp.json()
        assert data["valid"] is True
        assert data["decision_id"] == decision_id
        assert data["actor_id"] == "agent_api_6"

    @pytest.mark.asyncio
    async def test_verify_token_scope_mismatch(self, client):
        """Verification fails for out-of-scope action."""
        # Create + derive
        resp = await client.post(
            "/v1/governance/decisions",
            headers=HEADERS,
            json={
                "decision_type": "allow",
                "actor_id": "agent_api_7",
                "action": "file.read",
                "scope_actions": ["file.read"],
                "reason": "scope test",
            },
        )
        decision_id = resp.json()["decision_id"]
        token_resp = await client.post(
            f"/v1/governance/decisions/{decision_id}/tokens",
            headers=HEADERS,
            json={},
        )
        token_id = token_resp.json()["token_id"]

        # Verify wrong action
        verify_resp = await client.post(
            "/v1/governance/verify",
            headers=HEADERS,
            json={
                "credential": token_id,
                "action": "file.delete",
            },
        )
        assert verify_resp.status_code == 200
        data = verify_resp.json()
        assert data["valid"] is False
        assert data["reason"] == "scope_mismatch"

    @pytest.mark.asyncio
    async def test_verify_decision_directly(self, client):
        """Can verify a decision ID directly (no token)."""
        resp = await client.post(
            "/v1/governance/decisions",
            headers=HEADERS,
            json={
                "decision_type": "allow",
                "actor_id": "agent_api_8",
                "action": "config.update",
                "scope_actions": ["config.update"],
                "reason": "direct decision verify",
            },
        )
        decision_id = resp.json()["decision_id"]

        verify_resp = await client.post(
            "/v1/governance/verify",
            headers=HEADERS,
            json={
                "credential": decision_id,
                "action": "config.update",
            },
        )
        assert verify_resp.status_code == 200
        data = verify_resp.json()
        assert data["valid"] is True
        assert data["decision_id"] == decision_id

    @pytest.mark.asyncio
    async def test_verify_invalid_credential(self, client):
        """Invalid credential format is rejected."""
        resp = await client.post(
            "/v1/governance/verify",
            headers=HEADERS,
            json={
                "credential": "not_a_valid_id",
                "action": "anything",
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["valid"] is False
        assert data["reason"] == "invalid_credential_format"

    @pytest.mark.asyncio
    async def test_audit_chain_integrity(self, client):
        """Governance audit chain is valid after operations."""
        # Create decision + derive token (generates audit events)
        resp = await client.post(
            "/v1/governance/decisions",
            headers=HEADERS,
            json={
                "decision_type": "allow",
                "actor_id": "agent_api_9",
                "action": "log.read",
                "reason": "audit chain test",
            },
        )
        decision_id = resp.json()["decision_id"]
        await client.post(
            f"/v1/governance/decisions/{decision_id}/tokens",
            headers=HEADERS,
            json={},
        )

        # Verify chain
        chain_resp = await client.get(
            "/v1/governance/audit/verify",
            headers=HEADERS,
        )
        assert chain_resp.status_code == 200
        data = chain_resp.json()
        assert data["valid"] is True
        assert data["checked_count"] >= 2

    @pytest.mark.asyncio
    async def test_decision_audit_events(self, client):
        """Can query audit events for a specific decision."""
        resp = await client.post(
            "/v1/governance/decisions",
            headers=HEADERS,
            json={
                "decision_type": "allow",
                "actor_id": "agent_api_10",
                "action": "metric.read",
                "reason": "audit events test",
            },
        )
        decision_id = resp.json()["decision_id"]
        await client.post(
            f"/v1/governance/decisions/{decision_id}/tokens",
            headers=HEADERS,
            json={},
        )

        audit_resp = await client.get(
            f"/v1/governance/decisions/{decision_id}/audit",
            headers=HEADERS,
        )
        assert audit_resp.status_code == 200
        events = audit_resp.json()
        assert len(events) >= 2
        types = {e["event_type"] for e in events}
        assert "decision.created" in types
        assert "token.derived" in types

    @pytest.mark.asyncio
    async def test_auth_required(self, client):
        """Requests without API key are rejected."""
        resp = await client.post(
            "/v1/governance/decisions",
            headers={"X-Tenant-ID": "test_tenant_e2e"},  # No X-API-Key
            json={
                "decision_type": "allow",
                "actor_id": "agent_x",
                "action": "test.action",
                "reason": "auth test",
            },
        )
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_tenant_header_required(self, client):
        """Requests without X-Tenant-ID are rejected (422 for missing header)."""
        resp = await client.post(
            "/v1/governance/decisions",
            headers={"X-API-Key": "test-key"},  # No X-Tenant-ID
            json={
                "decision_type": "allow",
                "actor_id": "agent_x",
                "action": "test.action",
                "reason": "tenant test",
            },
        )
        assert resp.status_code == 422
