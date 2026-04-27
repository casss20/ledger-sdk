"""Provider-agnostic commercial event model and processor.

Stripe (or any future provider) translates its native events into
CommercialEvent objects. This module handles the business rules that
apply regardless of provider: grace periods, downgrade-to-free on cancel,
etc.
"""

import logging
from dataclasses import dataclass
from typing import Dict, Any, Optional
from datetime import datetime, timezone, timedelta

from .interface import CommercialRepository

logger = logging.getLogger(__name__)


@dataclass
class CommercialEvent:
    """Normalized commercial event — provider-agnostic."""
    event_type: str
    tenant_id: str
    payload: Dict[str, Any]


class CommercialEventProcessor:
    """Processes normalized commercial events and applies business rules.

    Rules implemented here (not in Stripe adapter):
    - Grace period length (7 days)
    - Downgrade to free on subscription deletion/cancel
    - Status transitions
    """

    GRACE_PERIOD_DAYS: int = 7

    def __init__(self, repo: CommercialRepository):
        self._repo = repo

    async def process(self, event: CommercialEvent) -> None:
        """Dispatch event to the appropriate handler."""
        handler = getattr(self, f"_handle_{event.event_type.replace('.', '_')}", None)
        if handler is None:
            logger.debug("No handler for commercial event type %r", event.event_type)
            return
        await handler(event)

    async def _handle_subscription_updated(self, event: CommercialEvent) -> None:
        """Subscription created or updated."""
        payload = event.payload
        await self._repo.upsert_subscription(
            tenant_id=event.tenant_id,
            plan_code=payload.get("plan_code", "free"),
            status=payload.get("status", "active"),
            grace_until=payload.get("grace_until"),
            current_period_end=payload.get("current_period_end"),
            current_period_start=payload.get("current_period_start"),
            cancel_at_period_end=payload.get("cancel_at_period_end", False),
        )

    async def _handle_subscription_deleted(self, event: CommercialEvent) -> None:
        """Subscription deleted — downgrade to free."""
        await self._repo.update_subscription_status(
            tenant_id=event.tenant_id,
            status="canceled",
        )
        await self._repo.upsert_subscription(
            tenant_id=event.tenant_id,
            plan_code="free",
            status="active",
        )
        logger.info(
            "Tenant %s subscription deleted — downgraded to free plan",
            event.tenant_id,
        )

    async def _handle_invoice_payment_failed(self, event: CommercialEvent) -> None:
        """Payment failed — enter grace period."""
        grace_until = datetime.now(timezone.utc) + timedelta(days=self.GRACE_PERIOD_DAYS)
        await self._repo.update_subscription_status(
            tenant_id=event.tenant_id,
            status="past_due",
            grace_until=grace_until,
        )
        logger.info(
            "Tenant %s payment failed — grace period until %s",
            event.tenant_id,
            grace_until.isoformat(),
        )

    async def _handle_invoice_payment_succeeded(self, event: CommercialEvent) -> None:
        """Payment succeeded — clear past_due and grace period."""
        await self._repo.update_subscription_status(
            tenant_id=event.tenant_id,
            status="active",
            grace_until=None,
        )
        logger.info("Tenant %s payment succeeded — status restored to active", event.tenant_id)

    async def _handle_subscription_created(self, event: CommercialEvent) -> None:
        """Alias for subscription.updated."""
        await self._handle_subscription_updated(event)
