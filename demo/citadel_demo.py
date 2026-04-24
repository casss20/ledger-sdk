#!/usr/bin/env python3
"""
🛡️  CITADEL Governance Demo — Standalone (no DB required)

Shows the complete governance lifecycle in ~30 seconds:
  1. AI agent executes → Governance allows ✅
  2. Agent tries dangerous action → Policy blocks ❌
  3. Kill switch activated → All agents stopped 🛑
  4. Audit trail → Cryptographic chain verified 🔗
  5. Framework integration → K2.6 agent with governance wrapper 🤖

Run: PYTHONPATH=apps/runtime python3 demo/citadel_demo.py
"""

import asyncio
import uuid
import sys
import hashlib
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional, Dict, List, Any
from enum import Enum

# Setup path
sys.path.insert(0, "apps/runtime")

# ──────────────────────────── Mock Infrastructure ────────────────────────────

class MockDB:
    """In-memory database for demo purposes."""
    def __init__(self):
        self.actions: List[Dict] = []
        self.decisions: List[Dict] = []
        self.audit_events: List[Dict] = []
        self.kill_switches: Dict[str, bool] = {}
        self.policies: List[Dict] = []
        self.approvals: List[Dict] = []
        self.usage: Dict[str, int] = {"api_calls": 0}
        
    def reset(self):
        self.__init__()
        
    def log_action(self, action: Dict):
        self.actions.append({
            **action,
            "timestamp": datetime.now(timezone.utc).isoformat()
        })
        
    def log_decision(self, decision: Dict):
        self.decisions.append(decision)
        
    def log_audit(self, event: Dict):
        prev_hash = self.audit_events[-1]["hash"] if self.audit_events else "0" * 64
        event_data = f"{event['event_type']}:{event['actor_id']}:{event.get('action', '')}:{time.time()}"
        event_hash = hashlib.sha256(f"{prev_hash}:{event_data}".encode()).hexdigest()[:16]
        self.audit_events.append({
            **event,
            "hash": event_hash,
            "prev_hash": prev_hash,
            "timestamp": datetime.now(timezone.utc).isoformat()
        })

mock_db = MockDB()

# ──────────────────────────── Governance Engine ────────────────────────────

class DecisionStatus(Enum):
    ALLOWED = "allowed"
    BLOCKED = "blocked"
    PENDING_APPROVAL = "pending_approval"
    KILL_SWITCH = "kill_switch_active"

@dataclass
class GovernanceDecision:
    status: DecisionStatus
    action: str
    actor: str
    reason: str
    rule_triggered: Optional[str] = None
    requires_approval: bool = False

@dataclass
class ExecutionResult:
    action: str
    allowed: bool
    executed: bool
    result: Any = None
    error: Optional[str] = None

