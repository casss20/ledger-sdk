"""
GOVERNOR â€” Central visibility and control plane for Citadel SDK

The GOVERNOR is the single source of truth for:
- What actions are pending (awaiting approval)
- What actions were skipped (null propagation)
- What actions failed (error tracking)
- What actions completed (audit trail)
- What's deferred to later (scheduler integration)

Like Weft's "orchestrator" but for governance state.
"""

from typing import Any, Dict, List, Optional, Set
from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum
import asyncio
import logging

logger = logging.getLogger(__name__)


class ActionState(Enum):
    """Lifecycle states for governed actions."""
    PENDING = "pending"          # Awaiting approval
    DEFERRED = "deferred"        # Scheduled for later
    SKIPPED = "skipped"          # Null propagation skipped this
    EXECUTING = "executing"      # Currently running
    SUCCESS = "success"          # Completed successfully
    FAILED = "failed"            # Exception raised
    DENIED = "denied"            # Kill switch or rejection
    TIMEOUT = "timeout"          # Approval/execution timeout


@dataclass
class ActionRecord:
    """
    Complete record of a governed action's lifecycle.
    Immutable once finalized.
    """
    id: str
    action: str
    resource: str
    state: ActionState
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    
    # Context
    agent: str = "default"
    risk: str = "LOW"
    approval_level: str = "NONE"
    
    # Execution details
    args_preview: str = ""           # First 200 chars of args
    result_preview: str = ""         # First 200 chars of result
    error_message: Optional[str] = None
    
    # Timing
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    
    # Links
    promise_id: Optional[str] = None     # Durable promise if deferred
    parent_id: Optional[str] = None      # For subgraph relationships
    children: List[str] = field(default_factory=list)
    
    # Metadata
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def duration_ms(self) -> Optional[int]:
        """Calculate execution duration in milliseconds."""
        if self.started_at and self.completed_at:
            delta = self.completed_at - self.started_at
            return int(delta.total_seconds() * 1000)
        return None
    
    def to_dict(self) -> Dict[str, Any]:
        """Export as dictionary."""
        data = asdict(self)
        data['state'] = self.state.value
        data['duration_ms'] = self.duration_ms()
        # Convert datetimes to ISO strings
        for key in ['created_at', 'updated_at', 'started_at', 'completed_at']:
            if data[key]:
                data[key] = data[key].isoformat() if isinstance(data[key], datetime) else data[key]
        return data


