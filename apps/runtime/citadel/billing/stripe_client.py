try:
    import stripe
except ImportError:
    stripe = None  # Stripe not installed â€” billing features disabled

from typing import Optional, Dict, Any
from citadel.config import settings

class StripeClient:
    def __init__(self):
        stripe.api_key = settings.stripe_secret_key

    def create_customer(self, email: str, tenant_id: str, name: Optional[str] = None) -> Dict[str, Any]:
        return stripe.Customer.create(
            email=email,
            name=name,
            metadata={"tenant_id": tenant_id}
        )

    def create_checkout_session(self, customer_id: str, price_id: str, tenant_id: str) -> Dict[str, Any]:
        return stripe.checkout.Session.create(
            mode="subscription",
            customer=customer_id,
            line_items=[{"price": price_id, "quantity": 1}],
            success_url=f"{settings.app_url}/settings/billing?checkout=success",
            cancel_url=f"{settings.app_url}/settings/billing?checkout=cancelled",
            metadata={"tenant_id": tenant_id},
        )

    def create_portal_session(self, customer_id: str) -> Dict[str, Any]:
        return stripe.billing_portal.Session.create(
            customer=customer_id,
            return_url=f"{settings.app_url}/settings/billing"
        )

    def verify_webhook(self, payload: bytes, sig_header: str) -> Dict[str, Any]:
        return stripe.Webhook.construct_event(
            payload, sig_header, settings.stripe_webhook_secret
        )