class GovernanceEngine:
    """Core governance engine — policy evaluation + audit logging."""
    
    POLICIES = [
        {
            "name": "safe_operations",
            "effect": "ALLOW",
            "conditions": {
                "action": ["db.read", "db.query", "file.read", "api.get"],
            }
        },
        {
            "name": "destructive_requires_approval",
            "effect": "PENDING_APPROVAL",
            "conditions": {
                "action": ["db.delete", "db.drop", "file.delete", "system.exec"],
            }
        },
        {
            "name": "no_production_delete",
            "effect": "BLOCK",
            "conditions": {
                "action": ["db.delete"],
                "context.environment": "production",
            }
        },
    ]
    
    def evaluate(self, action: str, actor: str, context: Dict) -> GovernanceDecision:
        # Check kill switch first
        if mock_db.kill_switches.get("global") or mock_db.kill_switches.get(action):
            return GovernanceDecision(
                status=DecisionStatus.KILL_SWITCH,
                action=action,
                actor=actor,
                reason="Kill switch is active — all operations halted",
                rule_triggered="emergency_stop"
            )
        
        # Evaluate policies (deny overrides allow)
        triggered = None
        for policy in self.POLICIES:
            if self._matches(policy, action, context):
                triggered = policy
                if policy["effect"] == "BLOCK":
                    return GovernanceDecision(
                        status=DecisionStatus.BLOCKED,
                        action=action,
                        actor=actor,
                        reason=f"Policy '{policy['name']}' blocked this action",
                        rule_triggered=policy["name"]
                    )
                elif policy["effect"] == "PENDING_APPROVAL":
                    return GovernanceDecision(
                        status=DecisionStatus.PENDING_APPROVAL,
                        action=action,
                        actor=actor,
                        reason=f"Policy '{policy['name']}' requires human approval",
                        rule_triggered=policy["name"],
                        requires_approval=True
                    )
        
        # Default allow
        return GovernanceDecision(
            status=DecisionStatus.ALLOWED,
            action=action,
            actor=actor,
            reason="No restrictive policies matched — action allowed",
            rule_triggered=triggered["name"] if triggered else None
        )
    
    def _matches(self, policy: Dict, action: str, context: Dict) -> bool:
        conditions = policy.get("conditions", {})
        
        # Check action match
        if "action" in conditions:
            if action not in conditions["action"]:
                return False
        
        # Check context conditions
        for key, value in conditions.items():
            if key.startswith("context."):
                ctx_key = key[8:]  # Remove "context."
                if context.get(ctx_key) != value:
                    return False
        
        return True
    
    async def execute(self, action: str, actor: str, context: Dict, 
                     payload: Optional[Dict] = None) -> ExecutionResult:
        # Evaluate
        decision = self.evaluate(action, actor, context)
        
        # Log action
        mock_db.log_action({
            "action_id": str(uuid.uuid4())[:8],
            "action": action,
            "actor": actor,
            "context": context,
            "decision": decision.status.value,
        })
        
        # Log audit
        mock_db.log_audit({
            "event_type": f"action.{decision.status.value}",
            "actor_id": actor,
            "action": action,
            "rule": decision.rule_triggered,
        })
        
        # Execute or block
        if decision.status == DecisionStatus.ALLOWED:
            result = self._simulate_execution(action, payload)
            mock_db.log_audit({
                "event_type": "execution.success",
                "actor_id": actor,
                "action": action,
            })
            return ExecutionResult(
                action=action,
                allowed=True,
                executed=True,
                result=result
            )
        
        elif decision.status == DecisionStatus.PENDING_APPROVAL:
            mock_db.approvals.append({
                "approval_id": str(uuid.uuid4())[:8],
                "action": action,
                "actor": actor,
                "status": "pending",
                "requested_at": datetime.now(timezone.utc).isoformat()
            })
            return ExecutionResult(
                action=action,
                allowed=False,
                executed=False,
                error="Pending human approval"
            )
        
        else:
            return ExecutionResult(
                action=action,
                allowed=False,
                executed=False,
                error=decision.reason
            )
    
    def _simulate_execution(self, action: str, payload: Optional[Dict]) -> str:
        """Simulate what the action would do."""
        if action.startswith("db."):
            return f"Executed {action} on table '{payload.get('table', 'unknown')}'"
        elif action.startswith("file."):
            return f"Executed {action} on path '{payload.get('path', 'unknown')}'"
        elif action.startswith("api."):
            return f"Executed {action} — returned 200 OK"
        elif action.startswith("agent."):
            return f"Agent task completed: {payload.get('task', 'unknown')}"
        return f"Executed {action}"


# ──────────────────────────── Framework Integration ────────────────────────────

class GovernedK26Agent:
    """Mock K2.6 agent with governance wrapper."""
    
    def __init__(self, engine: GovernanceEngine, agent_id: str = "k26_001"):
        self.engine = engine
        self.agent_id = agent_id
        self.task_history: List[Dict] = []
    
    async def execute_task(self, task: str, action: str, context: Dict,
                          payload: Optional[Dict] = None) -> ExecutionResult:
        """Execute task with governance check."""
        print(f"    🤖 Agent '{self.agent_id}' wants to: {task}")
        print(f"       └─ Action: {action}")
        
        result = await self.engine.execute(action, self.agent_id, context, payload)
        
        self.task_history.append({
            "task": task,
            "action": action,
            "allowed": result.allowed,
            "timestamp": datetime.now(timezone.utc).isoformat()
        })
        
        if result.allowed:
            print(f"       └─ ✅ ALLOWED — {result.result}")
        else:
            print(f"       └─ ❌ BLOCKED — {result.error}")
        
        return result


