"""Backward-compatibility shim — webhooks moved to citadel.commercial.adapters.stripe.webhooks."""
from citadel.commercial.adapters.stripe.webhooks import StripeWebhookHandler
__all__ = ["StripeWebhookHandler"]
