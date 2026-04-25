"""HTTP utilities."""

import httpx

from citadel_governance.exceptions import (
    AuthenticationError,
    CitadelError,
    Conflict,
    NotFound,
    RateLimitError,
    ServerError,
    ValidationError,
)


def _raise_for_status(response: httpx.Response) -> None:
    """Raise appropriate exception for HTTP errors."""
    if response.is_success:
        return
    data = (
        response.json()
        if response.headers.get("content-type", "").startswith("application/json")
        else {}
    )
    detail = data.get("detail") or data.get("error") or response.reason_phrase
    status = response.status_code

    if status == 400 or status == 422:
        raise ValidationError(detail, status)
    elif status == 401:
        raise AuthenticationError(detail, status)
    elif status == 404:
        raise NotFound(detail, status)
    elif status == 409:
        raise Conflict(detail, status)
    elif status == 429:
        retry_after = response.headers.get("Retry-After")
        raise RateLimitError(
            detail,
            status,
            retry_after=float(retry_after) if retry_after else None,
        )
    elif status >= 500:
        raise ServerError(detail, status)
    raise CitadelError(detail, status)
