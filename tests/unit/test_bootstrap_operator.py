import pytest

from citadel.api import _ensure_bootstrap_operator
from citadel.auth.operator import OperatorService
from citadel.config import settings


class FakeTransaction:
    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False


class FakeConnection:
    def __init__(self, count=0):
        self.count = count
        self.executed = []

    def transaction(self):
        return FakeTransaction()

    async def execute(self, sql, *args):
        self.executed.append((sql, args))

    async def fetchrow(self, sql, *args):
        return {"cnt": self.count}


class FakeAcquire:
    def __init__(self, conn):
        self.conn = conn

    async def __aenter__(self):
        return self.conn

    async def __aexit__(self, exc_type, exc, tb):
        return False


class FakePool:
    def __init__(self, conn):
        self.conn = conn

    def acquire(self):
        return FakeAcquire(self.conn)


@pytest.mark.asyncio
async def test_bootstrap_operator_uses_configured_secret(monkeypatch):
    conn = FakeConnection(count=3)
    monkeypatch.setattr(settings, "citadel_admin_bootstrap_username", "admin")
    monkeypatch.setattr(settings, "citadel_admin_bootstrap_password", "citadelsdk")
    monkeypatch.setattr(settings, "citadel_admin_bootstrap_tenant", "citadel")
    monkeypatch.setattr(settings, "citadel_admin_bootstrap_email", "admin@citadelsdk.com")
    monkeypatch.setattr(settings, "citadel_admin_bootstrap_role", "admin")

    await _ensure_bootstrap_operator(FakePool(conn))

    upsert_sql, upsert_args = conn.executed[-1]
    assert "ON CONFLICT (username) DO UPDATE" in upsert_sql
    assert upsert_args[1] == "admin"
    assert upsert_args[2] == "admin@citadelsdk.com"
    assert upsert_args[4] == "citadel"
    assert upsert_args[5] == "admin"
    assert OperatorService(None).verify_password("citadelsdk", upsert_args[3])


@pytest.mark.asyncio
async def test_bootstrap_operator_preserves_existing_without_secret(monkeypatch):
    conn = FakeConnection(count=1)
    monkeypatch.setattr(settings, "citadel_admin_bootstrap_password", None)

    await _ensure_bootstrap_operator(FakePool(conn))

    assert len(conn.executed) == 1
    assert conn.executed[0][0] == "SET LOCAL app.admin_bypass = 'true'"
