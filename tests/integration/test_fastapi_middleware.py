import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from citadel.middleware.fastapi_middleware import setup_tenant_middleware
from citadel.middleware.tenant_context import get_tenant_id

# Create a test app
app = FastAPI()
setup_tenant_middleware(app)

@app.get("/test-endpoint")
async def dummy_endpoint():
    return {"tenant_id": get_tenant_id()}

@app.get("/health")
async def health_endpoint():
    return {"status": "ok"}

client = TestClient(app)

def test_middleware_sets_tenant_context():
    """Test 1: Middleware successfully sets context from header"""
    response = client.get("/test-endpoint", headers={"X-Tenant-ID": "acme_corp"})
    assert response.status_code == 200
    assert response.json()["tenant_id"] == "acme_corp"

def test_middleware_rejects_missing_header():
    """Test 2: Request without header is rejected with 400"""
    response = client.get("/test-endpoint")
    assert response.status_code == 400
    assert "Missing X-Tenant-ID" in response.json()["error"]

def test_middleware_rejects_invalid_tenant_id():
    """Test 3: Invalid tenant_id format is rejected"""
    response = client.get("/test-endpoint", headers={"X-Tenant-ID": "invalid/path"})
    assert response.status_code == 400
    assert "Invalid X-Tenant-ID" in response.json()["error"]

def test_middleware_exempt_paths():
    """Test 4: Exempt paths bypass the check"""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"

def test_middleware_isolation():
    """Test 5: Context doesn't leak across requests"""
    # Just running them sequentially proves basic isolation since Test 1 passed, 
    # but let's just make two different requests
    r1 = client.get("/test-endpoint", headers={"X-Tenant-ID": "t1"})
    assert r1.json()["tenant_id"] == "t1"
    
    r2 = client.get("/test-endpoint", headers={"X-Tenant-ID": "t2"})
    assert r2.json()["tenant_id"] == "t2"
