# Maintainer Guide

> **What this doc covers:** How maintainers review PRs, cut releases, handle breaking changes, and enforce quality standards. This is the playbook for anyone with merge access.

---

## 🎯 Maintainer Responsibilities

Maintainers are trusted to:
1. **Review PRs** fairly, thoroughly, and promptly
2. **Merge only green PRs** — CI must pass
3. **Protect the codebase** — reject PRs that lower quality
4. **Cut releases** when the codebase is ready
5. **Enforce the license model** — respect Apache 2.0 vs BSL 1.1 boundaries
6. **Be welcoming** — especially to first-time contributors

---

## 🔍 How to Review a PR

### The Review Checklist

Before approving, verify:

- [ ] **Purpose is clear** — I understand *why* this change exists
- [ ] **Scope is appropriate** — The PR does one thing well
- [ ] **Tests exist** — New code has tests; changed code has updated tests
- [ ] **CI passes** — All checks are green
- [ ] **No security regressions** — Especially for `apps/runtime/` changes
- [ ] **No breaking changes** — Unless explicitly discussed and versioned
- [ ] **Documentation updated** — If user-facing behavior changed
- [ ] **CHANGELOG updated** — If this is a user-facing fix or feature
- [ ] **License respected** — Code in `packages/` is Apache 2.0; `apps/runtime/` is BSL 1.1

### Review Comments: Be Constructive

**Instead of:**
> "This is wrong."

**Say:**
> "Could you clarify why you chose X over Y? The existing pattern in `executor.py` uses Z, which might be more consistent here."

**Instead of:**
> "Fix this."

**Say:**
> "Consider adding a test for the edge case where `tenant_id` is None. See `test_tenant_context.py` for an example."

### Review Speed

| PR Type | Target Review Time |
|---|---|
| `good first issue` / docs | Within 24 hours |
| Bug fix | Within 48 hours |
| Feature | Within 72 hours |
| Breaking change / security | Within 24 hours, with 2 reviewers |

### When to Request Changes

