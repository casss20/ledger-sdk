"""Backward-compatibility shim — routes moved to citadel.commercial.routes."""
from citadel.commercial.routes import router
__all__ = ["router"]
