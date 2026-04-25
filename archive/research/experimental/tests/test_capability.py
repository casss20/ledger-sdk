"""
Tests for capability tokens — issue, verify, consume, revoke.
"""

import asyncio
import time
import pytest

from governance.capability import CapabilityIssuer


@pytest.fixture
def issuer():
    return CapabilityIssuer()


def test_issue_capability(issuer):
    """Can issue a capability token."""
    cap = issuer.issue(
        action="send_message",
        resource="email",
        ttl_seconds=300,
        max_uses=1,
        issued_to="test_agent"
    )
    
    assert cap.token is not None
    assert cap.action == "send_message"
    assert cap.resource == "email"
    assert cap.max_uses == 1
    assert cap.issued_to == "test_agent"


def test_verify_valid_capability(issuer):
    """Valid token passes verification."""
    cap = issuer.issue(
        action="send_message",
        resource="email",
        ttl_seconds=300,
        max_uses=1
    )
    
    valid, reason = issuer.verify(cap.token, "send_message", "email")
    assert valid is True
    assert reason == "ok"


def test_verify_wrong_action(issuer):
    """Token for wrong action fails verification."""
    cap = issuer.issue(action="send_message", resource="email")
    
    valid, reason = issuer.verify(cap.token, "delete", "email")
    assert valid is False
    assert reason == "action_mismatch"


def test_verify_wrong_resource(issuer):
    """Token for wrong resource fails verification."""
    cap = issuer.issue(action="send_message", resource="email")
    
    valid, reason = issuer.verify(cap.token, "send_message", "sms")
    assert valid is False
    assert reason == "resource_mismatch"


def test_verify_unknown_token(issuer):
    """Unknown token fails verification."""
    valid, reason = issuer.verify("invalid_token", "send", "email")
    assert valid is False
    assert reason == "unknown"


def test_capability_expiry(issuer):
    """Expired token fails verification."""
    cap = issuer.issue(
        action="send_message",
        resource="email",
        ttl_seconds=0,  # Already expired
        max_uses=1
    )
    
    time.sleep(0.1)  # Small delay to ensure expiry
    
    valid, reason = issuer.verify(cap.token, "send_message", "email")
    assert valid is False
    assert reason == "expired"


def test_capability_max_uses(issuer):
    """Token exhausted after max uses."""
    cap = issuer.issue(
        action="send_message",
        resource="email",
        max_uses=2
    )
    
    # First use
    valid, _ = issuer.verify(cap.token, "send_message", "email")
    assert valid is True
    issuer.consume(cap.token)
    
    # Second use
    valid, _ = issuer.verify(cap.token, "send_message", "email")
    assert valid is True
    issuer.consume(cap.token)
    
    # Third use — exhausted
    valid, reason = issuer.verify(cap.token, "send_message", "email")
    assert valid is False
    assert reason == "exhausted"


def test_revoke_capability(issuer):
    """Revoked token fails verification."""
    cap = issuer.issue(action="send_message", resource="email")
    
    issuer.revoke(cap.token)
    
    valid, reason = issuer.verify(cap.token, "send_message", "email")
    assert valid is False
    assert reason == "revoked"
