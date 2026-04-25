"""Backward-compatible shim for legacy ``import citadel``.

.. deprecated::
    This import path is deprecated and will be removed in v1.0.
    Please use ``import citadel_governance as cg`` instead.
"""

import warnings

with warnings.catch_warnings():
    warnings.simplefilter("always", DeprecationWarning)
    warnings.warn(
        "'import citadel' is deprecated. Use 'import citadel_governance as cg' instead. "
        "The 'citadel' module name will be removed in v1.0.",
        DeprecationWarning,
        stacklevel=2,
    )

# Re-export everything from the canonical package
from citadel_governance._version import __version__  # noqa: F401
from citadel_governance.exceptions import *  # noqa: F401,F403
from citadel_governance.exceptions import (
    AuthenticationError,
    RateLimitError,
    ValidationError,
    ServerError,
)
from citadel_governance.models import *  # noqa: F401,F403
from citadel_governance.client import CitadelClient  # noqa: F401
from citadel_governance._module_api import *  # noqa: F401,F403
from citadel_governance import __all__  # noqa: F401
from citadel_governance import __all__ as _cg_all  # noqa: F401

__all__ = _cg_all  # type: ignore[name-defined]  # noqa: F821
