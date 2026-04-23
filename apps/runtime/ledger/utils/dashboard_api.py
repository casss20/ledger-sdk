"""
Dashboard API — Ledger SDK

REST API endpoints for dashboard consumption.
Serves Governor data, analytics, and real-time updates.
"""

from typing import Optional, List
from datetime import datetime, timedelta

# Optional FastAPI integration
try:
    from fastapi import APIRouter, Query, HTTPException
    from fastapi.responses import JSONResponse
    HAS_FASTAPI = True
except ImportError:
    HAS_FASTAPI = False

from .governor import get_governor, ActionState
from .analytics import get_analytics, get_profiler, TimeWindow


class DashboardAPI:
    """
    Dashboard API endpoints for Ledger SDK.
    
    Provides:
    - Real-time action state queries
    - Analytics and anomaly alerts
    - Agent health checks
    - Historical data
    """
    
    def __init__(self):
        self.governor = get_governor()
        self.analytics = get_analytics()
        self.profiler = get_profiler()
    
    def get_routes(self):
        """Get API routes (dict format for any framework)."""
        return {
            "/dashboard/summary": {
                "method": "GET",
                "handler": self.get_summary,
                "description": "Executive summary of all actions"
            },
            "/dashboard/pending": {
                "method": "GET", 
                "handler": self.get_pending,
                "description": "Actions awaiting approval"
            },
            "/dashboard/failed": {
                "method": "GET",
                "handler": self.get_failed,
                "description": "Recently failed actions"
            },
            "/dashboard/anomalies": {
                "method": "GET",
                "handler": self.get_anomalies,
                "description": "Detected anomalies in last hour"
            },
            "/dashboard/agent/{agent}/health": {
                "method": "GET",
                "handler": self.get_agent_health,
                "description": "Health check for specific agent"
            },
            "/dashboard/actions/{action_id}": {
                "method": "GET",
                "handler": self.get_action_details,
                "description": "Detailed view of specific action"
            },
        }
    
    async def get_summary(self) -> dict:
        """Executive summary for dashboard landing page."""
        summary = self.governor.get_summary()
        
        # Add last hour analytics
        window = TimeWindow.last_hour()
        metrics = await self.analytics.analyze_window(window)
        analytics_summary = self.analytics.get_summary(metrics)
        
        return {
            "governor": summary,
            "analytics": analytics_summary,
            "timestamp": datetime.utcnow().isoformat()
        }
    
    async def get_pending(
        self,
        limit: int = 100
    ) -> List[dict]:
        """Get pending approvals."""
        pending = self.governor.list_pending()
        return [p.to_dict() for p in pending[:limit]]
    
    async def get_failed(
        self,
        hours: int = 24,
        limit: int = 100
    ) -> List[dict]:
        """Get recently failed actions."""
        failed = self.governor.list_failed()
        
        # Filter by time
        cutoff = datetime.utcnow() - timedelta(hours=hours)
        recent = [f for f in failed if f.created_at > cutoff]
        
        return [f.to_dict() for f in recent[:limit]]
    
    async def get_anomalies(
        self,
        hours: int = 1
    ) -> dict:
        """Get anomalies detected in recent window."""
        window = TimeWindow(
            datetime.utcnow() - timedelta(hours=hours),
            datetime.utcnow()
        )
        
        metrics = await self.analytics.analyze_window(window)
        
        anomalous = [
            {
                "action": action,
                "reasons": m.anomaly_reasons,
                "metrics": {
                    "total": m.total,
                    "failed": m.failed,
                    "success_rate": m.success / m.total if m.total > 0 else 0,
                }
            }
            for action, m in metrics.items()
            if m.is_anomalous
        ]
        
        return {
            "window_hours": hours,
            "anomaly_count": len(anomalous),
            "anomalies": anomalous
        }
    
    async def get_agent_health(
        self,
        agent: str,
        hours: int = 1
    ) -> dict:
        """Health check for specific agent."""
        window = TimeWindow(
            datetime.utcnow() - timedelta(hours=hours),
            datetime.utcnow()
        )
        
        return await self.analytics.check_agent_health(agent, window)
    
    async def get_action_details(
        self,
        action_id: str
    ) -> dict:
        """Get detailed view of specific action."""
        record = self.governor.get(action_id)
        if not record:
            return {"error": "Action not found"}
        
        return {
            "record": record.to_dict(),
            "timeline": self._build_timeline(record)
        }
    
    def _build_timeline(self, record) -> List[dict]:
        """Build execution timeline for an action."""
        timeline = []
        
        timeline.append({
            "time": record.created_at.isoformat(),
            "event": "created",
            "state": record.state.value
        })
        
        if record.started_at:
            timeline.append({
                "time": record.started_at.isoformat(),
                "event": "started_execution"
            })
        
        if record.completed_at:
            timeline.append({
                "time": record.completed_at.isoformat(),
                "event": "completed",
                "duration_ms": record.duration_ms()
            })
        
        return timeline


# FastAPI router (if available)
if HAS_FASTAPI:
    router = APIRouter(prefix="/dashboard", tags=["dashboard"])
    api = DashboardAPI()
    
    @router.get("/summary")
    async def dashboard_summary():
        """Executive summary for dashboard."""
        return await api.get_summary()
    
    @router.get("/pending")
    async def dashboard_pending(limit: int = Query(100, ge=1, le=1000)):
        """Pending approvals."""
        return await api.get_pending(limit=limit)
    
    @router.get("/failed")
    async def dashboard_failed(
        hours: int = Query(24, ge=1, le=168),
        limit: int = Query(100, ge=1, le=1000)
    ):
        """Recently failed actions."""
        return await api.get_failed(hours=hours, limit=limit)
    
    @router.get("/anomalies")
    async def dashboard_anomalies(hours: int = Query(1, ge=1, le=24)):
        """Detected anomalies."""
        return await api.get_anomalies(hours=hours)
    
    @router.get("/agent/{agent}/health")
    async def agent_health(agent: str, hours: int = Query(1, ge=1, le=24)):
        """Agent health check."""
        return await api.get_agent_health(agent, hours=hours)
    
    @router.get("/actions/{action_id}")
    async def action_details(action_id: str):
        """Action details."""
        result = await api.get_action_details(action_id)
        if "error" in result:
            raise HTTPException(status_code=404, detail=result["error"])
        return result


def create_dashboard_api():
    """Factory for dashboard API."""
    return DashboardAPI()


def get_fastapi_router():
    """Get FastAPI router (if FastAPI installed)."""
    if HAS_FASTAPI:
        return router
    raise ImportError("FastAPI not installed. Install with: pip install fastapi")


__all__ = [
    'DashboardAPI',
    'create_dashboard_api',
    'get_fastapi_router',
]
