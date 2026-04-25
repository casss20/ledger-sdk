"""
Tests for CITADEL SDK — @governed decorator integration.
"""

import os
import pytest
import pytest_asyncio

from citadel import Citadel, Denied


# Skip audit-dependent tests if no Postgres
has_postgres = os.getenv("AUDIT_DSN") is not None


@pytest_asyncio.fixture
async def citadel():
    dsn = os.getenv("AUDIT_DSN", "postgres://postgres:password@localhost/postgres")
    gov = Citadel(audit_dsn=dsn, agent="test")
    await gov.start()
    
    # Approval hook that approves everything
    gov.set_approval_hook(lambda ctx: True)
    
    yield gov
    await gov.stop()


@pytest.mark.asyncio
async def test_governed_decorator_executes(citadel):
    """@governed decorator allows execution with approval hook."""
    
    @citadel.governed(action="test_action", resource="test_resource")
    async def test_func(x):
        return {"result": x * 2}
    
    result = await test_func(5)
    assert result["result"] == 10


@pytest.mark.asyncio
async def test_kill_switch_blocks(citadel):
    """Kill switch blocks execution before approval hook."""
    citadel.killsw.register("test_feature", enabled=True)
    
    @citadel.governed(action="publish", resource="blog", flag="test_feature")
    async def publish_post(title):
        return {"published": title}
    
    # First call works
    result = await publish_post("Hello")
    assert result["published"] == "Hello"
    
    # Kill the feature
    citadel.killsw.kill("test_feature", reason="test")
    
    # Second call blocked
    with pytest.raises(Denied) as exc:
        await publish_post("World")
    
    assert "killed" in str(exc.value)


@pytest.mark.asyncio
async def test_no_approval_hook_blocks_hard_risk(citadel):
    """HARD risk actions blocked without approval hook."""
    # Remove approval hook
    citadel.set_approval_hook(None)
    
    @citadel.governed(action="delete", resource="database")
    async def delete_db():
        return {"deleted": True}
    
    with pytest.raises(Denied) as exc:
        await delete_db()
    
    assert "no_hook" in str(exc.value)


@pytest.mark.asyncio
async def test_build_prompt(citadel):
    """Can build system prompt for task."""
    prompt = citadel.build_prompt("Research quantum computing", session_id="test-123")
    
    assert "CONSTITUTION" in prompt or len(prompt) > 0


@pytest.mark.asyncio
@pytest.mark.skipif(not has_postgres, reason="No Postgres available")
async def test_audit_logged(citadel):
    """Actions are logged to audit."""
    
    @citadel.governed(action="research", resource="topic")
    async def do_research(topic):
        return {"topic": topic}
    
    await do_research("AI governance")
    
    # Verify audit has entries
    ok, count = await citadel.audit.verify_integrity()
    assert ok is True
    assert count > 0