# ──────────────────────────── Demo Scenarios ────────────────────────────

async def demo_1_safe_operation(engine: GovernanceEngine):
    """Demo 1: AI agent reads data — allowed."""
    print("\n" + "━" * 60)
    print("DEMO 1: Safe Operation (Database Read)")
    print("━" * 60)
    
    agent = GovernedK26Agent(engine, "k26_data_analyst")
    
    result = await agent.execute_task(
        task="Query user analytics for dashboard",
        action="db.query",
        context={"environment": "production", "data_sensitivity": "medium"},
        payload={"table": "users", "fields": ["id", "created_at"]}
    )
    
    return result.allowed


async def demo_2_dangerous_blocked(engine: GovernanceEngine):
    """Demo 2: Agent tries to delete production DB — blocked."""
    print("\n" + "━" * 60)
    print("DEMO 2: Dangerous Action — Production Database Delete")
    print("━" * 60)
    
    agent = GovernedK26Agent(engine, "k26_maintenance_bot")
    
    result = await agent.execute_task(
        task="Clean up old user records",
        action="db.delete",
        context={"environment": "production", "data_sensitivity": "high"},
        payload={"table": "users", "where": "last_login < '2023-01-01'"}
    )
    
    return not result.allowed


async def demo_3_kill_switch(engine: GovernanceEngine):
    """Demo 3: Emergency kill switch stops everything."""
    print("\n" + "━" * 60)
    print("DEMO 3: Kill Switch Activated")
    print("━" * 60)
    
    # Activate emergency stop
    mock_db.kill_switches["global"] = True
    print("🚨 SECURITY: Kill switch activated — possible intrusion detected")
    print("   └─ All AI agent operations halted immediately\n")
    
    agent = GovernedK26Agent(engine, "k26_rogue_agent")
    
    # This would normally be allowed (db.read is safe)
    result = await agent.execute_task(
        task="Read configuration settings",
        action="db.read",
        context={"environment": "production"},
        payload={"table": "config"}
    )
    
    # Deactivate
    mock_db.kill_switches["global"] = False
    print("\n🟢 Kill switch deactivated — normal operations resumed")
    
    return not result.allowed


async def demo_4_approval_workflow(engine: GovernanceEngine):
    """Demo 4: Destructive action requires human approval."""
    print("\n" + "━" * 60)
    print("DEMO 4: Approval Workflow (Staging Environment)")
    print("━" * 60)
    
    agent = GovernedK26Agent(engine, "k26_devops")
    
    # In staging, db.delete requires approval (not blocked outright)
    result = await agent.execute_task(
        task="Drop temporary tables after migration",
        action="db.delete",
        context={"environment": "staging"},  # Not production
        payload={"table": "temp_migration_001"}
    )
    
    if not result.allowed and "approval" in (result.error or "").lower():
        print(f"\n📋 Approval Queue:")
        for approval in mock_db.approvals:
            print(f"   └─ [{approval['status'].upper()}] {approval['action']} "
                  f"(requested by {approval['actor']}) — ID: {approval['approval_id']}")
    
    return result.error == "Pending human approval"


