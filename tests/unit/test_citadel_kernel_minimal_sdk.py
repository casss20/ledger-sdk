"""Tests for minimal Citadel Kernel SDK."""

import sys
import os
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Add minimal SDK package to path
sdk_kernel_path = Path(__file__).parent.parent.parent / "packages" / "sdk-python-kernel"
if str(sdk_kernel_path) not in sys.path:
    sys.path.insert(0, str(sdk_kernel_path))

from citadel_kernel.client import KernelClient


@pytest.mark.asyncio
async def test_kernel_client_initialization():
    """KernelClient initializes with connection parameters."""
    with patch("citadel_kernel.client.CitadelClient") as mock_citadel:
        client = KernelClient(
            base_url="https://api.citadelsdk.com",
            api_key="sk_test",
            actor_id="test-agent",
        )

        assert client._client is not None
        mock_citadel.assert_called_once()


@pytest.mark.asyncio
async def test_kernel_client_execute_delegates_to_citadel_client():
    """execute() delegates to underlying CitadelClient."""
    with patch("citadel_kernel.client.CitadelClient") as mock_citadel_class:
        mock_client = AsyncMock()
        mock_citadel_class.return_value = mock_client

        mock_result = MagicMock()
        mock_result.status = "executed"
        mock_client.execute = AsyncMock(return_value=mock_result)

        client = KernelClient(base_url="http://localhost:8000", api_key="sk_test")
        result = await client.execute(
            action="llm.generate",
            resource="anthropic:claude",
            provider="anthropic",
            model="claude-opus-4-7",
            input_tokens=1000,
            output_tokens=500,
        )

        assert result.status == "executed"
        mock_client.execute.assert_awaited_once()


@pytest.mark.asyncio
async def test_kernel_client_decide_delegates_to_citadel_client():
    """decide() delegates to underlying CitadelClient."""
    with patch("citadel_kernel.client.CitadelClient") as mock_citadel_class:
        mock_client = AsyncMock()
        mock_citadel_class.return_value = mock_client

        mock_result = MagicMock()
        mock_result.status = "dry_run"
        mock_client.decide = AsyncMock(return_value=mock_result)

        client = KernelClient(base_url="http://localhost:8000", api_key="sk_test")
        result = await client.decide(
            action="llm.generate",
            resource="anthropic:claude",
            provider="anthropic",
            model="claude-opus-4-7",
        )

        assert result.status == "dry_run"
        mock_client.decide.assert_awaited_once()


@pytest.mark.asyncio
async def test_kernel_client_export_evidence():
    """export_evidence() fetches decision evidence from API."""
    with patch("citadel_kernel.client.CitadelClient") as mock_citadel_class:
        mock_client = AsyncMock()
        mock_citadel_class.return_value = mock_client

        mock_response = MagicMock()
        mock_response.json.return_value = {
            "decision_id": "dec-123",
            "status": "executed",
            "root_hash": "abc123def456",
            "audit_events": [],
        }
        mock_client._request = AsyncMock(return_value=mock_response)

        client = KernelClient(base_url="http://localhost:8000", api_key="sk_test")
        evidence = await client.export_evidence("dec-123")

        assert evidence["decision_id"] == "dec-123"
        assert evidence["root_hash"] == "abc123def456"
        mock_client._request.assert_awaited_once_with("GET", "/v1/audit/evidence/dec-123")


@pytest.mark.asyncio
async def test_kernel_client_verify_evidence():
    """verify_evidence() verifies decision evidence tampering."""
    with patch("citadel_kernel.client.CitadelClient") as mock_citadel_class:
        mock_client = AsyncMock()
        mock_citadel_class.return_value = mock_client

        mock_response = MagicMock()
        mock_response.json.return_value = {
            "decision_id": "dec-123",
            "verified": True,
            "root_hash": "abc123def456",
            "event_count": 5,
        }
        mock_client._request = AsyncMock(return_value=mock_response)

        client = KernelClient(base_url="http://localhost:8000", api_key="sk_test")
        result = await client.verify_evidence("dec-123")

        assert result["verified"] is True
        assert result["event_count"] == 5
        mock_client._request.assert_awaited_once_with(
            "POST", "/v1/audit/evidence/dec-123/verify"
        )


def test_kernel_client_context_manager():
    """KernelClient works as async context manager."""
    with patch("citadel_kernel.client.CitadelClient"):
        client = KernelClient(base_url="http://localhost:8000", api_key="sk_test")
        assert hasattr(client, "__aenter__")
        assert hasattr(client, "__aexit__")