class Governor:
    """
    Central visibility and control plane.
    
    Single source of truth for all governed action state.
    Used by dashboard, API, and programmatic queries.
    """
    
    def __init__(self):
        self._records: Dict[str, ActionRecord] = {}
        self._by_state: Dict[ActionState, Set[str]] = {
            state: set() for state in ActionState
        }
        self._by_action: Dict[str, Set[str]] = {}
        self._by_agent: Dict[str, Set[str]] = {}
        self._pending_promises: Dict[str, str] = {}  # promise_id -> record_id
        self._lock = asyncio.Lock()
        self._subscribers: List[callable] = []
    
    # =========================================================================
    # Record Management
    # =========================================================================
    
    async def create(
        self,
        action_id: str,
        action: str,
        resource: str,
        agent: str = "default",
        risk: str = "LOW",
        approval_level: str = "NONE",
        args_preview: str = "",
        parent_id: Optional[str] = None,
        promise_id: Optional[str] = None,
    ) -> ActionRecord:
        """Create a new action record."""
        async with self._lock:
            record = ActionRecord(
                id=action_id,
                action=action,
                resource=resource,
                state=ActionState.PENDING,
                agent=agent,
                risk=risk,
                approval_level=approval_level,
                args_preview=args_preview[:200],
                parent_id=parent_id,
                promise_id=promise_id,
            )
            
            self._records[action_id] = record
            self._by_state[ActionState.PENDING].add(action_id)
            self._by_action.setdefault(action, set()).add(action_id)
            self._by_agent.setdefault(agent, set()).add(action_id)
            
            if promise_id:
                self._pending_promises[promise_id] = action_id
            
            logger.debug(f"[GOVERNOR] Created {action_id}: {action} ({resource})")
            await self._notify(record)
            return record
    
    async def transition(
        self,
        action_id: str,
        new_state: ActionState,
        result_preview: str = "",
        error_message: Optional[str] = None,
        metadata: Optional[Dict] = None,
    ) -> Optional[ActionRecord]:
        """Transition an action to a new state."""
        async with self._lock:
            record = self._records.get(action_id)
            if not record:
                logger.warning(f"[GOVERNOR] Unknown action: {action_id}")
                return None
            
            old_state = record.state
            
            # Update state tracking
            self._by_state[old_state].discard(action_id)
            self._by_state[new_state].add(action_id)
            
            # Update record
            record.state = new_state
            record.updated_at = datetime.utcnow()
            
            if result_preview:
                record.result_preview = result_preview[:200]
            if error_message:
                record.error_message = error_message
            if metadata:
                record.metadata.update(metadata)
            
            # Timing
            if new_state == ActionState.EXECUTING:
                record.started_at = datetime.utcnow()
            if new_state in (ActionState.SUCCESS, ActionState.FAILED, ActionState.DENIED, ActionState.TIMEOUT):
                record.completed_at = datetime.utcnow()
            
            logger.debug(f"[GOVERNOR] {action_id}: {old_state.value} -> {new_state.value}")
            await self._notify(record)
            return record
    
    async def skip(
        self,
        action_id: str,
        reason: str = "null_propagation",
    ) -> Optional[ActionRecord]:
        """Mark an action as skipped (null propagation)."""
        return await self.transition(
            action_id,
            ActionState.SKIPPED,
            metadata={"skip_reason": reason}
        )
    
    async def defer(
        self,
        action_id: str,
        promise_id: str,
        scheduled_for: Optional[datetime] = None,
    ) -> Optional[ActionRecord]:
        """Mark an action as deferred to durable execution."""
        record = await self.transition(
            action_id,
            ActionState.DEFERRED,
            metadata={
                "promise_id": promise_id,
                "scheduled_for": scheduled_for.isoformat() if scheduled_for else None,
            }
        )
        if record:
            self._pending_promises[promise_id] = action_id
        return record
    
    # =========================================================================
    # Queries
    # =========================================================================
    
    def get(self, action_id: str) -> Optional[ActionRecord]:
        """Get a single record by ID."""
        return self._records.get(action_id)
    
    def get_by_promise(self, promise_id: str) -> Optional[ActionRecord]:
        """Get record associated with a durable promise."""
        action_id = self._pending_promises.get(promise_id)
        if action_id:
            return self._records.get(action_id)
        return None
    
    def list_by_state(self, state: ActionState, limit: int = 100) -> List[ActionRecord]:
        """List all actions in a given state."""
        ids = list(self._by_state[state])[:limit]
        return [self._records[i] for i in ids if i in self._records]
    
    def list_pending(self) -> List[ActionRecord]:
        """List all pending approvals."""
        return self.list_by_state(ActionState.PENDING)
    
    def list_deferred(self) -> List[ActionRecord]:
        """List all deferred actions."""
        return self.list_by_state(ActionState.DEFERRED)
    
    def list_skipped(self) -> List[ActionRecord]:
        """List all skipped actions."""
        return self.list_by_state(ActionState.SKIPPED)
    
    def list_failed(self) -> List[ActionRecord]:
        """List all failed actions."""
        return self.list_by_state(ActionState.FAILED)
    
    def list_by_agent(self, agent: str, limit: int = 100) -> List[ActionRecord]:
        """List all actions by agent."""
        ids = list(self._by_agent.get(agent, set()))[:limit]
        return [self._records[i] for i in ids if i in self._records]
    
    def get_stats(self) -> Dict[str, int]:
        """Get counts by state."""
        return {
            state.value: len(ids)
            for state, ids in self._by_state.items()
        }
    
    def get_summary(self) -> Dict[str, Any]:
        """Get executive summary of current state."""
        stats = self.get_stats()
        pending = self.list_pending()
        failed = self.list_failed()
        
        return {
            "total_actions": len(self._records),
            "by_state": stats,
            "requires_attention": {
                "pending_approvals": len(pending),
                "failed_actions": len(failed),
                "deferred_actions": stats.get("deferred", 0),
            },
            "latest_pending": [r.to_dict() for r in pending[:5]],
            "latest_failed": [r.to_dict() for r in failed[:5]],
        }
    
    # =========================================================================
    # Subscriptions
    # =========================================================================
    
    def subscribe(self, callback: callable):
        """Subscribe to state changes."""
        self._subscribers.append(callback)
    
    async def _notify(self, record: ActionRecord):
        """Notify all subscribers of a state change."""
        for callback in self._subscribers:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(record)
                else:
                    callback(record)
            except Exception as e:
                logger.error(f"[GOVERNOR] Subscriber error: {e}")
    
    # =========================================================================
    # Cleanup
    # =========================================================================
    
    async def cleanup_old(self, hours: int = 24):
        """Remove records older than N hours."""
        cutoff = datetime.utcnow() - __import__('datetime').timedelta(hours=hours)
        to_remove = []
        
        async with self._lock:
            for action_id, record in self._records.items():
                if record.created_at < cutoff:
                    to_remove.append(action_id)
            
            for action_id in to_remove:
                self._remove(action_id)
        
        logger.info(f"[GOVERNOR] Cleaned up {len(to_remove)} old records")
        return len(to_remove)
    
    def _remove(self, action_id: str):
        """Internal remove without lock."""
        record = self._records.pop(action_id, None)
        if record:
            self._by_state[record.state].discard(action_id)
            self._by_action.get(record.action, set()).discard(action_id)
            self._by_agent.get(record.agent, set()).discard(action_id)
            if record.promise_id:
                self._pending_promises.pop(record.promise_id, None)


# Singleton
governor = Governor()


def get_governor() -> Governor:
    """Get the global governor instance."""
    return governor


__all__ = [
    'Governor',
    'ActionRecord',
    'ActionState',
    'get_governor',
]
