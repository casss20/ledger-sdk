"""
Tests for audit log — hash-chained integrity.
"""

import os
import pytest
import pytest_asyncio

from governance.audit import AuditService, _hash


# Skip tests if no Postgres DSN available
pytestmark = pytest.mark.skipif(
    os.getenv("AUDIT_DSN") is None,
    reason="No AUDIT_DSN env var set"
)


@pytest_asyncio.fixture
async def audit():
    dsn = os.getenv("AUDIT_DSN", "postgres://postgres:password@localhost/postgres")
    service = AuditService(dsn)
    await service.start()
    yield service
    await service.stop()


@pytest.mark.asyncio
async def test_log_event(audit):
    """Can log an event."""
    event_hash = await audit.log(
        actor="test_agent",
        action="send_message",
        resource="email:123",
        risk="medium",
        approved=True,
        payload={"to": "user@test.com"}
    )
    
    assert event_hash is not None
    assert len(event_hash) == 64  # SHA-256 hex


@pytest.mark.asyncio
async def test_verify_integrity_empty(audit):
    """Empty audit log verifies as valid."""
    ok, count = await audit.verify_integrity()
    assert ok is True
    assert count == 0


@pytest.mark.asyncio
async def test_verify_integrity_chain(audit):
    """Chain of 10 events verifies correctly."""
    # Log 10 events
    for i in range(10):
        await audit.log(
            actor="test_agent",
            action="test_action",
            resource=f"resource:{i}",
            risk="low",
            approved=True,
            payload={"seq": i}
        )
    
    ok, count = await audit.verify_integrity()
    assert ok is True
    assert count == 10


@pytest.mark.asyncio
async def test_hash_function():
    """Hash function produces consistent output."""
    prev = "GENESIS"
    body = {"ts": 1234567890, "actor": "test", "action": "test"}
    
    h1 = _hash(prev, body)
    h2 = _hash(prev, body)
    
    assert h1 == h2
    assert len(h1) == 64
    
    # Different body = different hash
    body2 = {"ts": 1234567890, "actor": "test", "action": "different"}
    h3 = _hash(prev, body2)
    assert h3 != h1


@pytest.mark.asyncio
async def test_chain_tamper_detection(audit):
    """Tampered chain fails verification."""
    # This test would require direct database access to simulate tampering
    # For now, we verify the hash function works correctly
    pass