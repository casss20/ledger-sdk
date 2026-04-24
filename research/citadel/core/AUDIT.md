# AUDIT.md — Decision Integrity Log

## Purpose

Immutable record of significant governance decisions.

- What happened
- Why it happened
- Who/what was involved
- Result

---

## What to Log

Log to AUDIT.md for:
- GOVERNOR level 3 escalation
- Repeated or significant level 2 escalation
- Protected file modification
- Rollback events
- SELF-MOD rejection
- Rule conflict stopping execution
- External action blocked by guardrail
- Failure materially changing outcome

Do NOT log:
- Normal rewrites
- Small fixes
- Ordinary planning revisions
- Low-impact internal corrections

---

## Log Format

```
[YYYY-MM-DD HH:MM UTC] EVENT_TYPE | ACTOR | RESOURCE | OUTCOME
- Context: brief description
- Decision: what was decided
- Reasoning: why
- Metadata: relevant ids, hashes
```

---

## Integrity

AUDIT.md is:
- Append-only
- Never rewritten silently
- Referenced in disputes

Protect its integrity.

---

## Principle

Trust requires verification.
Verification requires record.

Log what matters.

---

> 🧠 Final line
> This is the immutable record.
> It keeps the system honest by making decisions visible.