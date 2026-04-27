"""Backward-compatibility shim — re-exports from citadel.commercial.

All billing code has moved to `citadel.commercial`. Import from there
for new code; this shim preserves existing imports until they are migrated.
"""

# Re-export everything from the new commercial package
from citadel.commercial.models import BillingStatus, TenantEntitlements, UsageSnapshot
from citadel.commercial.interface import CommercialRepository
from citadel.commercial.entitlement_service import EntitlementService
from citadel.commercial.usage_service import UsageService
from citadel.commercial.events import CommercialEvent, CommercialEventProcessor
from citadel.commercial.middleware import CommercialMiddleware, BillingMiddleware
from citadel.commercial.routes import router

# Re-export Stripe adapter under old names
from citadel.commercial.adapters.stripe.client import StripeClient
from citadel.commercial.adapters.stripe.repository import StripeCommercialRepository as BillingRepository
from citadel.commercial.adapters.stripe.webhooks import StripeWebhookHandler

__all__ = [
    "BillingStatus",
    "TenantEntitlements",
    "UsageSnapshot",
    "CommercialRepository",
    "EntitlementService",
    "UsageService",
    "CommercialEvent",
    "CommercialEventProcessor",
    "CommercialMiddleware",
    "BillingMiddleware",
    "router",
    "StripeClient",
    "BillingRepository",
    "StripeWebhookHandler",
]
