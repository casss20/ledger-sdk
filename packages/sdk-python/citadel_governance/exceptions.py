"""SDK exceptions."""


class CitadelError(Exception):
    """Base exception for SDK errors."""

    def __init__(self, message: str, status: int = 0):
        super().__init__(message)
        self.status = status


class AuthenticationError(CitadelError):
    """Raised when API key is invalid or missing (401)."""


class RateLimitError(CitadelError):
    """Raised when rate limit is exceeded (429)."""

    def __init__(self, message: str, status: int = 429, retry_after: float | None = None):
        super().__init__(message, status)
        self.retry_after = retry_after


class ValidationError(CitadelError):
    """Raised when request data is invalid (400, 422)."""


class ServerError(CitadelError):
    """Raised when the server returns a 5xx error."""


class ActionBlocked(CitadelError):
    """Raised when an action is blocked by governance policy."""


class ApprovalRequired(CitadelError):
    """Raised when an action requires human approval before proceeding."""


class NotFound(CitadelError):
    """Raised when a requested resource is not found (404)."""


class Conflict(CitadelError):
    """Raised when a resource already exists (409)."""
