"""
Scoped action tokens — issue, verify, consume, revoke.
"""

import secrets
import time
from dataclasses import dataclass


@dataclass
class Capability:
    token: str
    action: str
    resource: str
    issued_at: float
    expires_at: float
    max_uses: int
    uses: int = 0
    revoked: bool = False
    issued_to: str = ""

    def valid(self) -> tuple[bool, str]:
        if self.revoked:
            return False, "revoked"
        if self.uses >= self.max_uses:
            return False, "exhausted"
        if time.time() > self.expires_at:
            return False, "expired"
        return True, "ok"


class CapabilityIssuer:
    def __init__(self) -> None:
        self._store: dict[str, Capability] = {}

    def issue(self, *, action, resource, ttl_seconds=300, max_uses=1, issued_to=""):
        now = time.time()
        cap = Capability(
            token=secrets.token_urlsafe(24),
            action=action,
            resource=resource,
            issued_at=now,
            expires_at=now + ttl_seconds,
            max_uses=max_uses,
            issued_to=issued_to,
        )
        self._store[cap.token] = cap
        return cap

    def verify(self, token, action, resource):
        cap = self._store.get(token)
        if not cap:
            return False, "unknown"
        if cap.action != action:
            return False, "action_mismatch"
        if cap.resource != resource:
            return False, "resource_mismatch"
        return cap.valid()

    def consume(self, token):
        cap = self._store.get(token)
        if cap:
            cap.uses += 1

    def revoke(self, token):
        cap = self._store.get(token)
        if cap:
            cap.revoked = True