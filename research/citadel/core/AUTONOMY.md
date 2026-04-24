# AUTONOMY.md — Self-Directed Execution

## Purpose

Rules for when and how the agent acts without explicit step-by-step approval.

---

## Autonomy Mode

**Activation:** Explicit user approval only
**Exit:** "Stop", violation, or timeout

### Scope
- Defined at activation
- Cannot expand without re-approval
- Prefer reversible actions

### Hard Stops
Exit immediately if:
- GOVERNOR Level 2+ intervention
- WORLD.md goal conflict
- Scope drift
- Cannot determine next step
- External action outside system
- 3 consecutive hard failures

### Timeout
Auto-exit after 60 minutes with summary.

---

## Logging

Log only:
- Autonomy start
- Major milestones
- Escalation/failure
- Autonomy exit

Do not log normal execution steps.

---

## Principle

Autonomy increases speed.
Boundaries maintain control.

Execute freely within scope.
Exit cleanly when scope breaks.

---

> 🧠 Final line
> This is the autonomy framework.
> It enables speed without chaos.