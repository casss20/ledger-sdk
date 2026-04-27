"""Stripe webhook handler.

Receives raw Stripe webhooks, verifies HMAC signatures, translates to
CommercialEvents, and dispatches to the provider-agnostic event processor.
"""

import hmac
import hashlib
import logging
from datetime import datetime, timezone
from typing import Optional

from fastapi import HTTPException, Request

from .translator import StripeEventTranslator
from .repository import StripeCommercialRepository
from ...events import CommercialEventProcessor

logger = logging.getLogger(__name__)


class StripeWebhookHandler:
    """Receives Stripe webhooks and dispatches normalized events."""

    def __init__(
        self,
        repo: StripeCommercialRepository,
        event_processor: Optional[CommercialEventProcessor] = None,
        webhook_secret: Optional[str] = None,
    ):
        self._repo = repo
        self._translator = StripeEventTranslator(repo)
        if event_processor is None and repo is not None:
            event_processor = CommercialEventProcessor(repo)
        self._processor = event_processor
        self._webhook_secret = webhook_secret

    def verify_signature(self, payload: bytes, signature_header: Optional[str]) -> bool:
        """Verify Stripe webhook signature using HMAC-SHA256."""
        if not self._webhook_secret:
            from citadel.config import settings
            if not settings.debug:
                logger.error("Stripe webhook secret missing in production — rejecting")
                return False
            logger.warning("Stripe webhook secret missing — skipping verification (dev only)")
            return True

        if not signature_header:
            return False

        try:
            elements = signature_header.split(",")
            sig_dict = {}
            for element in elements:
                item = element.strip()
                if "=" in item:
                    key, val = item.split("=", 1)
                    sig_dict[key] = val

            timestamp = int(sig_dict.get("t", 0))
            signature = sig_dict.get("v1", "")

            # Replay protection: 5-minute tolerance
            now = int(datetime.now(timezone.utc).timestamp())
            if abs(now - timestamp) > 300:
                return False

            signed_payload = f"{timestamp}.{payload.decode('utf-8')}"
            expected = hmac.new(
                self._webhook_secret.encode("utf-8"),
                signed_payload.encode("utf-8"),
                hashlib.sha256,
            ).hexdigest()

            return hmac.compare_digest(expected, signature)

        except (ValueError, TypeError, KeyError, UnicodeDecodeError) as exc:
            logger.warning("Stripe signature verification error: %s", exc)
            return False

    async def handle(self, request: Request) -> dict:
        """Process an incoming Stripe webhook request."""
        payload = await request.body()
        sig_header = request.headers.get("stripe-signature")

        if not self.verify_signature(payload, sig_header):
            raise HTTPException(status_code=400, detail="Invalid signature")

        # Parse JSON
        import json
        try:
            event_data = json.loads(payload)
        except json.JSONDecodeError as exc:
            raise HTTPException(status_code=400, detail=f"Invalid JSON: {exc}")

        event_id = event_data.get("id", "unknown")
        event_type = event_data.get("type", "unknown")

        # Log event for idempotency
        await self._repo.log_event("stripe", event_id, event_type, event_data)

        try:
            # Translate to provider-agnostic event
            commercial_event = await self._translator.translate(event_data)
            if commercial_event:
                # Resolve plan code from price_id if needed
                if commercial_event.event_type in ("subscription.updated", "subscription.created"):
                    price_id = commercial_event.payload.get("price_id")
                    if price_id:
                        plan = await self._repo.get_plan_by_price_id(price_id)
                        commercial_event.payload["plan_code"] = plan["code"] if plan else "free"

                await self._processor.process(commercial_event)
                await self._repo.mark_event_processed(event_id)
            else:
                await self._repo.mark_event_processed(event_id, error="No translator mapping")

            return {"status": "ok", "event_id": event_id}

        except HTTPException:
            raise
        except Exception as exc:
            logger.exception("Stripe webhook event processing failed: %s", exc)
            await self._repo.mark_event_processed(event_id, error=str(exc))
            raise HTTPException(status_code=500, detail="Event processing failed")
