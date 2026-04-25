"""Tests for the new hashed, scoped API key management."""

import hashlib
import time

import pytest

from citadel.auth.api_key import ApiKey, ApiKeyManager


class TestApiKey:
    """Unit tests for the ApiKey dataclass."""

    def test_creation(self):
        key = ApiKey(
            key_hash="abc123",
            scopes=["read", "write"],
            tenant_id="tenant-1",
            actor_id="agent-1",
            expires_at=time.time() + 3600,
        )
        assert key.key_hash == "abc123"
        assert key.scopes == ["read", "write"]
        assert key.tenant_id == "tenant-1"
        assert key.is_expired is False

    def test_expiration(self):
        expired = ApiKey(
            key_hash="expired",
            scopes=["read"],
            expires_at=time.time() - 1,
        )
        assert expired.is_expired is True

    def test_has_scope(self):
        key = ApiKey(key_hash="h", scopes=["read", "write", "admin"])
        assert key.has_scope("write") is True
        assert key.has_scope("admin") is True
        assert key.has_scope("delete") is False

    def test_default_admin_scope(self):
        key = ApiKey(key_hash="h", scopes=[])
        assert key.has_scope("read") is True  # default admin grants all
        assert key.has_scope("admin") is True


class TestApiKeyManager:
    """Unit tests for ApiKeyManager."""

    def test_hashing_never_stores_plaintext(self):
        mgr = ApiKeyManager()
        plain = "my-secret-key"
        hashed = mgr._hash_key(plain)
        assert hashed != plain
        assert len(hashed) == 64  # SHA-256 hex
        assert mgr._verify_key(plain, hashed) is True
        assert mgr._verify_key("wrong-key", hashed) is False

    def test_add_key_and_lookup(self):
        mgr = ApiKeyManager()
        key = mgr.add_key("test-key-123", scopes=["read", "write"], tenant_id="t1")
        assert key.key_hash != "test-key-123"
        assert key.scopes == ["read", "write"]

        looked_up = mgr.lookup("test-key-123")
        assert looked_up is not None
        assert looked_up.tenant_id == "t1"
        assert looked_up.has_scope("write") is True

    def test_lookup_not_found(self):
        mgr = ApiKeyManager()
        assert mgr.lookup("nonexistent") is None

    def test_revoke_key(self):
        mgr = ApiKeyManager()
        mgr.add_key("key-to-revoke", scopes=["admin"])
        assert mgr.lookup("key-to-revoke") is not None

        mgr.revoke("key-to-revoke")
        assert mgr.lookup("key-to-revoke") is None

    def test_validate_success(self):
        mgr = ApiKeyManager()
        mgr.add_key("valid-key", scopes=["read", "write"])
        result = mgr.validate("valid-key", required_scopes=["read"])
        assert result.is_valid is True
        assert result.scopes == ["read", "write"]
        assert result.error is None

    def test_validate_missing_scopes(self):
        mgr = ApiKeyManager()
        mgr.add_key("limited-key", scopes=["read"])
        result = mgr.validate("limited-key", required_scopes=["write"])
        assert result.is_valid is False
        assert result.error == "insufficient_scope"

    def test_validate_expired(self):
        mgr = ApiKeyManager()
        mgr.add_key(
            "expired-key",
            scopes=["admin"],
            expires_at=time.time() - 10,
        )
        result = mgr.validate("expired-key")
        assert result.is_valid is False
        assert result.error == "expired"

    def test_validate_not_found(self):
        mgr = ApiKeyManager()
        result = mgr.validate("missing")
        assert result.is_valid is False
        assert result.error == "invalid_key"

    def test_load_from_settings_string(self):
        mgr = ApiKeyManager()
        mgr.load_from_settings("dev-key:read,write;prod-key:admin")
        assert len(mgr._keys) == 2

        dev = mgr.lookup("dev-key")
        assert dev is not None
        assert dev.scopes == ["read", "write"]

        prod = mgr.lookup("prod-key")
        assert prod is not None
        assert prod.scopes == ["admin"]

    def test_load_from_settings_backward_compat(self):
        """Plain key without scope defaults to admin."""
        mgr = ApiKeyManager()
        mgr.load_from_settings("legacy-key")
        key = mgr.lookup("legacy-key")
        assert key is not None
        assert key.scopes == ["admin"]

    def test_last_used_tracking(self):
        mgr = ApiKeyManager()
        mgr.add_key("tracked-key", scopes=["read"])
        before = time.time()
        mgr.validate("tracked-key")
        after = time.time()

        key = mgr.lookup("tracked-key")
        assert key.last_used_at is not None
        assert before <= key.last_used_at <= after

    def test_tenant_isolation(self):
        mgr = ApiKeyManager()
        mgr.add_key("tenant-a-key", scopes=["read"], tenant_id="tenant-a")
        mgr.add_key("tenant-b-key", scopes=["read"], tenant_id="tenant-b")

        a = mgr.lookup("tenant-a-key")
        b = mgr.lookup("tenant-b-key")
        assert a.tenant_id == "tenant-a"
        assert b.tenant_id == "tenant-b"
