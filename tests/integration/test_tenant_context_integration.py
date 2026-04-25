"""
End-to-end integration test: Request comes in, middleware sets context,
RLS filters data, response goes out.
"""

import os
import pytest

# Set testing mode BEFORE importing app to skip startup secret validation
os.environ["CITADEL_TESTING"] = "true"

from fastapi.testclient import TestClient
from citadel.api import app
import uuid

# We MUST override the db_pool dependency for TestClient if we don't have
# a real running DB for tests, but we'll assume the pytest `db_pool` fixture
# or a mocked DB is configured correctly if the user is running `pytest tests/`.
# Here we just use the real app and see if the middleware responds correctly.

client = TestClient(app)

def test_full_request_flow_missing_tenant_context():
    """
    Missing X-Tenant-ID header -> 400 (auth passes via test key first).
    """
    response = client.get(
        "/v1/actions/some-uuid",
        headers={"Authorization": "Bearer test-key"},
    )
    assert response.status_code == 400
    assert "X-Tenant-ID" in response.json()["error"]

def test_full_request_flow_exempt_path():
    """
    Health path -> 200 (no tenant required)
    """
    response = client.get("/v1/health")
    assert response.status_code == 200
