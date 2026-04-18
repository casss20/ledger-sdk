"""
Durable Execution — Ledger SDK

Survives server restarts using Redis.
Inspired by Weft's durable execution via Restate.
"""

import asyncio
import json
from dataclasses import dataclass, asdict
from typing import Optional, Any, Callable, Awaitable
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

# Optional redis import
try:
    import redis.asyncio as redis
    HAS_REDIS = True
except ImportError:
    redis = None
    HAS_REDIS = False
    logger.warning("[Durable] redis not installed. Durable execution disabled. Install with: pip install ledger-sdk[durable]")


@dataclass
class DurablePromise:
    """
    A promise that survives server restarts.
    
    Like Weft's durable execution — a human approval that takes 3 days
    is the same code as one that takes 3 seconds.
    
    Reports DEFERRED state to GOVERNOR for visibility.
    """
    promise_id: str
    action: str
    resource: str
    risk: str
    args: dict
    created_at: str
    state: str = "pending"  # pending, fulfilled, rejected
    result: Optional[Any] = None
    approved_by: Optional[str] = None
    approved_at: Optional[str] = None
    action_id: Optional[str] = None  # Link to GOVERNOR record
    
    # Redis client (class-level)
    _redis: Optional[Any] = None
    
    @classmethod
    def get_redis(cls) -> Optional[Any]:
        if not HAS_REDIS:
            raise ImportError("redis not installed. Install with: pip install ledger-sdk[durable]")
        if cls._redis is None:
            cls._redis = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)
        return cls._redis
    
    async def persist(self, ttl_seconds: int = 86400) -> None:
        """Save to Redis with TTL (default 24 hours)."""
        if not HAS_REDIS:
            logger.error("[Durable] Cannot persist: redis not installed")
            return
        r = self.get_redis()
        data = json.dumps(asdict(self), default=str)
        await r.setex(f"ledger:promise:{self.promise_id}", ttl_seconds, data)
        logger.debug(f"[Durable] Persisted {self.promise_id}")
    
    async def wait(self, timeout_sec: float = 300) -> bool:
        """
        Wait for fulfillment with exponential backoff.
        Survives server restarts.
        Updates GOVERNOR state on fulfillment/rejection.
        """
        if not HAS_REDIS:
            logger.error("[Durable] Cannot wait: redis not installed")
            return False
        r = self.get_redis()
        start_time = asyncio.get_event_loop().time()
        attempt = 0
        
        # Report DEFERRED to GOVERNOR
        if self.action_id:
            try:
                from ledger.governor import get_governor, ActionState
                gov = get_governor()
                await gov.defer(
                    self.action_id,
                    self.promise_id,
                    scheduled_for=None  # Waiting for human
                )
            except Exception as e:
                logger.debug(f"[Durable] Could not report defer to governor: {e}")
        
        while True:
            # Check if we've exceeded timeout
            elapsed = asyncio.get_event_loop().time() - start_time
            if elapsed > timeout_sec:
                logger.warning(f"[Durable] Timeout waiting for {self.promise_id}")
                # Report TIMEOUT to GOVERNOR
                if self.action_id:
                    try:
                        from ledger.governor import get_governor, ActionState
                        gov = get_governor()
                        await gov.transition(self.action_id, ActionState.TIMEOUT)
                    except Exception:
                        pass
                return False
            
            # Check Redis for state
            data = await r.get(f"ledger:promise:{self.promise_id}")
            if data:
                state = json.loads(data)
                if state.get("state") == "fulfilled":
                    self.result = state.get("result")
                    self.approved_by = state.get("approved_by")
                    self.approved_at = state.get("approved_at")
                    logger.info(f"[Durable] ✅ Promise fulfilled: {self.promise_id}")
                    # Report back to GOVERNOR
                    if self.action_id:
                        try:
                            from ledger.governor import get_governor, ActionState
                            gov = get_governor()
                            await gov.transition(self.action_id, ActionState.PENDING,
                                               metadata={"promise_fulfilled": True})
                        except Exception:
                            pass
                    return True
                if state.get("state") == "rejected":
                    logger.info(f"[Durable] ❌ Promise rejected: {self.promise_id}")
                    # Report DENIED to GOVERNOR
                    if self.action_id:
                        try:
                            from ledger.governor import get_governor, ActionState
                            gov = get_governor()
                            await gov.transition(self.action_id, ActionState.DENIED,
                                               metadata={"promise_rejected": True})
                        except Exception:
                            pass
                    return False
            
            # Exponential backoff, capped at 60 seconds
            sleep_time = min(2 ** attempt, 60)
            await asyncio.sleep(sleep_time)
            attempt += 1
    
    async def fulfill(self, approved: bool, approved_by: str = "system", result: Any = None) -> None:
        """Fulfill the promise (called by dashboard/API)."""
        if not HAS_REDIS:
            logger.error("[Durable] Cannot fulfill: redis not installed")
            return
        r = self.get_redis()
        self.state = "fulfilled" if approved else "rejected"
        self.approved_by = approved_by
        self.approved_at = datetime.utcnow().isoformat()
        self.result = result
        
        data = json.dumps(asdict(self), default=str)
        await r.set(f"ledger:promise:{self.promise_id}", data)
        logger.info(f"[Durable] Promise {self.promise_id} marked as {self.state}")
    
    @classmethod
    async def get_pending(cls) -> list:
        """Get all pending promises (for dashboard)."""
        if not HAS_REDIS:
            return []
        r = cls.get_redis()
        keys = await r.keys("ledger:promise:*")
        promises = []
        for key in keys:
            data = await r.get(key)
            if data:
                p = json.loads(data)
                if p.get("state") == "pending":
                    promises.append(p)
        return promises
    
    @classmethod
    async def get_by_id(cls, promise_id: str) -> Optional[dict]:
        """Get promise by ID."""
        if not HAS_REDIS:
            return None
        r = cls.get_redis()
        data = await r.get(f"ledger:promise:{self.promise_id}")
        return json.loads(data) if data else None


