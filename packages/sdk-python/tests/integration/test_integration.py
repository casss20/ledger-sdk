"""Sample integration tests.

These hit a real backend. Run only when you have a live server.
"""

import pytest

from citadel_governance import CitadelClient

pytestmark = pytest.mark.integration


@pytest.mark.asyncio
async def test_integration_health(base_url, api_key):
    """Smoke test: can we reach the dashboard stats endpoint?"""
    async with CitadelClient(base_url=base_url, api_key=api_key) as client:
        stats = await client.get_stats()
        assert isinstance(stats.pending_approvals, int)


@pytest.mark.asyncio
async def test_integration_execute_and_get_action(base_url, api_key):
    """End-to-end: execute an action, then fetch it by ID."""
    async with CitadelClient(base_url=base_url, api_key=api_key, actor_id="integration-test") as client:
        result = await client.execute(
            action="integration.test",
            resource="test:123",
            payload={"hello": "world"},
        )
        assert result.action_id is not None

        fetched = await client.get_action(result.action_id)
        assert fetched["action_id"] == result.action_id
