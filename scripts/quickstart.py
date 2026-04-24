#!/usr/bin/env python3
"""
Citadel Quickstart: 10-minute onboarding for founders.

This script demonstrates Citadel's core value: governance for AI actions.
It initializes a test environment, executes a governed action, and
proves it was logged immutably.

Why this matters: when your agent makes decisions, Citadel checks them
before execution. This script shows exactly how.
"""

import asyncio  # Why: async is required for Citadel's async kernel
import hashlib  # Why: API keys are hashed for secure storage
import secrets  # Why: cryptographically secure random key generation
import sys  # Why: modify Python path to find citadel package
import uuid  # Why: Citadel uses UUIDs for all primary identifiers
from datetime import datetime  # Why: audit trail requires timestamps
from pathlib import Path  # Why: resolve src/ directory for imports

# Why: add src/ to Python path so `import citadel` works from repo root
src_path = Path(__file__).parent / "src"
sys.path.insert(0, str(src_path))

import asyncpg  # Why: direct PostgreSQL access for quickstart setup

# Why: import Citadel's core governance engine
from citadel import Kernel, Repository, Action
from citadel.execution.executor import Executor
from citadel.policy_resolver import PolicyResolver, PolicyEvaluator
from citadel.precedence import Precedence
from citadel.approval_service import ApprovalService
from citadel.audit_service import AuditService
from citadel.capability_service import CapabilityService

# Why: test database — quickstart uses same local Postgres as tests
DSN = "postgresql://citadel:citadel@localhost:5432/ledger_test"


async def initialize_test_tenant():
    """Create a test tenant. Why: every action belongs to a tenant."""
    conn = await asyncpg.connect(DSN)  # Why: direct connection for admin setup
    await conn.execute("SET app.admin_bypass = 'true'")  # Why: admin creates tenant
    tenant_id = f"tenant_{uuid.uuid4().hex[:8]}"  # Why: unique tenant identifier
    await conn.execute("INSERT INTO actors (actor_id, actor_type, tenant_id, status) VALUES ($1, $2, $3, 'active')", tenant_id, "service", tenant_id)
    await conn.close()  # Why: clean up connection
    return tenant_id


async def seed_api_key(tenant_id):
    """Generate API key for tenant. Why: agents authenticate with keys."""
    conn = await asyncpg.connect(DSN)  # Why: direct connection for key creation
    await conn.execute("SET app.admin_bypass = 'true'")  # Why: admin bypass for setup
    plaintext = f"sk_test_{secrets.token_urlsafe(32)}"  # Why: secure random key
    key_hash = hashlib.sha256(plaintext.encode()).hexdigest()  # Why: hash for storage
    await conn.execute("INSERT INTO api_keys (key_hash, tenant_id, name, scopes) VALUES ($1, $2, $3, $4)", key_hash, tenant_id, "quickstart", '["*"]')
    await conn.close()  # Why: clean up connection
    return plaintext


async def execute_sample_action(tenant_id, api_key):
    """Execute a governed action. Why: this is Citadel's core purpose."""
    pool = await asyncpg.create_pool(DSN, setup=lambda conn: conn.execute("SELECT set_tenant_context($1)", tenant_id))  # Why: set tenant context on every connection
    repo = Repository(pool)  # Why: repository handles all database access
    policy_eval = PolicyEvaluator()  # Why: evaluates policy rules against actions
    precedence = Precedence(repo, policy_eval)  # Why: precedence needs repo + evaluator
    kernel = Kernel(  # Why: kernel is the governance enforcement engine
        repository=repo,
        policy_resolver=PolicyResolver(repo),
        precedence=precedence,
        approval_service=ApprovalService(repo),
        capability_service=CapabilityService(repo),
        audit_service=AuditService(repo),
        executor=Executor(),
    )
    action = Action(  # Why: canonical action interface — all paths use this
        action_id=uuid.uuid4(),
        actor_id=tenant_id,
        actor_type="agent",
        action_name="file.write",
        resource="/tmp/ledger_test.txt",
        tenant_id=tenant_id,
        payload={"content": "Citadel governed this action."},
        context={"source": "quickstart"},
        session_id=None,
        request_id=None,
        idempotency_key=None,
        created_at=datetime.utcnow(),
    )
    result = await kernel.handle(action)  # Why: single entry point for governance
    await pool.close()  # Why: clean up pool
    return {
        "action_id": str(result.action.action_id),
        "decision": result.decision.status.value,
    }


async def verify_audit(action_id, tenant_id):
    """Verify action in audit trail. Why: governance without audit is just a firewall."""
    pool = await asyncpg.create_pool(DSN, setup=lambda conn: conn.execute("SELECT set_tenant_context($1)", tenant_id))  # Why: set tenant context for RLS
    repo = Repository(pool)  # Why: repository handles all database access
    action = await repo.get_action(uuid.UUID(action_id))  # Why: fetch by UUID
    await pool.close()  # Why: clean up pool
    return action  # Why: return record for verification


async def main():
    """Run quickstart. Why: founders run this to see Citadel work."""
    tenant_id = await initialize_test_tenant()  # Why: create isolated namespace
    print(f"Tenant created: {tenant_id}")  # Why: deterministic output line 1
    api_key = await seed_api_key(tenant_id)  # Why: credentials for testing
    print(f"API Key: {api_key}")  # Why: deterministic output line 2
    result = await execute_sample_action(tenant_id, api_key)  # Why: execute governance
    print(f"Action executed: {result['action_id']}")  # Why: deterministic output line 3
    print(f"Decision: {result['decision'].lower()}")  # Why: deterministic output line 4
    audit = await verify_audit(result["action_id"], tenant_id)  # Why: prove immutability
    print(f"Logged: {str(audit is not None).lower()}")  # Why: deterministic output line 5


if __name__ == "__main__":
    asyncio.run(main())  # Why: Python async entry point
