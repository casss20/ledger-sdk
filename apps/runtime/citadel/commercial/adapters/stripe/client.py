"""Stripe API client wrapper.

Thin wrapper around the Stripe SDK. All Stripe-specific API calls
(checkout sessions, portal sessions, customer operations) live here.
Core code never imports this directly.
"""

import logging
from typing import Optional

from citadel.config import settings

logger = logging.getLogger(__name__)


class StripeClient:
    """Stripe SDK wrapper — handles initialization and common operations."""

    def __init__(self):
        self._stripe = None

    def _get_stripe(self):
        """Lazy-import stripe to avoid hard dependency at import time."""
        if self._stripe is None:
            import stripe
            stripe.api_key = settings.stripe_secret_key
            self._stripe = stripe
        return self._stripe

    async def create_checkout_session(
        self,
        customer_id: Optional[str] = None,
        price_id: Optional[str] = None,
        success_url: Optional[str] = None,
        cancel_url: Optional[str] = None,
        metadata: Optional[dict] = None,
    ) -> str:
        """Create a Stripe Checkout session and return its URL."""
        stripe = self._get_stripe()
        params = {
            "mode": "subscription",
            "success_url": success_url or settings.stripe_success_url,
            "cancel_url": cancel_url or settings.stripe_cancel_url,
            "metadata": metadata or {},
        }
        if customer_id:
            params["customer"] = customer_id
        if price_id:
            params["line_items"] = [{"price": price_id, "quantity": 1}]

        session = stripe.checkout.Session.create(**params)
        return session.url

    async def create_portal_session(self, customer_id: str) -> str:
        """Create a Stripe Billing Portal session and return its URL."""
        stripe = self._get_stripe()
        session = stripe.billing_portal.Session.create(
            customer=customer_id,
            return_url=settings.stripe_portal_return_url,
        )
        return session.url

    async def get_customer(self, stripe_customer_id: str) -> Optional[dict]:
        """Fetch a Stripe customer by ID."""
        stripe = self._get_stripe()
        try:
            return stripe.Customer.retrieve(stripe_customer_id)
        except Exception as exc:
            logger.warning("Failed to retrieve Stripe customer %s: %s", stripe_customer_id, exc)
            return None

    async def get_subscription(self, stripe_subscription_id: str) -> Optional[dict]:
        """Fetch a Stripe subscription by ID."""
        stripe = self._get_stripe()
        try:
            return stripe.Subscription.retrieve(stripe_subscription_id)
        except Exception as exc:
            logger.warning("Failed to retrieve Stripe subscription %s: %s", stripe_subscription_id, exc)
            return None
