"""Commercial adapter registry.

Register provider adapters here. Core code never imports from
provider-specific subpackages directly — it uses the port
(CommercialRepository) and lets the composition root wire the
concrete adapter.
"""

from typing import Dict, Type, Optional
from ..interface import CommercialRepository

_ADAPTERS: Dict[str, Type[CommercialRepository]] = {}


def register_adapter(name: str, cls: Type[CommercialRepository]) -> None:
    """Register a provider adapter by name."""
    _ADAPTERS[name] = cls


def get_adapter(name: str) -> Optional[Type[CommercialRepository]]:
    """Look up a registered adapter class."""
    return _ADAPTERS.get(name)


def list_adapters() -> list:
    """Return names of all registered adapters."""
    return list(_ADAPTERS.keys())


# Auto-register built-in adapters
from .stripe.repository import StripeCommercialRepository
register_adapter("stripe", StripeCommercialRepository)
