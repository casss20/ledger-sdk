"""Tests for gt_ governance token generation and properties."""

import hashlib

import pytest

from ledger.tokens import GovernanceToken, TokenType, _base62_encode, _canonical_json


class TestTokenGenerationFormat:
    def test_token_format(self):
        """Token ID must match gt_<type>_<random> format."""
        token = GovernanceToken.generate(
            token_type=TokenType.POLICY_DECISION,
            tenant_id="tnt_test",
            decision_trace={"action": "file.write"},
        )
        assert token.token_id.startswith("gt_pol_")
        parts = token.token_id.split("_")
        assert len(parts) == 3
        assert parts[0] == "gt"
        assert parts[1] == "pol"
        assert len(parts[2]) > 20  # base62 of 32 bytes is ~43 chars

    def test_all_token_types(self):
        """Each token type has correct prefix."""
        expected = {
            TokenType.POLICY_DECISION: "gt_pol_",
            TokenType.APPROVAL: "gt_apr_",
            TokenType.AUDIT_EVENT: "gt_aud_",
            TokenType.KILL_SWITCH: "gt_kil_",
            TokenType.AUTHORITY_DELEGATION: "gt_del_",
        }
        for ttype, prefix in expected.items():
            token = GovernanceToken.generate(
                token_type=ttype,
                tenant_id="tnt_test",
                decision_trace={"test": True},
            )
            assert token.token_id.startswith(prefix)


class TestTokenUniqueness:
    def test_cryptographic_randomness(self):
        """Generating 100 tokens should produce 100 unique IDs."""
        tokens = [
            GovernanceToken.generate(
                token_type=TokenType.AUDIT_EVENT,
                tenant_id="tnt_test",
                decision_trace={"seq": i},
            )
            for i in range(100)
        ]
        ids = [t.token_id for t in tokens]
        assert len(set(ids)) == 100


class TestContentHashDeterministic:
    def test_same_payload_same_hash(self):
        """JCS canonicalization produces deterministic hash."""
        payload = {"b": 2, "a": 1}
        t1 = GovernanceToken.generate(
            token_type=TokenType.POLICY_DECISION,
            tenant_id="tnt_test",
            decision_trace=payload,
        )
        t2 = GovernanceToken.generate(
            token_type=TokenType.POLICY_DECISION,
            tenant_id="tnt_test",
            decision_trace=payload,
        )
        # Same payload should produce same content hash
        assert t1.content_hash == t2.content_hash

    def test_different_payload_different_hash(self):
        """Different payloads produce different hashes."""
        t1 = GovernanceToken.generate(
            token_type=TokenType.POLICY_DECISION,
            tenant_id="tnt_test",
            decision_trace={"action": "read"},
        )
        t2 = GovernanceToken.generate(
            token_type=TokenType.POLICY_DECISION,
            tenant_id="tnt_test",
            decision_trace={"action": "write"},
        )
        assert t1.content_hash != t2.content_hash


class TestChainHashLinksToPrevious:
    def test_first_token_chain_equals_content(self):
        """First token in chain: chain_hash == content_hash."""
        token = GovernanceToken.generate(
            token_type=TokenType.AUDIT_EVENT,
            tenant_id="tnt_test",
            decision_trace={"event": "test"},
        )
        assert token.chain_hash == token.content_hash

    def test_chained_token_links_correctly(self):
        """Token with previous_hash produces different chain_hash."""
        first = GovernanceToken.generate(
            token_type=TokenType.AUDIT_EVENT,
            tenant_id="tnt_test",
            decision_trace={"event": 1},
        )
        second = GovernanceToken.generate(
            token_type=TokenType.AUDIT_EVENT,
            tenant_id="tnt_test",
            decision_trace={"event": 2},
            previous_hash=first.chain_hash,
        )
        assert second.chain_hash != second.content_hash
        # Verify chain hash computation
        expected = hashlib.sha256(
            f"{second.content_hash}||{first.chain_hash}".encode()
        ).hexdigest()
        assert second.chain_hash == expected


class TestTokenNonPortable:
    def test_public_dict_excludes_trace(self):
        """Public representation does NOT include decision trace."""
        token = GovernanceToken.generate(
            token_type=TokenType.POLICY_DECISION,
            tenant_id="tnt_test",
            decision_trace={"secret": "data"},
        )
        public = token.to_public_dict()
        assert "secret" not in str(public)
        assert "decision_trace" not in public
        assert "_decision_trace" not in public

    def test_decision_trace_readable(self):
        """Decision trace accessible via property."""
        trace = {"action": "test", "result": "allowed"}
        token = GovernanceToken.generate(
            token_type=TokenType.POLICY_DECISION,
            tenant_id="tnt_test",
            decision_trace=trace,
        )
        assert token.decision_trace == trace
