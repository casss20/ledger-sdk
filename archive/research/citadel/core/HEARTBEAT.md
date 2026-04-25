# HEARTBEAT.md — System Health Polling

## Purpose

Periodic checks to keep Citadel healthy between sessions.

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

- "Run audit" → full system check
- "Run integrity check" → verify files
- "Check for new files" → run file_tracker
- "Run PRUNE" → context cleanup

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

> 🧠 Final line
> HEARTBEAT keeps the system alive and sharp between sessions.