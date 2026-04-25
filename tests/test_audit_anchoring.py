"""Tests for audit chain Merkle root anchoring."""

import pytest
import hashlib
import hmac
from datetime import datetime, timezone

from citadel.audit_anchoring import AuditAnchorService, AnchorResult, ChainVerification


class TestAuditAnchorService:
    """Unit tests for Merkle root signing and verification."""

    def test_generate_hmac_key(self):
        key = AuditAnchorService.generate_hmac_key()
        assert len(key) == 32
        assert isinstance(key, bytes)

    def test_sign_and_verify_batch(self):
        # These tests verify the signing logic without a database
        service = AuditAnchorService.__new__(AuditAnchorService)
        service.signing_key = b"secret_key_32_bytes_long_ok!!!"
        service.algorithm = "hmac-sha256"
        service.key_id = "test-key"

        message = b"test_message"
        signature = service._sign(message)
        assert isinstance(signature, str)
        assert len(signature) == 64  # hex-encoded SHA256

        # Verify the signature
        assert service._verify_signature(message, signature) is True

    def test_verify_bad_signature(self):
        service = AuditAnchorService.__new__(AuditAnchorService)
        service.signing_key = b"secret_key_32_bytes_long_ok!!!"
        service.algorithm = "hmac-sha256"

        message = b"test_message"
        bad_sig = "a" * 64
        assert service._verify_signature(message, bad_sig) is False

    def test_compute_merkle_root_logic(self):
        """Test the Merkle root computation logic."""
        # Simulate what compute_merkle_root does
        hashes = ["abc123", "def456", "ghi789"]
        combined = b""
        for h in hashes:
            combined = hashlib.sha256(combined + h.encode()).digest()

        root = combined.hex()
        assert len(root) == 64
        assert root != hashes[0]

    def test_anchor_result_dataclass(self):
        result = AnchorResult(
            root_hash="abcd" * 16,
            from_event_id=1,
            to_event_id=100,
            event_count=100,
            signature="sig123",
            key_id="test-key",
            signed_at=datetime.now(timezone.utc),
        )
        assert result.root_hash == "abcd" * 16
        assert result.event_count == 100

    def test_chain_verification_dataclass(self):
        result = ChainVerification(
            chain_valid=True,
            chain_checked_count=1000,
            chain_broken_at=None,
            merkle_root_valid=True,
            latest_root_hash="abcd" * 16,
            latest_root_signed_at=datetime.now(timezone.utc),
        )
        assert result.chain_valid is True
        assert result.merkle_root_valid is True

    def test_hmac_consistency(self):
        """Same message + key = same signature."""
        service = AuditAnchorService.__new__(AuditAnchorService)
        service.signing_key = b"consistent_key_for_testing!!"
        service.algorithm = "hmac-sha256"

        msg = b"consistent"
        sig1 = service._sign(msg)
        sig2 = service._sign(msg)
        assert sig1 == sig2

    def test_different_messages_different_sigs(self):
        service = AuditAnchorService.__new__(AuditAnchorService)
        service.signing_key = b"consistent_key_for_testing!!"
        service.algorithm = "hmac-sha256"

        sig1 = service._sign(b"message_one")
        sig2 = service._sign(b"message_two")
        assert sig1 != sig2

    def test_different_keys_different_sigs(self):
        service1 = AuditAnchorService.__new__(AuditAnchorService)
        service1.signing_key = b"key_one_for_testing_purposes"
        service1.algorithm = "hmac-sha256"

        service2 = AuditAnchorService.__new__(AuditAnchorService)
        service2.signing_key = b"key_two_for_testing_purposes"
        service2.algorithm = "hmac-sha256"

        msg = b"same_message"
        sig1 = service1._sign(msg)
        sig2 = service2._sign(msg)
        assert sig1 != sig2