class DurableApprovalQueue:
    """
    Redis-backed approval queue.
    Survives server restarts unlike the in-memory version.
    """
    
    def __init__(self):
        self._hooks: list[Callable[[DurablePromise], Awaitable[None]]] = []
    
    async def push(self, promise: DurablePromise) -> None:
        """Add promise to queue and persist to Redis."""
        await promise.persist(ttl_seconds=86400)  # 24 hour TTL
        logger.info(f"[ApprovalQueue] New request: {promise.action} ({promise.promise_id})")
        
        # Notify hooks
        for hook in self._hooks:
            try:
                await hook(promise)
            except Exception as e:
                logger.error(f"[ApprovalQueue] Hook error: {e}")
    
    async def approve(self, promise_id: str, approved_by: str) -> bool:
        """Approve a pending promise."""
        promise_data = await DurablePromise.get_by_id(promise_id)
        if not promise_data or promise_data.get("state") != "pending":
            return False
        
        promise = DurablePromise(**promise_data)
        await promise.fulfill(approved=True, approved_by=approved_by)
        return True
    
    async def deny(self, promise_id: str, approved_by: str) -> bool:
        """Deny a pending promise."""
        promise_data = await DurablePromise.get_by_id(promise_id)
        if not promise_data or promise_data.get("state") != "pending":
            return False
        
        promise = DurablePromise(**promise_data)
        await promise.fulfill(approved=False, approved_by=approved_by)
        return True
    
    async def get_pending(self) -> list[DurablePromise]:
        """Get all pending promises."""
        pending_data = await DurablePromise.get_pending()
        return [DurablePromise(**p) for p in pending_data]
    
    async def get_by_id(self, promise_id: str) -> Optional[DurablePromise]:
        """Get promise by ID."""
        data = await DurablePromise.get_by_id(promise_id)
        return DurablePromise(**data) if data else None
    
    def register_hook(self, hook: Callable[[DurablePromise], Awaitable[None]]):
        """Register callback for new promises."""
        self._hooks.append(hook)


# Singleton
_queue_instance: Optional[DurableApprovalQueue] = None


def get_durable_queue() -> DurableApprovalQueue:
    """Get or create the global durable approval queue."""
    global _queue_instance
    if _queue_instance is None:
        _queue_instance = DurableApprovalQueue()
    return _queue_instance


# Wire into governance
async def durable_approval_hook(ctx: dict) -> bool:
    """
    Durable approval hook for @governed decorator.
    Survives server restarts.
    Reports DEFERRED state to GOVERNOR.
    """
    import uuid
    
    queue = get_durable_queue()
    action_id = ctx.get("id")  # From @governed decorator
    
    promise = DurablePromise(
        promise_id=f"req_{uuid.uuid4().hex[:12]}",
        action=ctx.get("action", "unknown"),
        resource=ctx.get("resource", "unknown"),
        risk=ctx.get("risk", "unknown"),
        args=ctx.get("args", {}),
        created_at=datetime.utcnow().isoformat(),
        action_id=action_id,
    )
    
    await queue.push(promise)
    logger.info(f"[DurableHook] Waiting for approval: {promise.promise_id}")
    
    approved = await promise.wait(timeout_sec=300)  # 5 min timeout default
    return approved