Request changes (don't approve) when:
- Tests are missing or insufficient
- Security implications are unclear
- The change breaks existing tests
- Documentation is missing for user-facing changes
- The PR does too many things (ask to split)

### When to Approve

Approve when:
- All checklist items pass
- The change is well-tested
- The purpose and scope are clear
- You're confident it won't break production

### Merge Strategy

We use **Squash and Merge** for most PRs:

```
git checkout master
git pull upstream master
git merge --squash feature/branch-name
```

This keeps the `master` history clean with one commit per PR. The commit message should follow Conventional Commits format.

**Exception:** For large, multi-commit refactors where individual commits tell a story, use a regular merge with a merge commit.

---

## 🏷️ Release Process

### Pre-Release Quality Gate

Before cutting any release, the maintainer must run the QA gate and verify three critical items. This is non-negotiable — skipping any of these blocks the release.

**1. Review QA gate evidence**
Read `docs/QA_GATE_EVIDENCE.md` and confirm every checklist item in that document is satisfied. This includes test coverage, lint status, type-check status, and migration readiness. If the QA gate evidence is stale, update it before proceeding.

**2. Verify backward compatibility of the public API**
The public API surface is `packages/sdk-python/citadel_governance/`. Before any release, run the SDK tests and confirm that existing SDK methods still work:
```bash
cd packages/sdk-python
pytest tests/ -v
```
If a release includes a breaking change to the public API, it **must** be a major version bump and must include a migration guide.

**3. Verify security tests pass for sensitive areas**
For any release that touches authentication, tokens, billing, or the governance kernel, run the full security test suite:
```bash
pytest tests/security/ -v
```
If any security test fails, the release is blocked until the failure is resolved. This applies to:
- `apps/runtime/citadel/auth/`
- `apps/runtime/citadel/tokens/`
- `apps/runtime/citadel/billing/`
- `apps/runtime/citadel/core/`
- `apps/runtime/citadel/execution/kernel.py`

### When to Release

Release when:
- A critical bug is fixed
- A significant feature is complete
- Enough small fixes have accumulated (patch release)
- The CHANGELOG has meaningful entries

### Release Checklist

```
□ All tests pass on master
□ CHANGELOG.md is updated
□ Version bumped in all relevant files
□ No open critical issues
□ Migration files are ready (if schema changed)
□ QA gate evidence reviewed (see docs/QA_GATE_EVIDENCE.md)
□ Backward compatibility of public API verified (packages/sdk-python/)
□ Security tests pass: pytest tests/security/ -v
```

**Security release rule:** Any release touching `apps/runtime/citadel/auth/`, `citadel/tokens/`, `citadel/billing/`, or the governance kernel (`citadel/core/`, `citadel/execution/kernel.py`) **must** pass `pytest tests/security/` before tagging.

### Version Bump Locations

| File | Field | Example |
|---|---|---|
| `pyproject.toml` (root) | `[project] version` | `0.2.2` |
| `packages/sdk-python/pyproject.toml` | `[project] version` | `0.2.2` |
| `apps/runtime/citadel/__init__.py` | `__version__` | `"0.2.2"` |
| `apps/runtime/citadel/config.py` | `app_version` | `"0.2.2"` |

### Release Steps

```bash
# 1. Ensure master is green
git checkout master
git pull upstream master

# 2. Create release branch
git checkout -b release/v0.2.2

# 3. Update versions and CHANGELOG
#    (edit files manually or use bump-my-version)

# 4. Commit
git add -A
git commit -m "chore(release): bump version to 0.2.2"

# 5. Open PR for the release (optional but recommended for visibility)
#    This gives other maintainers a chance to catch issues

# 6. After PR is approved, tag and push
git checkout master
git merge release/v0.2.2 --no-ff
git tag -a v0.2.2 -m "Release v0.2.2"
git push upstream master --tags

# 7. Delete release branch
git branch -d release/v0.2.2
```

### SDK Release to PyPI

The SDK (`packages/sdk-python/`) is auto-deployed to PyPI by CI when `PYPI_API_TOKEN` is configured. If you need to release manually:

```bash
cd packages/sdk-python
python -m build
python -m twine upload dist/*
```

### Post-Release

1. Create a [GitHub Release](https://github.com/casss20/citadel-sdk/releases) with release notes
2. Announce in Discord #announcements
3. Update the docs site if needed
4. Monitor error rates for 24 hours

---

## 📋 Changelog & Versioning

### CHANGELOG.md Format

```markdown
## [0.2.2] — 2026-05-01

### Added
- New feature description

### Fixed
- Bug fix description

### Changed
- Breaking or significant change

### Security
- Security fix description

[0.2.2]: https://github.com/casss20/citadel-sdk/compare/v0.2.1...v0.2.2
```

Follow [Keep a Changelog](https://keepachangelog.com/) format with these sections:
- `Added` — New features
- `Changed` — Changes to existing functionality
- `Deprecated` — Soon-to-be-removed features
- `Removed` — Removed features
- `Fixed` — Bug fixes
- `Security` — Security fixes

### Versioning Rules

| Change Type | Version Bump | Example |
|---|---|---|
| Bug fix | Patch | `0.2.1` → `0.2.2` |
| New feature (backward compatible) | Minor | `0.2.1` → `0.3.0` |
| Breaking change | Major | `0.2.1` → `1.0.0` |
| Security fix | Patch (urgent) | `0.2.1` → `0.2.2` |

### Deprecation Policy

Before removing a public API:
1. Mark as deprecated in the current minor version (add `DeprecationWarning`)
2. Document the replacement in CHANGELOG.md
3. Remove in the next major version

Example:
```python
import warnings

def old_function():
    warnings.warn(
        "old_function is deprecated. Use new_function instead.",
        DeprecationWarning,
        stacklevel=2,
    )
    return new_function()
```

---

## 💥 Handling Breaking Changes

### What Counts as Breaking

A breaking change is any change that could cause existing integrations to fail:

- Removing or renaming a public API method
- Changing the return type of a public method
- Changing HTTP endpoint paths or request/response schemas
- Changing database schema in a non-backward-compatible way
- Removing environment variables or changing their behavior

### Breaking Change Process

1. **Discuss first** — Open a GitHub Discussion or RFC issue before implementing
2. **Version appropriately** — Must be a MAJOR version bump
3. **Migration guide** — Write a `docs/public/migration-guides/vX-Y-Z.md`
4. **Deprecation period** — If possible, support both old and new for one minor version
5. **Announce** — Post in Discord and GitHub Discussions

### RFC Template for Breaking Changes

```markdown
# RFC: Title

## Summary
One paragraph description.

## Motivation
Why is this change needed?

## Detailed Design
Technical details of the change.

## Breaking Changes
List of what breaks and why.

## Migration Guide
How users update their code.

## Timeline
When will this be implemented and released?
```

---

## 🛡️ Quality Bar Before Merging

### Code Quality Standards

| Metric | Minimum | Target |
|---|---|---|
| Test coverage | 70% | 85% |
| Lint errors | 0 | 0 |
| Type check errors | 0 | 0 |
| Security scan issues | 0 critical/high | 0 |
| Documentation for new features | Required | Required |

### Security Review Requirements

PRs touching these areas need **2 maintainer approvals**:
- `apps/runtime/citadel/security/`
- `apps/runtime/citadel/auth/`
- `apps/runtime/citadel/tokens/`
- `apps/runtime/citadel/billing/`
- `db/schema.sql` (RLS policy changes)

### Performance Review

PRs that could affect performance at scale need:
- Benchmark results (before vs after)
- Explanation of big-O complexity changes
- Consideration for database query patterns

---

## 🚨 Incident Response

### If a Bad Release Goes Out

```bash
# 1. Assess impact
#    Check: Fly.io dashboard, error logs, user reports

# 2. Rollback (if needed)
#    Fly.io: flyctl deploy --app citadel-sdk --image <previous-image>
#    Or: git revert the bad commit on master

# 3. Fix forward
#    Create a hotfix branch from the last good tag
#    git checkout -b hotfix/v0.2.2 v0.2.1
#    # Fix the issue
#    git commit -m "fix(runtime): ..."
#    git tag -a v0.2.2 -m "Hotfix v0.2.2"
#    git push upstream hotfix/v0.2.2 --tags

# 4. Post-mortem
#    Write up what happened, why, and how to prevent it
```

### Security Incident Response

1. **Immediate:** Assess scope and contain (revoke keys, disable features)
2. **Within 1 hour:** Notify affected users if data was at risk
3. **Within 24 hours:** Deploy fix
4. **Within 1 week:** Publish post-mortem (if appropriate)

---

## 👥 Onboarding New Maintainers

### Criteria

- Consistent, high-quality contributions over 3+ months
- Deep understanding of the architecture
- Good judgment on PR reviews
- Alignment with project values

### Process

1. Existing maintainer nominates candidate
2. Discussion among current maintainers (private channel)
3. Invite to maintainer team
4. Add to:
   - GitHub repo with write access
   - Fly.io team
   - Vercel team
   - Discord admin role

### New Maintainer Checklist

```
□ Added to GitHub repo (write access)
□ Added to Fly.io organization
□ Added to Vercel team
□ Added to PyPI project (if releasing SDK)
□ Has FLY_API_TOKEN for emergency deploys
□ Has VERCEL_TOKEN for emergency deploys
□ Subscribed to repo notifications
□ Added to private maintainer Discord channel
```

---

## 📜 License Enforcement

### What to Watch For in PRs

- ❌ Code in `packages/` that imports from proprietary `enterprise/`
- ❌ Proprietary code submitted to `packages/`
- ❌ Copy-pasted code without compatible license
- ❌ Patents or trade secrets in contributions

### If Unsure About a License Question

- Check [LICENSING.md](../LICENSING.md)
- Ask in the private maintainer channel
- When in doubt, ask the contributor to clarify

---

## 📞 Escalation Paths

| Situation | Who to Contact | How |
|---|---|---|
| Security incident | All maintainers | Discord #maintainers + email |
| License question | Project lead | Discord DM |
| Disagreement on PR | Another maintainer | Discord #maintainers |
| Infrastructure down | Whoever has deploy keys | Discord #maintainers |
| Community conflict | Any two maintainers | Discord #moderation |

---

## 🔗 Related Docs

- [CONTRIBUTING.md](../CONTRIBUTING.md) — Contributor guidelines
- [docs/DEVELOPMENT.md](DEVELOPMENT.md) — Day-to-day workflow
- [docs/PROJECT_STRUCTURE.md](PROJECT_STRUCTURE.md) — Architecture overview
- [LICENSING.md](../LICENSING.md) — License boundaries
