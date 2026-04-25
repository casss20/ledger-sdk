
"""Tests for the synchronous CitadelClient wrapper."""

import httpx
import pytest
import respx

from citadel_governance import ActionBlocked
from citadel_governance.sync import CitadelClient as SyncClient

@respx.mock
def test_sync_execute():
    client = SyncClient(base_url="https://api.citadelsdk.com", api_key="k")
    route = respx.post("https://api.citadelsdk.com/v1/actions/execute").mock(
        return_value=httpx.Response(200, json={
            "action_id": "act-1",
            "status": "executed",
            "winning_rule": "allow",
            "reason": "OK",
            "executed": True,
        })
    )
    result = client.execute(action="test", resource="r")
    assert result.status == "executed"
    assert route.called
    client.close()

@respx.mock
def test_sync_guard_decorator():
    client = SyncClient(base_url="https://api.citadelsdk.com", api_key="k")
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
    def my_func():
        return "sync success"

    assert my_func() == "sync success"
    client.close()

@respx.mock
def test_sync_guard_blocked():
    client = SyncClient(base_url="https://api.citadelsdk.com", api_key="k")
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
    def my_func():
        return "should not reach"

    with pytest.raises(ActionBlocked):
        my_func()
    client.close()

def test_sync_context_manager():
    with SyncClient(base_url="https://api.citadelsdk.com", api_key="k") as client:
        assert client._async_client.api_key == "k"
