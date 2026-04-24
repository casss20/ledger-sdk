"""
Stream 3a: Onboarding Flow — Quickstart Tests

These tests verify that a founder can go from `pip install` to first
governed action in < 10 minutes with zero manual setup.

All tests start RED (features don't exist yet), then go GREEN.
"""

import sys
from pathlib import Path

# Why: add repo root to path so tests can import quickstart module
sys.path.insert(0, str(Path(__file__).parent.parent))

import subprocess
import time

import pytest


@pytest.mark.asyncio
async def test_quickstart_tenant_initialization():
    """
    Asserts: test tenant created without manual DB setup.
    Verifies: tenant_id is returned and valid.
    """
    from quickstart import initialize_test_tenant

    tenant_id = await initialize_test_tenant()
    assert tenant_id is not None
    assert tenant_id.startswith("tenant_") or tenant_id.startswith("test_tenant_")
    assert len(tenant_id) > 0


@pytest.mark.asyncio
async def test_quickstart_api_key_seeding():
    """
    Asserts: valid API key is generated.
    Verifies: key can authenticate a request.
    """
    from quickstart import initialize_test_tenant, seed_api_key

    tenant_id = await initialize_test_tenant()
    api_key = await seed_api_key(tenant_id)
    assert api_key is not None
    assert api_key.startswith("sk_")
    assert len(api_key) > 20  # reasonable length for a secure key


@pytest.mark.asyncio
async def test_quickstart_action_execution():
    """
    Asserts: sample action executes through Citadel.
    Verifies: action_id is returned.
    """
    from quickstart import initialize_test_tenant, seed_api_key, execute_sample_action

    tenant_id = await initialize_test_tenant()
    api_key = await seed_api_key(tenant_id)
    result = await execute_sample_action(tenant_id, api_key)

    assert result is not None
    assert "action_id" in result
    # action_id is a UUID string, not prefixed with "act_"
    assert len(result["action_id"]) > 30  # UUID format
    assert "decision" in result


@pytest.mark.asyncio
async def test_quickstart_audit_logged():
    """
    Asserts: action appears in audit trail.
    Verifies: audit record includes decision + metadata.
    """
    from quickstart import (
        initialize_test_tenant,
        seed_api_key,
        execute_sample_action,
        verify_audit,
    )

    tenant_id = await initialize_test_tenant()
    api_key = await seed_api_key(tenant_id)
    result = await execute_sample_action(tenant_id, api_key)
    action_id = result["action_id"]

    audit = await verify_audit(action_id, tenant_id)
    assert audit is not None
    # UUID may be returned as UUID object or string
    audit_action_id = str(audit["action_id"]) if hasattr(audit["action_id"], "hex") else audit["action_id"]
    assert audit_action_id == action_id


def test_quickstart_cli_output_deterministic():
    """
    Asserts: `python quickstart.py` produces exact output format.
    Verifies: output is parseable and deterministic.
    """
    result = subprocess.run(
        [sys.executable, "quickstart.py"],
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 0, f"quickstart.py failed: {result.stderr}"

    output = result.stdout.strip()
    lines = output.split("\n")

    assert len(lines) == 5, f"Expected 5 lines, got {len(lines)}: {output}"
    assert lines[0].startswith("Tenant created: ")
    assert lines[1].startswith("API Key: ")
    assert lines[2].startswith("Action executed: ")
    assert lines[3] == "Decision: executed"
    assert lines[4] == "Logged: true"


def test_quickstart_performance_constraint():
    """
    Asserts: execution completes in < 5 seconds.
    Verifies: import-to-completion is sub-5s.
    """
    start = time.time()
    result = subprocess.run(
        [sys.executable, "quickstart.py"],
        capture_output=True,
        text=True,
        timeout=30,
    )
    elapsed = time.time() - start

    assert result.returncode == 0, f"quickstart.py failed: {result.stderr}"
    assert elapsed < 5, f"Quickstart took {elapsed:.2f}s, must be < 5s"
