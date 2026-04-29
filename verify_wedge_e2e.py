"""End-to-end verification of the Citadel wedge (cost enforcement + evidence export).

Tests without requiring a running database or API server. Uses the kernel directly
with minimal mocked collaborators.
"""

import asyncio
import sys
import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock
from types import SimpleNamespace

sys.path.insert(0, 'apps/runtime')

from citadel.actions import Action, KernelStatus
from citadel.commercial.cost_controls import BudgetDecision, CostBudget
from citadel.execution.kernel import Kernel
from citadel.audit_evidence import EvidenceExporter, AuditEvent, DecisionEvidence


async def build_test_kernel():
    """Build a kernel with stubs that allow spending to be blocked."""
    repo = AsyncMock()
    repo.find_decision_by_idempotency = AsyncMock(return_value=None)
    repo.save_action = AsyncMock(return_value=True)
    repo.save_decision = AsyncMock(return_value=None)
    repo.save_execution_result = AsyncMock(return_value=None)
    repo.fetch_audit_events_for_decision = AsyncMock(return_value=[])

    snapshot = SimpleNamespace(snapshot_id=uuid.uuid4(), policy_version="v1")
    policy_resolver = AsyncMock()
    policy_resolver.resolve = AsyncMock(return_value=snapshot)

    precedence_result = SimpleNamespace(
        blocked=False,
        status=KernelStatus.ALLOWED,
        winning_rule="default_allow",
        reason="ok",
        path_taken="default",
    )
    precedence = AsyncMock()
    precedence.evaluate = AsyncMock(return_value=precedence_result)

    approval_check = SimpleNamespace(required=False, reason="", risk_level=None, risk_score=None)
    approvals = AsyncMock()
    approvals.check_required = AsyncMock(return_value=approval_check)

    capability_service = AsyncMock()
    audit = AsyncMock()
    executor = AsyncMock()
    executor.run = AsyncMock(return_value={"ok": True})

    cost_service = AsyncMock()

    kernel = Kernel(
        repository=repo,
        policy_resolver=policy_resolver,
        precedence=precedence,
        approval_service=approvals,
        capability_service=capability_service,
        audit_service=audit,
        executor=executor,
        cost_service=cost_service,
    )
    return kernel, executor, audit, cost_service, repo


async def test_wedge_a_spend_enforcement():
    """Test Wedge A: Hard cost enforcement blocks before execution."""
    print("\n" + "=" * 70)
    print("WEDGE A: Hard Cost Enforcement (Estimate + BLOCK Before LLM Call)")
    print("=" * 70)

    kernel, executor, audit, cost_service, repo = await build_test_kernel()

    # Setup: Configure a budget that will be exceeded
    now = datetime.now(timezone.utc)
    budget = CostBudget(
        tenant_id="tenant-1",
        name="Daily LLM cap",
        scope_type="tenant",
        scope_value="tenant-1",
        amount_cents=1000,  # $10.00
        reset_period="daily",
        enforcement_action="block",
        budget_id="budget-1",
    )
    blocked_decision = BudgetDecision(
        allowed=False,
        enforcement_action="block",
        reason="tenant budget 'Daily LLM cap' would be exceeded: 1100/1000 cents",
        projected_cost_cents=100,
        current_spend_cents=1000,
        budget_amount_cents=1000,
        period_start=now,
        period_end=now,
        budget=budget,
    )
    cost_service.check_budget = AsyncMock(return_value=blocked_decision)

    # Create an action with cost info (simulating Anthropic Claude call)
    action = Action(
        action_id=uuid.uuid4(),
        actor_id="agent-1",
        actor_type="agent",
        action_name="llm.generate",
        resource="anthropic:claude",
        tenant_id="tenant-1",
        payload={},
        context={
            "projected_cost_cents": 100,
            "provider": "anthropic",
            "model": "claude-opus-4-7",
            "input_tokens": 10000,
            "output_tokens": 2000,
        },
        session_id=None,
        request_id=str(uuid.uuid4()),
        idempotency_key=None,
        created_at=datetime.now(timezone.utc),
    )

    # Execute the action
    result = await kernel.handle(action)

    # Verify BLOCKING
    print(f"[OK] Action status: {result.decision.status.value}")
    print(f"[OK] Winning rule: {result.decision.winning_rule}")
    print(f"[OK] Reason: {result.decision.reason}")
    print(f"[OK] Executed: {result.executed}")

    assert result.executed is False, "Action should NOT execute"
    assert result.decision.status == KernelStatus.BLOCKED_POLICY, "Should be blocked"
    assert result.decision.winning_rule == "spend_limit_exceeded", "Should cite budget"
    assert "would be exceeded" in result.decision.reason, "Reason should explain overage"

    # Verify audit event was emitted
    audit.spend_limit_exceeded.assert_awaited_once()
    call_args = audit.spend_limit_exceeded.call_args
    print(f"[OK] Audit event emitted: spend_limit_exceeded")
    print(f"  - Audit method called with action_id={call_args[0][0].action_id}")

    # Verify executor was NOT called (hard block before API call)
    executor.run.assert_not_called()
    print(f"[OK] Executor NOT called (hard block before LLM API)")

    print("\n[OK] WEDGE A VERIFIED: Spending is blocked before execution")
    return True


