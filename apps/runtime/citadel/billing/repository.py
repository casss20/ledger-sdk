"""Backward-compatibility shim — repository moved to citadel.commercial.adapters.stripe.repository."""
from citadel.commercial.adapters.stripe.repository import StripeCommercialRepository as BillingRepository
from citadel.commercial.interface import CommercialRepository
__all__ = ["BillingRepository", "CommercialRepository"]
