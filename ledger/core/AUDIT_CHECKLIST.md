# Monthly Audit Checklist

Run on the 1st of each month via HEARTBEAT or CRON.

---

## 1. File Lifecycle Check

- [ ] Review all .md files for usage in past 30 days
- [ ] Flag files with <5% activation
- [ ] Check for redundant content across files
- [ ] Apply PRUNE Rule #1: merge, archive, or delete unused

---

## 2. Ownership Validation

- [ ] Verify each file's ownership matches actual behavior
- [ ] Check for boundary creep (layers acting outside ownership)
- [ ] Confirm conflict resolution hierarchy is being followed

---

## 3. Consistency Scan

- [ ] Cross-reference START.md hierarchy with RUNTIME.md
- [ ] Check AGENTS.md against actual activation patterns
- [ ] Verify CHANGELOG.md is updated (version bumps?)

---

## 4. Governance Health

- [ ] Review AUDIT.md for override patterns
- [ ] Check GOVERNOR escalation frequency
- [ ] Verify SELF-MOD modifications are logged
- [ ] Confirm CONSTITUTION has no unauthorized changes

---

## 5. Token Efficiency Review

- [ ] Check Fast Path usage (should be 80%+ of responses)
- [ ] Review verbose outputs from past month
- [ ] Verify MEMORY.md isn't growing unbounded
- [ ] Confirm PRUNE is being triggered appropriately

---

## 6. Drift Detection

- [ ] Review ADAPTATION calibration changes
- [ ] Check for pattern shifts in user behavior
- [ ] Verify GOVERNOR thresholds still make sense
- [ ] Confirm calibration reflects actual consistency

---

## 7. Active Layer Count

- [ ] Count how many files actually activated in past month
- [ ] Compare to CORE 6 baseline
- [ ] Flag any new files added without justification

---

## Output

After completion:
- Log findings in `memory/YYYY-MM-01-audit.md`
- If issues found → create action items
- If critical drift → alert user immediately

---

## Principle

The audit exists to keep the system sharp.

Not to create busywork.
Not to find problems constantly.

To ensure the architecture stays true to its design.

> **A system that doesn't audit itself will eventually drift.**
---

> 🧠 Final line
> This is the monthly health check.
> It ensures the system stays true to its design, not just its latest edit.
