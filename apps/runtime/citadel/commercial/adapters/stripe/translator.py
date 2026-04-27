"""Stripe event translator — converts raw Stripe webhooks into provider-agnostic CommercialEvents.

This is the boundary layer: Stripe specifics enter here, normalized events exit.
The core CommercialEventProcessor never sees Stripe objects.
"""

import logging
from typing import Dict, Any, Optional

from ...events import CommercialEvent
from .repository import StripeCommercialRepository

logger = logging.getLogger(__name__)


def _ts_to_epoch(ts: Optional[int]) -> Optional[int]:
    """Convert Stripe timestamp to epoch int."""
    return ts


class StripeEventTranslator:
    """Translates Stripe webhook payloads into CommercialEvent objects."""

    def __init__(self, repository: StripeCommercialRepository):
        self._repo = repository

    async def translate(self, stripe_event: Dict[str, Any]) -> Optional[CommercialEvent]:
        """Convert a Stripe event dict to a provider-agnostic CommercialEvent."""
        event_type = stripe_event.get("type")
        data = stripe_event.get("data", {}).get("object", {})

        if not event_type or not data:
            logger.warning("Malformed Stripe event — missing type or data")
            return None

        tenant_id = await self._resolve_tenant(data)
        if not tenant_id:
            logger.warning("Could not resolve tenant_id for Stripe event %s", event_type)
            return None

        # Map Stripe event types to generic commercial events
        mapper = {
            "customer.subscription.created": self._map_subscription_updated,
            "customer.subscription.updated": self._map_subscription_updated,
            "customer.subscription.deleted": self._map_subscription_deleted,
            "invoice.paid": self._map_invoice_paid,
            "invoice.payment_failed": self._map_invoice_payment_failed,
            "checkout.session.completed": self._map_checkout_completed,
        }

        mapper_fn = mapper.get(event_type)
        if not mapper_fn:
            logger.debug("No translator mapping for Stripe event %r", event_type)
            return None

        return mapper_fn(tenant_id, data)

    # ── Internal mappers ──────────────────────────────────────────────────

    def _map_subscription_updated(self, tenant_id: str, obj: Dict[str, Any]) -> CommercialEvent:
        items = obj.get("items", {}).get("data", [])
        price_id = items[0]["price"]["id"] if items else None
        plan = None
        # Best-effort plan lookup — fire-and-forget, don't block on DB miss
        if price_id:
            # Async plan lookup can't happen inside sync mapper; pass price_id in payload
            pass

        return CommercialEvent(
            event_type="subscription.updated",
            tenant_id=tenant_id,
            payload={
                "subscription_id": obj.get("id"),
                "status": obj.get("status"),
                "price_id": price_id,
                "plan_code": None,  # Will be resolved by webhook handler if needed
                "current_period_start": obj.get("current_period_start"),
                "current_period_end": obj.get("current_period_end"),
                "trial_start": obj.get("trial_start"),
                "trial_end": obj.get("trial_end"),
                "cancel_at_period_end": obj.get("cancel_at_period_end", False),
                "metadata": obj.get("metadata", {}),
            },
        )

    def _map_subscription_deleted(self, tenant_id: str, obj: Dict[str, Any]) -> CommercialEvent:
        return CommercialEvent(
            event_type="subscription.deleted",
            tenant_id=tenant_id,
            payload={
                "subscription_id": obj.get("id"),
                "status": "canceled",
            },
        )

    def _map_invoice_paid(self, tenant_id: str, obj: Dict[str, Any]) -> CommercialEvent:
        return CommercialEvent(
            event_type="invoice.payment_succeeded",
            tenant_id=tenant_id,
            payload={
                "invoice_id": obj.get("id"),
                "subscription_id": obj.get("subscription"),
            },
        )

    def _map_invoice_payment_failed(self, tenant_id: str, obj: Dict[str, Any]) -> CommercialEvent:
        return CommercialEvent(
            event_type="invoice.payment_failed",
            tenant_id=tenant_id,
            payload={
                "invoice_id": obj.get("id"),
                "subscription_id": obj.get("subscription"),
                "attempt_count": obj.get("attempt_count", 1),
            },
        )

    def _map_checkout_completed(self, tenant_id: str, obj: Dict[str, Any]) -> CommercialEvent:
        return CommercialEvent(
            event_type="checkout.completed",
            tenant_id=tenant_id,
            payload={
                "session_id": obj.get("id"),
                "customer_id": obj.get("customer"),
                "subscription_id": obj.get("subscription"),
                "metadata": obj.get("metadata", {}),
            },
        )

    # ── Tenant resolution ───────────────────────────────────────────────────

    async def _resolve_tenant(self, stripe_object: Dict[str, Any]) -> Optional[str]:
        """Look up tenant_id from a Stripe object.

        Priority:
        1. metadata.tenant_id (set by us during checkout)
        2. customer → billing_customers lookup
        3. customer_details → billing_customers lookup by email
        """
        # 1. Direct metadata
        metadata = stripe_object.get("metadata", {})
        tenant_id = metadata.get("tenant_id")
        if tenant_id:
            return tenant_id

        # 2. Stripe customer ID lookup
        customer_id = stripe_object.get("customer")
        if customer_id:
            customer = await self._repo.get_customer_by_stripe_id(str(customer_id))
            if customer:
                return customer.get("tenant_id")

        # 3. Fallback: customer_details email lookup (for checkout.session.completed)
        customer_details = stripe_object.get("customer_details", {})
        email = customer_details.get("email")
        if email:
            # NOTE: This is weak — multiple tenants could share an email.
            # In practice checkout.session.completed carries metadata.tenant_id.
            row = await self._repo.pool.fetchrow(
                "SELECT tenant_id FROM billing_customers WHERE billing_email = $1 LIMIT 1", email
            )
            if row:
                return row["tenant_id"]

        return None
