"""Tests for API key manager."""

import pytest
import time
from datetime import datetime, timezone, timedelta

from citadel.auth.api_key import ApiKey, ApiKeyManager


class TestApiKey:
    """Unit tests for the ApiKey dataclass."""

    def test_creation(self):
        key = ApiKey(
            key_hash="abc123",
            scopes={"read", "write"},
            created_at=datetime.now(timezone.utc),
            tenant_id="tenant-1",
            expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
        )
        assert key.key_hash == "abc123"
        assert key.scopes == {"read", "write"}
        assert key.tenant_id == "tenant-1"
        assert key.is_expired() is False

    def test_has_scope(self):
        key = ApiKey(
            key_hash="abc",
            scopes={"read"},
            created_at=datetime.now(timezone.utc),
        )
        assert key.has_scope("read") is True
        assert key.has_scope("write") is False
        assert key.has_scope("admin") is False

    def test_admin_scope_grants_all(self):
        key = ApiKey(
            key_hash="abc",
            scopes={"admin"},
            created_at=datetime.now(timezone.utc),
        )
        assert key.has_scope("read") is True
        assert key.has_scope("write") is True
        assert key.has_scope("admin") is True

    def test_expired_key(self):
        key = ApiKey(
            key_hash="abc",
            scopes={"read"},
            created_at=datetime.now(timezone.utc),
            expires_at=datetime.now(timezone.utc) - timedelta(hours=1),
        )
        assert key.is_expired() is True
        assert key.is_valid() is False

    def test_no_expiration_never_expired(self):
        key = ApiKey(
            key_hash="abc",
            scopes={"read"},
            created_at=datetime.now(timezone.utc),
            expires_at=None,
        )
        assert key.is_expired() is False
        assert key.is_valid() is True


class TestApiKeyManager:
    """Unit tests for ApiKeyManager."""

    def test_validate_valid_key(self):
        manager = ApiKeyManager()
        manager.add_key("sk_test_123", scopes={"read", "write"})
        
        result = manager.validate("sk_test_123")
        assert result is not None
        assert result.key_hash == manager._hash_key("sk_test_123")
        assert result.has_scope("write") is True

    def test_validate_invalid_key(self):
        manager = ApiKeyManager()
        manager.add_key("sk_test_123", scopes={"read"})
        
        result = manager.validate("wrong_key")
        assert result is None

    def test_validate_expired_key(self):
        manager = ApiKeyManager()
        manager.add_key(
            "sk_test_123",
            scopes={"read"},
            expires_at=datetime.now(timezone.utc) - timedelta(hours=1),
        )
        
        result = manager.validate("sk_test_123")
        assert result is None

    def test_validate_updates_last_used(self):
        manager = ApiKeyManager()
        manager.add_key("sk_test_123", scopes={"read"})
        
        result = manager.validate("sk_test_123")
        assert result.last_used_at is not None

    def test_add_duplicate_key_fails(self):
        manager = ApiKeyManager()
        manager.add_key("sk_test_123", scopes={"read"})
        
        with pytest.raises(ValueError, match="already exists"):
            manager.add_key("sk_test_123", scopes={"write"})

    def test_revoke_key(self):
        manager = ApiKeyManager()
        manager.add_key("sk_test_123", scopes={"read"})
        
        key_hash = manager._hash_key("sk_test_123")
        assert manager.revoke_key(key_hash) is True
        assert manager.validate("sk_test_123") is None

    def test_revoke_nonexistent_key(self):
        manager = ApiKeyManager()
        assert manager.revoke_key("nonexistent") is False

    def test_from_settings_with_scopes(self):
        manager = ApiKeyManager.from_settings("sk_prod_abc:read|write,sk_dev_xyz:admin")
        
        assert len(manager.list_keys()) == 2
        
        prod = manager.validate("sk_prod_abc")
        assert prod is not None
        assert prod.has_scope("read") is True
        assert prod.has_scope("write") is True
        assert prod.has_scope("admin") is False
        
        dev = manager.validate("sk_dev_xyz")
        assert dev is not None
        assert dev.has_scope("admin") is True

    def test_from_settings_plaintext_fallback(self):
        manager = ApiKeyManager.from_settings("sk_legacy_key")
        
        key = manager.validate("sk_legacy_key")
        assert key is not None
        assert key.has_scope("admin") is True

    def test_from_settings_empty(self):
        manager = ApiKeyManager.from_settings("")
        assert len(manager.list_keys()) == 0

    def test_generate_key_format(self):
        key = ApiKeyManager.generate_key(prefix="sk", length=16)
        assert key.startswith("sk_")
        assert len(key) > 20  # prefix + underscore + base64 token

    def test_stats(self):
        manager = ApiKeyManager()
        manager.add_key("key1", scopes={"read"})
        manager.add_key("key2", scopes={"write"})
        manager.add_key(
            "key3",
            scopes={"admin"},
            expires_at=datetime.now(timezone.utc) - timedelta(hours=1),
        )
        
        stats = manager.get_stats()
        assert stats["total_keys"] == 3
        assert stats["active_keys"] == 2
        assert stats["expired_keys"] == 1
        assert stats["by_scope"]["read"] == 1
        assert stats["by_scope"]["write"] == 1
        assert stats["by_scope"]["admin"] == 1

    def test_validate_or_raise_success(self):
        manager = ApiKeyManager()
        manager.add_key("sk_test_123", scopes={"read"})
        
        result = manager.validate_or_raise("sk_test_123")
        assert result is not None

    def test_validate_or_raise_failure(self):
        manager = ApiKeyManager()
        
        with pytest.raises(ValueError, match="Invalid or expired"):
            manager.validate_or_raise("wrong_key")

    def test_key_hashing_is_deterministic(self):
        manager = ApiKeyManager()
        hash1 = manager._hash_key("my_secret_key")
        hash2 = manager._hash_key("my_secret_key")
        assert hash1 == hash2
        assert hash1 != "my_secret_key"
