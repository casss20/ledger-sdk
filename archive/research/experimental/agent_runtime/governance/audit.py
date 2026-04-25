"""
Hash-chained audit log — immutable record of all governance decisions.
Uses asyncpg for async Postgres operations.
"""

import hashlib
import json
import time
from typing import Any

import asyncpg


SCHEMA = """
CREATE TABLE IF NOT EXISTS audit_log (
    id BIGSERIAL PRIMARY KEY,
    ts DOUBLE PRECISION NOT NULL,
    actor TEXT NOT NULL,
    action TEXT NOT NULL,
    resource TEXT NOT NULL,
    risk TEXT NOT NULL,
    approved BOOLEAN NOT NULL,
    payload JSONB NOT NULL,
    prev_hash TEXT NOT NULL,
    event_hash TEXT NOT NULL UNIQUE
);
CREATE INDEX IF NOT EXISTS audit_actor_ts ON audit_log (actor, ts DESC);
"""


def _hash(prev: str, body: dict[str, Any]) -> str:
    canonical = json.dumps(body, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256((prev + canonical).encode()).hexdigest()


class AuditService:
    def __init__(self, dsn: str) -> None:
        self._dsn = dsn
        self._pool: asyncpg.Pool | None = None

    async def start(self) -> None:
        self._pool = await asyncpg.create_pool(self._dsn, min_size=2, max_size=10)
        async with self._pool.acquire() as conn:
            await conn.execute(SCHEMA)

    async def stop(self) -> None:
        if self._pool:
            await self._pool.close()

    async def log(self, *, actor, action, resource, risk, approved, payload):
        assert self._pool
        async with self._pool.acquire() as conn:
            prev = await conn.fetchval(
                "SELECT event_hash FROM audit_log ORDER BY id DESC LIMIT 1"
            ) or "GENESIS"
            body = {
                "ts": time.time(),
                "actor": actor,
                "action": action,
                "resource": resource,
                "risk": risk,
                "approved": approved,
                "payload": payload,
            }
            event_hash = _hash(prev, body)
            await conn.execute(
                """INSERT INTO audit_log (ts, actor, action, resource, risk, approved, payload, prev_hash, event_hash)
                VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9)""",
                body["ts"],
                actor,
                action,
                resource,
                risk,
                approved,
                json.dumps(payload),
                prev,
                event_hash,
            )
            return event_hash

    async def verify_integrity(self) -> tuple[bool, int]:
        assert self._pool
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(
                """SELECT ts, actor, action, resource, risk, approved, payload, prev_hash, event_hash
                FROM audit_log ORDER BY id ASC"""
            )
            prev = "GENESIS"
            for r in rows:
                body = {
                    "ts": r["ts"],
                    "actor": r["actor"],
                    "action": r["action"],
                    "resource": r["resource"],
                    "risk": r["risk"],
                    "approved": r["approved"],
                    "payload": json.loads(r["payload"]),
                }
                if _hash(prev, body) != r["event_hash"]:
                    return False, len(rows)
                if r["prev_hash"] != prev:
                    return False, len(rows)
                prev = r["event_hash"]
            return True, len(rows)