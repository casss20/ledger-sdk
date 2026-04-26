"""
Audit Rich Router
─────────────────
GET  /api/audit          – paginated, filterable audit log with all traceability fields
GET  /api/audit/export   – export as JSON or CSV
"""

import csv
import io
import json
from typing import Optional

from fastapi import APIRouter, Request, Query
from fastapi.responses import StreamingResponse

router = APIRouter(tags=["audit-rich"])

# ── decision classification ───────────────────────────────────────────────────

_ALLOWED_TYPES   = {"execution.allowed", "token.verification", "token.derived", "decision.verification"}
_BLOCKED_TYPES   = {"execution.blocked", "execution.rate_limited", "token.revoked", "decision.revoked"}
_ESCALATED_TYPES = {"decision.created", "approval.requested"}


def _classify(event_type: str) -> str:
    if event_type in _ALLOWED_TYPES:
        return "allowed"
    if event_type in _BLOCKED_TYPES:
        return "blocked"
    return "escalated"


# ── helpers ───────────────────────────────────────────────────────────────────

def _row_to_dict(row) -> dict:
    payload = row.get("payload_json") or {}
    if isinstance(payload, str):
        try:
            payload = json.loads(payload)
        except (json.JSONDecodeError, TypeError, ValueError):
            payload = {}

    decision = _classify(row["event_type"])

    return {
        "id":             str(row["event_id"]),
        "trace_id":       row.get("trace_id") or f"trc-{row['event_id']:04d}",
        "timestamp":      row["event_ts"].isoformat() if hasattr(row["event_ts"], "isoformat") else str(row["event_ts"]),
        "event_type":     row["event_type"],
        "decision":       decision,
        "initiator_id":   row.get("actor_id") or "system",
        "initiator_role": row.get("initiator_role") or "operator",
        "agent_id":       row.get("agent_id") or payload.get("agent_id", "—"),
        "action":         payload.get("action", row["event_type"]),
        "policy_id":      row.get("policy_id") or row.get("decision_id") or "—",
        "policy_name":    row.get("policy_name") or row.get("event_type", "—"),
        "reason":         row.get("reason") or payload.get("reason", "Policy evaluation complete."),
        "approver_id":    row.get("approver_id"),
        "approver_role":  row.get("approver_role"),
        "latency_ms":     payload.get("latency_ms"),
        "environment":    row.get("environment") or "production",
        "session_id":     row.get("session_id"),
        "event_hash":     row.get("event_hash", "")[:16] + "…" if row.get("event_hash") else None,
        "verified":       bool(row.get("event_hash")),
    }


# ── GET /api/audit ────────────────────────────────────────────────────────────

