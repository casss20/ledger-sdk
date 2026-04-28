"""
Tests for Phase 1 governance visibility endpoints:
- Decision lineage API
- Approval queue metrics
- Admin capacity endpoint
"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from datetime import datetime, timezone
import uuid

from fastapi.testclient import TestClient
from fastapi import FastAPI

from citadel.execution.kernel import Kernel

TENANT = "test_tenant"


def _make_mock_kernel(repo_methods: dict):
    """Build a mock kernel with a mock repo that has the given async methods."""
    kernel = MagicMock(spec=Kernel)
    repo = MagicMock()
    for name, return_value in repo_methods.items():
        setattr(repo, name, AsyncMock(return_value=return_value))
    kernel.repo = repo
    return kernel


def _make_test_app(mock_kernel):
    app = FastAPI(lifespan=lambda app: (yield))  # bypass lifespan startup

    async def _get_kernel():
        return mock_kernel

    async def _require_api_key():
        return "test-api-key"

    # Override the dependency functions used by routers
    from citadel.api.dependencies import get_kernel as real_get_kernel
    from citadel.api.dependencies import require_api_key as real_require_api_key

    app.dependency_overrides[real_get_kernel] = _get_kernel
    app.dependency_overrides[real_require_api_key] = _require_api_key

    # Import routers fresh to pick up dependency overrides
    from citadel.api.routers.decisions import router as decisions_router
    from citadel.api.routers.approvals import router as approvals_router
    from citadel.api.routers.admin import router as admin_router

    app.include_router(decisions_router, prefix="/v1")
    app.include_router(approvals_router, prefix="/v1")
    app.include_router(admin_router, prefix="/v1")
    return app


class TestDecisionLineage:
    """GET /v1/decisions/{id}/lineage"""

    @pytest.fixture
    def client(self):
        decision_id = uuid.uuid4()
        parent_id = uuid.uuid4()
        nodes = [
            {
                "decision_id": decision_id,
                "action_id": uuid.uuid4(),
                "parent_decision_id": parent_id,
                "root_decision_id": parent_id,
                "trace_id": "trace-1",
                "workflow_id": "wf-1",
                "status": "allowed",
                "winning_rule": "allow",
                "reason": "test",
                "risk_level": "low",
                "risk_score": 1,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "depth_level": 0,
            },
            {
                "decision_id": parent_id,
                "action_id": uuid.uuid4(),
                "parent_decision_id": None,
                "root_decision_id": parent_id,
                "trace_id": "trace-1",
                "workflow_id": "wf-1",
                "status": "allowed",
                "winning_rule": "allow",
                "reason": "root",
                "risk_level": "low",
                "risk_score": 1,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "depth_level": 1,
            },
        ]
        mock_kernel = _make_mock_kernel({"get_decision_lineage": nodes})
        app = _make_test_app(mock_kernel)
        return TestClient(app)

    def test_lineage_returns_nodes(self, client):
        decision_id = uuid.uuid4()
        response = client.get(f"/v1/decisions/{decision_id}/lineage")
        assert response.status_code == 200
        data = response.json()
        assert data["node_count"] == 2
        assert len(data["nodes"]) == 2
        assert data["nodes"][0]["depth_level"] == 0
        assert data["nodes"][1]["depth_level"] == 1

    def test_lineage_depth_param(self, client):
        decision_id = uuid.uuid4()
        response = client.get(f"/v1/decisions/{decision_id}/lineage?depth=3")
        assert response.status_code == 200

    def test_lineage_not_found(self, client):
        """Empty result from repo → 404."""
        mock_kernel = _make_mock_kernel({"get_decision_lineage": []})
        app = _make_test_app(mock_kernel)
        client = TestClient(app)
        decision_id = uuid.uuid4()
        response = client.get(f"/v1/decisions/{decision_id}/lineage")
        assert response.status_code == 404


class TestDecisionDescendants:
    """GET /v1/decisions/{id}/descendants"""

    @pytest.fixture
    def client(self):
        decision_id = uuid.uuid4()
        child_id = uuid.uuid4()
        nodes = [
            {
                "decision_id": decision_id,
                "action_id": uuid.uuid4(),
                "parent_decision_id": None,
                "root_decision_id": decision_id,
                "trace_id": "trace-1",
                "workflow_id": "wf-1",
                "status": "allowed",
                "winning_rule": "allow",
                "reason": "root",
                "risk_level": "low",
                "risk_score": 1,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "depth_level": 0,
            },
            {
                "decision_id": child_id,
                "action_id": uuid.uuid4(),
                "parent_decision_id": decision_id,
                "root_decision_id": decision_id,
                "trace_id": "trace-1",
                "workflow_id": "wf-1",
                "status": "allowed",
                "winning_rule": "allow",
                "reason": "child",
                "risk_level": "low",
                "risk_score": 1,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "depth_level": 1,
            },
        ]
        mock_kernel = _make_mock_kernel({"get_decision_descendants": nodes})
        app = _make_test_app(mock_kernel)
        return TestClient(app)

    def test_descendants_returns_nodes(self, client):
        decision_id = uuid.uuid4()
        response = client.get(f"/v1/decisions/{decision_id}/descendants")
        assert response.status_code == 200
        data = response.json()
        assert data["node_count"] == 2
        assert data["nodes"][1]["parent_decision_id"] == str(data["nodes"][0]["decision_id"])


class TestWorkflowTree:
    """GET /v1/decisions/workflows/{id}/tree"""

    @pytest.fixture
    def client(self):
        nodes = [
            {
                "decision_id": uuid.uuid4(),
                "action_id": uuid.uuid4(),
                "parent_decision_id": None,
                "root_decision_id": None,
                "trace_id": "t1",
                "workflow_id": "wf-1",
                "status": "allowed",
                "winning_rule": "allow",
                "reason": "step 1",
                "risk_level": "low",
                "risk_score": 1,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "depth_level": 0,
            },
            {
                "decision_id": uuid.uuid4(),
                "action_id": uuid.uuid4(),
                "parent_decision_id": None,
                "root_decision_id": None,
                "trace_id": "t2",
                "workflow_id": "wf-1",
                "status": "allowed",
                "winning_rule": "allow",
                "reason": "step 2",
                "risk_level": "low",
                "risk_score": 1,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "depth_level": 0,
            },
        ]
        mock_kernel = _make_mock_kernel({"get_workflow_tree": nodes})
        app = _make_test_app(mock_kernel)
        return TestClient(app)

    def test_workflow_tree_returns_nodes(self, client):
        response = client.get("/v1/decisions/workflows/wf-1/tree")
        assert response.status_code == 200
        data = response.json()
        assert data["workflow_id"] == "wf-1"
        assert data["node_count"] == 2


class TestApprovalQueueMetrics:
    """GET /v1/approvals/queue-metrics"""

    @pytest.fixture
    def client(self):
        metrics = {
            "queue_depth": 5,
            "avg_wait_seconds": 120.0,
            "throughput_per_hour": 12,
            "avg_service_seconds": 45.0,
            "arrival_rate_per_hour": 15,
            "implied_arrival_rate_per_second": 0.11,
            "observed_load_factor": 2.67,
            "computed_at": datetime.now(timezone.utc).isoformat(),
        }
        mock_kernel = _make_mock_kernel({"get_approval_queue_metrics": metrics})
        app = _make_test_app(mock_kernel)
        return TestClient(app)

    def test_queue_metrics_returns_keys(self, client):
        response = client.get("/v1/approvals/queue-metrics")
        assert response.status_code == 200
        data = response.json()
        assert data["queue_depth"] == 5
        assert data["avg_wait_seconds"] == 120.0
        assert data["arrival_rate_per_hour"] == 15
        assert "computed_at" in data


class TestAdminCapacity:
    """GET /v1/admin/capacity"""

    @pytest.fixture
    def client(self):
        metrics = {
            "queue_depth": 10,
            "avg_wait_seconds": 300.0,
            "throughput_per_hour": 8,
            "avg_service_seconds": 120.0,
            "arrival_rate_per_hour": 20,
            "implied_arrival_rate_per_second": 0.083,
            "observed_load_factor": 2.5,
            "computed_at": datetime.now(timezone.utc).isoformat(),
        }
        mock_kernel = _make_mock_kernel({"get_approval_queue_metrics": metrics})
        app = _make_test_app(mock_kernel)
        return TestClient(app)

    def test_capacity_returns_estimate(self, client):
        response = client.get("/v1/admin/capacity")
        assert response.status_code == 200
        data = response.json()["capacity"]
        assert "estimated_approvers_needed" in data
        assert data["current_queue_depth"] == 10
        assert data["avg_wait_seconds"] == 300.0
        assert data["throughput_per_hour"] == 8
        assert data["arrival_rate_per_hour"] == 20
        assert data["utilization_factor"] == 2.5
        assert "recommendation" in data
        assert "computed_at" in data

    def test_capacity_recommendation_elevated(self, client):
        """Load factor > 2.0 should trigger critical recommendation."""
        response = client.get("/v1/admin/capacity")
        assert response.status_code == 200
        data = response.json()["capacity"]
        assert "critical" in data["recommendation"].lower()