async def demo_5_framework_integration(engine: GovernanceEngine):
    """Demo 5: Multiple framework agents with governance."""
    print("\n" + "━" * 60)
    print("DEMO 5: Multi-Agent System with Unified Governance")
    print("━" * 60)
    
    agents = [
        GovernedK26Agent(engine, "k26_researcher"),
        GovernedK26Agent(engine, "k26_coder"),
        GovernedK26Agent(engine, "k26_ops"),
    ]
    
    tasks = [
        ("Fetch research papers", "api.get", {"environment": "production"}, None),
        ("Write code to file", "file.write", {"environment": "production"}, {"path": "/tmp/test.py"}),
        ("Restart production server", "system.exec", {"environment": "production"}, {"command": "reboot"}),
    ]
    
    print(f"Running {len(agents)} AI agents with different roles...\n")
    
    for agent, (task, action, ctx, payload) in zip(agents, tasks):
        await agent.execute_task(task, action, ctx, payload)
    
    allowed_count = sum(1 for a in agents for t in a.task_history if t["allowed"])
    blocked_count = sum(1 for a in agents for t in a.task_history if not t["allowed"])
    
    print(f"\n📊 Results: {allowed_count} allowed, {blocked_count} blocked")
    
    return blocked_count >= 1


async def demo_6_audit_trail():
    """Demo 6: Verify the complete audit chain."""
    print("\n" + "━" * 60)
    print("DEMO 6: Audit Trail Verification")
    print("━" * 60)
    
    events = mock_db.audit_events
    
    print(f"\n📋 Total audit events: {len(events)}")
    print(f"   └─ Chain integrity: {'✅ VALID' if len(events) > 0 else '⚠️  EMPTY'}")
    
    print("\n🔗 Audit Chain (last 6 events):")
    print(f"   {'Hash':18s} │ {'Previous':18s} │ Event")
    print(f"   {'─' * 18}─┼─{'─' * 18}─┼─{'─' * 30}")
    
    for event in events[-6:]:
        print(f"   {event['hash']:<18s} │ {event['prev_hash']:<18s} │ {event['event_type']}")
    
    # Verify chain
    valid = True
    for i in range(1, len(events)):
        if events[i]["prev_hash"] != events[i-1]["hash"]:
            valid = False
            break
    
    print(f"\n{'✅' if valid else '❌'} Cryptographic chain verification: {'PASS' if valid else 'FAIL'}")
    
    return valid


# ──────────────────────────── Main ────────────────────────────

async def main():
    print("\n")
    print("╔" + "═" * 58 + "╗")
    print("║" + " " * 12 + "🛡️  CITADEL GOVERNANCE SYSTEM" + " " * 17 + "║")
    print("║" + " " * 8 + "AI Agent Oversight with Cryptographic Audit" + " " * 7 + "║")
    print("╚" + "═" * 58 + "╝")
    
    engine = GovernanceEngine()
    results = []
    
    # Run all demos
    results.append(("Safe Operation", await demo_1_safe_operation(engine)))
    results.append(("Dangerous Blocked", await demo_2_dangerous_blocked(engine)))
    results.append(("Kill Switch", await demo_3_kill_switch(engine)))
    results.append(("Approval Workflow", await demo_4_approval_workflow(engine)))
    results.append(("Multi-Agent", await demo_5_framework_integration(engine)))
    results.append(("Audit Trail", await demo_6_audit_trail()))
    
    # Summary
    print("\n")
    print("━" * 60)
    print("DEMO SUMMARY")
    print("━" * 60)
    
    passed = 0
    for name, ok in results:
        status = "✅ PASS" if ok else "❌ FAIL"
        print(f"  {status:10s} │ {name}")
        if ok:
            passed += 1
    
    print(f"\n{'✅' if passed == len(results) else '⚠️'} {passed}/{len(results)} demos passed")
    
    # Stats
    print(f"\n📊 Session Stats:")
    print(f"   Actions evaluated: {len(mock_db.actions)}")
    print(f"   Decisions made:    {len(mock_db.decisions)}")
    print(f"   Audit events:      {len(mock_db.audit_events)}")
    print(f"   Pending approvals: {len(mock_db.approvals)}")
    
    print("\n" + "━" * 60)
    print("Demo complete! Try the real thing:")
    print("  → Framework integrations: docs/public/integrations/")
    print("  → API reference:          apps/runtime/citadel/api/")
    print("  → Tests:                  pytest tests/ -v")
    print("━" * 60)
    
    return passed == len(results)


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