@router.get("/audit")
async def list_audit(
    request: Request,
    limit:       int            = Query(50,  ge=1, le=500),
    offset:      int            = Query(0,   ge=0, le=10000),
    decision:    Optional[str]  = Query(None, description="allowed | blocked | escalated"),
    agent_id:    Optional[str]  = Query(None),
    policy_id:   Optional[str]  = Query(None),
    environment: Optional[str]  = Query(None),
    from_ts:     Optional[str]  = Query(None, alias="from", max_length=64),
    to_ts:       Optional[str]  = Query(None, alias="to", max_length=64),
):
    pool = request.app.state.db_pool
    tenant_id = getattr(request.state, "tenant_id", "demo")

    # Build WHERE clauses
    conditions = ["tenant_id = $1"]
    params: list = [tenant_id]
    p = 2

    if agent_id:
        conditions.append(f"agent_id = ${p}")
        params.append(agent_id); p += 1

    if policy_id:
        conditions.append(f"(policy_id = ${p} OR decision_id = ${p})")
        params.append(policy_id); p += 1

    if environment:
        conditions.append(f"environment = ${p}")
        params.append(environment); p += 1

    if from_ts:
        conditions.append(f"event_ts >= ${p}::timestamptz")
        params.append(from_ts); p += 1

    if to_ts:
        conditions.append(f"event_ts <= ${p}::timestamptz")
        params.append(to_ts); p += 1

    # decision filter mapped to event_type
    if decision == "allowed":
        conditions.append(f"event_type = ANY(${p})")
        params.append(list(_ALLOWED_TYPES)); p += 1
    elif decision == "blocked":
        conditions.append(f"event_type = ANY(${p})")
        params.append(list(_BLOCKED_TYPES)); p += 1
    elif decision == "escalated":
        combined = list(_ALLOWED_TYPES | _BLOCKED_TYPES)
        conditions.append(f"event_type != ALL(${p})")
        params.append(combined); p += 1

    where = " AND ".join(conditions)

    async with pool.acquire() as conn:
        rows = await conn.fetch(
            f"""
            SELECT event_id, event_ts, event_type, tenant_id, actor_id,
                   decision_id, token_id, payload_json, prev_hash, event_hash,
                   session_id, request_id,
                   trace_id, initiator_role, agent_id, policy_id, policy_name,
                   reason, approver_id, approver_role, environment
            FROM governance_audit_log
            WHERE {where}
            ORDER BY event_id DESC
            LIMIT ${p} OFFSET ${p+1}
            """,
            *params, limit, offset,
        )

        total = await conn.fetchval(
            f"SELECT COUNT(*) FROM governance_audit_log WHERE {where}",
            *params,
        )

    entries = [_row_to_dict(dict(r)) for r in rows]
    return {"entries": entries, "total": total, "limit": limit, "offset": offset}


# ── GET /api/audit/export ─────────────────────────────────────────────────────

@router.get("/audit/export")
async def export_audit(
    request: Request,
    format:  str           = Query("json", description="json | csv"),
    limit:   int           = Query(1000, ge=1, le=10000),
    decision: Optional[str] = Query(None),
):
    pool = request.app.state.db_pool
    tenant_id = getattr(request.state, "tenant_id", "demo")

    conditions = ["tenant_id = $1"]
    params: list = [tenant_id]
    p = 2

    if decision == "allowed":
        conditions.append(f"event_type = ANY(${p})")
        params.append(list(_ALLOWED_TYPES)); p += 1
    elif decision == "blocked":
        conditions.append(f"event_type = ANY(${p})")
        params.append(list(_BLOCKED_TYPES)); p += 1
    elif decision == "escalated":
        conditions.append(f"event_type != ALL(${p})")
        params.append(list(_ALLOWED_TYPES | _BLOCKED_TYPES)); p += 1

    where = " AND ".join(conditions)

    async with pool.acquire() as conn:
        rows = await conn.fetch(
            f"""
            SELECT event_id, event_ts, event_type, actor_id, payload_json,
                   trace_id, initiator_role, agent_id, policy_id, policy_name,
                   reason, approver_id, approver_role, environment, event_hash, session_id
            FROM governance_audit_log
            WHERE {where}
            ORDER BY event_id DESC
            LIMIT ${p}
            """,
            *params, limit,
        )

    entries = [_row_to_dict(dict(r)) for r in rows]

    if format == "csv":
        fields = ["id", "trace_id", "timestamp", "decision", "initiator_id",
                  "initiator_role", "agent_id", "action", "policy_id", "policy_name",
                  "reason", "approver_id", "approver_role", "latency_ms",
                  "environment", "verified"]
        buf = io.StringIO()
        writer = csv.DictWriter(buf, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(entries)
        return StreamingResponse(
            iter([buf.getvalue()]),
            media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=citadel_audit.csv"},
        )

    # JSON export
    payload = json.dumps({"exported_at": __import__("datetime").datetime.utcnow().isoformat() + "Z", "entries": entries}, indent=2)
    return StreamingResponse(
        iter([payload]),
        media_type="application/json",
        headers={"Content-Disposition": "attachment; filename=citadel_audit.json"},
    )
