# HEARTBEAT.md â€” System Health Polling

## Purpose

Periodic checks to keep CITADEL healthy between sessions.

---

## Triggers

### Daily (light)
- Check urgent messages
- Check calendar

### Weekly (medium)
- Review memory accumulation
- Check priority drift
- File tracker run

### Monthly (heavy)
- Full system audit
- PRUNE enforcement
- Version consistency
- Skill security sweep

---

## Skill Security Sweep

When skills are added:
1. Vet new skills
2. Audit existing
3. Check evolution
4. Log results

---

## Manual Triggers

- "Run audit" â†’ full system check
- "Run integrity check" â†’ verify files
- "Check for new files" â†’ run file_tracker
- "Run PRUNE" â†’ context cleanup

---

## Output

```
=== HEARTBEAT CHECK ===
Date: YYYY-MM-DD
Status: OK / NEEDS ATTENTION

=== FINDINGS ===
- Files: [status]
- Skills: [count] installed
- Memory: Within limits / Over threshold

=== ACTION ===
- [Action item]
```

---

> ðŸ§  Final line
> HEARTBEAT keeps the system alive and sharp between sessions.