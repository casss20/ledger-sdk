import hmac
import hashlib
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional
from .repository import BillingRepository

def ts_to_dt(ts: Optional[int]) -> Optional[datetime]:
    if ts is None: return None
    return datetime.fromtimestamp(ts, tz=timezone.utc)

class StripeWebhookHandler:
    def __init__(self, repo: BillingRepository, webhook_secret: Optional[str] = None):
        self.repo = repo
        self.webhook_secret = webhook_secret

    def verify_signature(self, payload: bytes, signature_header: Optional[str]) -> bool:
        """
        Verify Stripe webhook signature using HMAC-SHA256.
        
        This prevents webhook replay attacks and ensures the event
        actually came from Stripe.
        """
        if not self.webhook_secret:
            # In development without webhook secret, log warning but allow
            import logging
            logging.getLogger(__name__).warning(
                "Stripe webhook secret not configured — skipping signature verification. "
                "NEVER do this in production."
            )
            return True
        
        if not signature_header:
            return False
        
        try:
            # Stripe signature format: t=timestamp,v1=signature,v0=legacy
            elements = signature_header.split(",")
            sig_dict = {}
            for element in elements:
                item = element.strip()
                if "=" in item:
                    key, val = item.split("=", 1)
                    sig_dict[key] = val
            
            timestamp = int(sig_dict.get("t", 0))
            signature = sig_dict.get("v1", "")
            
            # Check timestamp to prevent replay attacks (5 minute tolerance)
            now = int(datetime.now(timezone.utc).timestamp())
            if abs(now - timestamp) > 300:
                return False
            
            # Compute expected signature
            signed_payload = f"{timestamp}.{payload.decode('utf-8')}"
            expected = hmac.new(
                self.webhook_secret.encode("utf-8"),
                signed_payload.encode("utf-8"),
                hashlib.sha256,
            ).hexdigest()
            
            # Use constant-time comparison to prevent timing attacks
            return hmac.compare_digest(expected, signature)
            
        except Exception:
            return False

    async def handle(self, event: Dict[str, Any]):
        etype = event["type"]
        obj = event["data"]["object"]
        
        if etype == "checkout.session.completed":
            await self._handle_checkout_completed(obj)
        elif etype in {"customer.subscription.created", "customer.subscription.updated"}:
            await self._handle_subscription_sync(obj)
        elif etype == "customer.subscription.deleted":
            await self._handle_subscription_deleted(obj)
        elif etype == "invoice.paid":
            await self._handle_invoice_paid(obj)
        elif etype == "invoice.payment_failed":
            await self._handle_invoice_failed(obj)

    async def _handle_checkout_completed(self, obj: Dict[str, Any]):
        tenant_id = obj.get("metadata", {}).get("tenant_id")
        stripe_id = obj.get("customer")
        email = obj.get("customer_details", {}).get("email")
        if tenant_id and stripe_id:
            await self.repo.create_customer(tenant_id, email or "", None, stripe_id)

    async def _handle_subscription_sync(self, obj: Dict[str, Any]):
        customer = await self.repo.get_customer_by_stripe_id(obj["customer"])
        if not customer: return

        items = obj.get("items", {}).get("data", [])
        price_id = items[0]["price"]["id"] if items else None
        plan = await self.repo.get_plan_by_price_id(price_id) if price_id else None

        await self.repo.upsert_subscription({
            "tenant_id": customer["tenant_id"],
            "billing_customer_id": customer["id"],
            "plan_code": plan["code"] if plan else "free",
            "stripe_subscription_id": obj["id"],
            "stripe_price_id": price_id,
            "status": obj["status"],
            "cancel_at_period_end": obj["cancel_at_period_end"],
            "current_period_start": ts_to_dt(obj.get("current_period_start")),
            "current_period_end": ts_to_dt(obj.get("current_period_end")),
            "trial_start": ts_to_dt(obj.get("trial_start")),
            "trial_end": ts_to_dt(obj.get("trial_end")),
            "metadata_json": obj.get("metadata", {})
        })

    async def _handle_subscription_deleted(self, obj: Dict[str, Any]):
        customer = await self.repo.get_customer_by_stripe_id(obj["customer"])
        if not customer: return
        
        await self.repo.upsert_subscription({
            "tenant_id": customer["tenant_id"],
            "billing_customer_id": customer["id"],
            "plan_code": "free",
            "status": "canceled",
            "cancel_at_period_end": True
        })

    async def _handle_invoice_paid(self, obj: Dict[str, Any]):
        customer = await self.repo.get_customer_by_stripe_id(obj["customer"])
        if not customer: return
        # Implementation depends on how you want to update payment state
        pass

    async def _handle_invoice_failed(self, obj: Dict[str, Any]):
        customer = await self.repo.get_customer_by_stripe_id(obj["customer"])
        if not customer: return
        # Set grace period etc
        pass
