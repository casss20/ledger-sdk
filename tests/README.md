# Citadel Kernel Conformance Tests

Test suite proving the governance kernel enforces all control semantics end-to-end.

## Test Coverage

### 10 Deterministic Scenarios

| # | Scenario | Verifies |
|---|----------|----------|
| 1 | **Blocked by Kill Switch** | Emergency stops work, BLOCKED_EMERGENCY decision |
| 2 | **Blocked by Policy** | Policy rules enforced, policy snapshot for replay |
| 3 | **Blocked by Capability Expiry** | Token expiration enforced |
| 4 | **Pending Approval** | High-risk actions queue for human review |
| 5 | **Approval Rejected** | Human rejection blocks action |
| 6 | **Approval Expired** | Timeouts handled correctly |
| 7 | **Allowed + Executed** | Happy path: ALLOWED → EXECUTED → result |
| 8 | **Execution Failed** | Runtime errors captured in decisions |
| 9 | **Idempotency** | Duplicate keys return cached result |
| 10 | **Audit Chain Integrity** | Hash chain valid, tamper-evident |

### Additional Tests

| Test | Verifies |
|------|----------|
| `test_replay_same_inputs_same_output` | Deterministic replay via policy snapshots |
| `test_concurrent_action_isolation` | No cross-contamination under load |

## Running Tests

```bash
# Setup test database
createdb citadel_test
psql citadel_test -f db/schema.sql

# Run all conformance tests
pytest tests/test_kernel_conformance.py -v

# Run single scenario
pytest tests/test_kernel_conformance.py::TestKernelConformance::test_01_blocked_by_kill_switch -v

# Run with coverage
pytest tests/test_kernel_conformance.py --cov=citadel --cov-report=html
```

## Test Structure

```
TestKernelConformance
├── test_01_blocked_by_kill_switch
├── test_02_blocked_by_policy
├── test_03_blocked_by_capability_expiry
├── test_04_pending_approval
├── test_05_approval_rejected
├── test_06_approval_expired
├── test_07_allowed_and_executed
├── test_08_execution_failed
├── test_09_idempotency_duplicate
└── test_10_audit_chain_integrity

TestReplayDeterminism
├── test_replay_same_inputs_same_output
└── test_concurrent_action_isolation
```

## What Each Test Verifies

### Database Writes
Every test confirms:
- `actions` — canonical request recorded
- `decisions` — terminal outcome written
- `audit_events` — chronological trail with hash chain

### Specific Checks

**Kill Switch Test (01)**
- Kill switch enabled in DB
- Action attempted
- BLOCKED_EMERGENCY decision
- Kill switch checked in audit trail

**Policy Test (02)**
- Policy created with BLOCK rule
- Policy snapshot created for replay
- BLOCKED_POLICY decision cites rule

**Capability Test (03)**
- Expired capability token
- BLOCKED_CAPABILITY decision
- Capability token referenced in decision

**Approval Flow (04-06)**
- PENDING_APPROVAL decision created
- Approval queue entry appears
- Human decision updates status
- Expiry handled correctly

**Success Path (07)**
- ALLOWED or EXECUTED status
- Execution result recorded
- Capability consumed atomically

**Failure Path (08)**
- FAILED_EXECUTION status
- Error message captured
- Stack trace available

**Idempotency (09)**
- Same idempotency key
- Same result returned
- No duplicate database entries

**Audit Integrity (10)**
- `verify_audit_chain()` returns valid
- Hash chain unbroken
- Tamper-evident

## Fixtures

| Fixture | Purpose |
|---------|---------|
| `citadel` | Fresh Citadel instance per test |
| `db` | Asyncpg connection for verification |
| `postgres_dsn` | Database connection string |
| `clean_database` | Truncate all tables before each test |

## Assertions

Each test asserts on:
1. **Decision status** — correct terminal state
2. **Database state** — rows exist with correct values
3. **Audit trail** — events recorded in sequence
4. **Views** — operational views show correct data
5. **Integrity** — hash chain, constraints enforced

## Expected Runtime

- Fast tests (< 100ms each): 01, 02, 03, 09
- Medium tests (100-500ms): 04, 05, 06, 07, 08
- Integrity test (500ms+): 10 (scans audit_events)

Total suite: ~3-5 seconds

## CI/CD Integration

```yaml
# .github/workflows/test.yml
- name: Run Kernel Conformance
  run: |
    pip install pytest pytest-asyncio asyncpg
    pytest tests/test_kernel_conformance.py -v --tb=short
    
- name: Verify Audit Chain
  run: |
    psql $DATABASE_URL -c "SELECT * FROM verify_audit_chain();"
```

## Failure Modes

If tests fail, check:

1. **Database not initialized**: Run `db/schema.sql`
2. **Citadel kernel not implemented**: Some tests assume Python methods exist
3. **Async issues**: Ensure `pytest-asyncio` configured
4. **Transaction isolation**: Tests clean DB, but concurrent runs may conflict

## Next Steps

When tests pass, you have proven:
- ✅ Kernel writes to database correctly
- ✅ All control paths deterministic
- ✅ Audit chain integrity maintained
- ✅ Replay supported via snapshots
- ✅ Idempotency works
- ✅ Approval flow functional

This turns "strong schema" into "provable kernel."
