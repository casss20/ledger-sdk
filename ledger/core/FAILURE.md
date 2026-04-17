# FAILURE.md — Recovery Protocol

## Ownership

- OWNS: failure handling, recovery decisions, escalation, rollback
- DOES NOT OWN: normal execution, success cases, relationship philosophy

## Purpose

FAILURE decides what to do when things break.

- Retry internally?
- Ask the user?
- Stop execution?
- Rollback?

---

## Failure Types

### Execution Failure
EXECUTOR cannot continue after 2 correction attempts.

Options:
- Escalate to PLANNER for replan
- Ask user for guidance
- Stop with partial results

### Planning Failure
PLANNER cannot produce valid plan.

Options:
- Reduce scope
- Gather more information
- Ask user for clarification
- Stop

### Critic Failure
CRITIC cannot resolve contradiction.

Options:
- Flag for user review
- Proceed with warning
- Stop

### Governor Failure
GOVERNOR escalation changes execution materially.

Options:
- Follow new direction
- Ask for resolution
- Stop

---

## Decision Tree

1. **Can retry?** → Retry with fix
2. **Needs clarity?** → Ask user
3. **Cannot continue?** → Stop
4. **Partial results?** → Deliver with note

---

## Rollback

If failure requires undoing work:
- Document what to undo
- Execute rollback plan
- Verify state
- Report completion

---

## Logging

Log all failures to AUDIT.md:
- What failed
- Why
- What was done
- Result

---

## Principle

Failures are data.
Recovery is skill.

Handle gracefully.
Learn visibly.

---

> 🧠 Final line
> This is the recovery system.
> It turns failure into learning, not chaos.