async def test_wedge_b_evidence_export():
    """Test Wedge B: Cryptographic audit evidence."""
    print("\n" + "=" * 70)
    print("WEDGE B: Decision-First Cryptographic Audit Evidence")
    print("=" * 70)

    # Create a mock decision with audit events
    now = datetime.now(timezone.utc)
    decision_id = str(uuid.uuid4())
    action_id = str(uuid.uuid4())

    events = [
        AuditEvent(
            event_id=1,
            event_type="action_received",
            actor_id=None,
            payload={"action_name": "llm.generate"},
            event_ts=now,
        ),
        AuditEvent(
            event_id=2,
            event_type="spend_limit_exceeded",
            actor_id="kernel",
            payload={"budget_id": "budget-1", "reason": "Budget exceeded"},
            event_ts=now,
        ),
        AuditEvent(
            event_id=3,
            event_type="decision_made",
            actor_id="kernel",
            payload={"status": "blocked", "winning_rule": "spend_limit_exceeded"},
            event_ts=now,
        ),
    ]

    # Create evidence bundle
    from citadel.audit_evidence import _compute_root_hash

    root_hash = _compute_root_hash(events)
    evidence = DecisionEvidence(
        decision_id=decision_id,
        action_id=action_id,
        status="blocked",
        winning_rule="spend_limit_exceeded",
        reason="Budget would be exceeded",
        created_at=now,
        policy_snapshot_id=str(uuid.uuid4()),
        audit_events=events,
        root_hash=root_hash,
    )

    # Verify export
    print(f"[OK] Evidence bundle created:")
    print(f"  - Decision ID: {evidence.decision_id[:8]}...")
    print(f"  - Status: {evidence.status}")
    print(f"  - Winning rule: {evidence.winning_rule}")
    print(f"  - Audit events: {len(evidence.audit_events)}")
    print(f"  - Root hash: {evidence.root_hash[:16]}...")

    # Verify integrity
    is_valid = evidence.verify()
    print(f"[OK] Evidence verification: {is_valid}")
    assert is_valid, "Evidence should be tamper-free"

    # Verify JSON export
    json_str = evidence.to_json()
    print(f"[OK] JSON export: {len(json_str)} chars")
    assert decision_id in json_str, "Decision ID should be in export"
    assert root_hash in json_str, "Root hash should be in export"

    # Simulate tampering and verify detection
    tampered_events = [
        AuditEvent(
            event_id=1,
            event_type="action_received",
            actor_id=None,
            payload={"action_name": "llm.generate", "tampered": True},
            event_ts=now,
        ),
    ] + events[1:]

    tampered_evidence = DecisionEvidence(
        decision_id=decision_id,
        action_id=action_id,
        status="blocked",
        winning_rule="spend_limit_exceeded",
        reason="Budget would be exceeded",
        created_at=now,
        policy_snapshot_id=str(uuid.uuid4()),
        audit_events=tampered_events,
        root_hash=root_hash,  # Use the original hash (now invalid)
    )

    is_tampered = tampered_evidence.verify()
    print(f"[OK] Tamper detection: {not is_tampered}")
    assert not is_tampered, "Tampered evidence should fail verification"

    print("\n[OK] WEDGE B VERIFIED: Evidence is tamper-evident and exportable")
    return True


async def main():
    """Run all wedge verifications."""
    print("\n" + "=" * 70)
    print("CITADEL WEDGE E2E VERIFICATION")
    print("=" * 70)

    try:
        wedge_a_ok = await test_wedge_a_spend_enforcement()
        wedge_b_ok = await test_wedge_b_evidence_export()

        print("\n" + "=" * 70)
        print("VERIFICATION COMPLETE")
        print("=" * 70)
        print("[OK] Wedge A (Hard Cost Enforcement): VERIFIED")
        print("[OK] Wedge B (Evidence Export + Verification): VERIFIED")
        print("\nConclusion: Both wedges are functional and ready for testing.")
        print("=" * 70)

        return True

    except Exception as e:
        print(f"\n[FAIL] VERIFICATION FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
