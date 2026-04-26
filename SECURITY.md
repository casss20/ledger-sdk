# Security Policy

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| 0.2.x   | :white_check_mark: |
| < 0.2   | :x:                |

## Reporting a Vulnerability

**Please do not file public issues for security vulnerabilities.**

Instead, report privately to:

- **Email:** security@citadelsdk.com
- **Telegram:** @Anthonycass (for urgent issues)

We will acknowledge receipt within 48 hours and provide a timeline for a fix within 7 days.

## Security Principles

Citadel is a governance SDK that enterprises and AI agents depend on. Our security posture:

1. **Fail-closed by default** — Any error in enforcement logic defaults to blocking, not allowing.
2. **Zero hardcoded secrets** — No default passwords, API keys, or JWT secrets in production code.
3. **Defense in depth** — OWASP controls at multiple layers (middleware, runtime, database).
4. **Observability** — All security events are structured-logged and audit-trailed.
5. **Least privilege** — Every component has minimal required permissions.

## Security Architecture

### Trust Boundaries

```
┌─────────────────────────────────────────────────────────────┐
│                    EXTERNAL CLIENT                          │
│  [Python SDK] [Node.js SDK] [AI Agent] [CLI]                │
└──────────────┬──────────────────────────────────────────────┘
               │ HTTPS + API Key / JWT
               ▼
┌─────────────────────────────────────────────────────────────┐
│                    FASTAPI API LAYER                         │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │   CORS       │  │ Auth (JWT)   │  │ Rate Limit   │      │
│  │   Middleware │  │ + API Key    │  │ + Billing    │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
└──────────────┬──────────────────────────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────────────────────────┐
│              OWASP SECURITY MIDDLEWARE                       │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │ Security     │  │ Input        │  │ SSRF         │      │
│  │ Headers      │  │ Validation   │  │ Protection   │      │
│  │ (HSTS,CSP)   │  │              │  │              │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
└──────────────┬──────────────────────────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────────────────────────┐
│                    GOVERNANCE KERNEL                         │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │ Policy       │  │ Kill Switch  │  │ Audit        │      │
│  │ Engine       │  │ Enforcement  │  │ Anchoring    │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
└──────────────┬──────────────────────────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────────────────────────┐
│              POSTGRESQL + OPTIONAL BLOCKCHAIN                │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │ Row-Level    │  │ Encrypted    │  │ Immutable    │      │
│  │ Security     │  │ Fields       │  │ Audit Log    │      │
│  │ (RLS)        │  │ (at-rest)    │  │ (hash chain) │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
└─────────────────────────────────────────────────────────────┘
```

### Authentication

- **API Keys:** Scoped, revocable. Format: `key_id:scope1,scope2`
- **JWT:** RS256/HS256 with configurable secret. Short-lived access tokens.
- **Agent Identity:** Ed25519 challenge-response for cryptographic auth.

### Authorization

- **RBAC:** Role-based access control (admin, operator, viewer, agent)
- **RLS:** PostgreSQL Row-Level Security enforces tenant isolation at the database layer
- **Policy Engine:** Attribute-based access control for fine-grained governance

## Security Controls

| OWASP | Control | Implementation |
|-------|---------|----------------|
| A01 Broken Access Control | RBAC + RLS + JWT tenant binding | `citadel/auth/` + `citadel/governance/` |
| A02 Security Misconfiguration | 10 security headers, HSTS, CSP | `citadel/security/owasp_middleware.py` |
| A03 Supply Chain | Dependency pinning, SBOM, no dev deps in prod | `requirements.txt`, `package-lock.json` |
| A04 Cryptographic Failures | Ed25519, bcrypt, PBKDF2, challenge-response | `citadel/auth/` |
| A05 Injection | Parameterized queries, input validation | `asyncpg`, `InputValidationMiddleware` |
| A06 Insecure Design | Kill switch, budget enforcement, approvals | `citadel/core/governor.py` |
| A07 Auth Failures | API key + secret + Ed25519 challenge | `citadel/auth/api_key.py`, `citadel/auth/jwt_token.py` |
| A08 Data Integrity | JWT sig verify, request signing, nonces | `citadel/security/` |
| A09 Logging Failures | Structured JSON logging, audit table | `citadel/sre/structured_logging.py` |
| A10 SSRF | URL allowlist, internal IP block | `SSRFProtectionMiddleware` |

## Secret Management

### Environment Variables

All secrets must be set via environment variables. **Never commit secrets to git.**

| Variable | Purpose | Required in Prod |
|----------|---------|-----------------|
| `CITADEL_JWT_SECRET` | JWT signing key | ✅ Yes |
| `CITADEL_API_KEYS` | API key whitelist | ✅ Yes |
| `CITADEL_ADMIN_BOOTSTRAP_PASSWORD` | Bootstrap admin password | ✅ Yes |
| `CITADEL_DATABASE_URL` | PostgreSQL DSN | ✅ Yes |
| `STRIPE_SECRET_KEY` | Payment processing | Only if billing enabled |
| `STRIPE_WEBHOOK_SECRET` | Stripe webhooks | Only if billing enabled |

### Development Mode

In `debug=True` mode:
- JWT secret is **auto-generated per session** (random, not hardcoded)
- API keys should still be set; empty defaults will trigger warnings
- Bootstrap password is auto-generated if not set; a hash hint (not the password) is logged

### Validation

Startup validation (`settings.validate_secrets()`) checks for:
1. Empty or default JWT secrets
2. Empty or default API keys
3. Missing bootstrap password

In production (`debug=False`), missing secrets cause a **fatal startup error**.

## Secure Development

### Pre-commit Checklist

- [ ] No hardcoded passwords, API keys, or tokens
- [ ] No `print()` or `logging.info()` of sensitive data
- [ ] All SQL uses parameterized queries (asyncpg `$1`, `$2`)
- [ ] Input validation on all API endpoints (Pydantic models, FastAPI `Query()` validators)
- [ ] Rate limiting on sensitive endpoints
- [ ] Tests cover both success and failure paths
- [ ] Security tests pass (`pytest tests/security/`)

### Code Review Requirements

PRs touching these areas require **2 maintainer approvals**:
- `apps/runtime/citadel/security/`
- `apps/runtime/citadel/auth/`
- `apps/runtime/citadel/tokens/`
- `apps/runtime/citadel/billing/`
- `apps/runtime/citadel/db/schema.sql`

### Static Analysis

Run security-focused static analysis:

```bash
# Bandit (Python security linter)
bandit -r apps/runtime/citadel/ -f json -o bandit-report.json

# Safety (dependency vulnerability scanner)
safety check

# Semgrep (pattern-based security scanning)
semgrep --config=auto apps/runtime/citadel/
```

## Incident Response

### Severity Levels

| Level | Criteria | Response Time |
|-------|----------|--------------|
| **Critical** | RCE, auth bypass, data breach | 4 hours |
| **High** | SSRF, injection, privilege escalation | 24 hours |
| **Medium** | Information disclosure, DoS | 7 days |
| **Low** | Best practice gaps, hardening | Next release |

### Response Process

1. **Acknowledge** — Confirm receipt to reporter within 48 hours
2. **Assess** — Reproduce and assign severity
3. **Fix** — Develop patch in private branch
4. **Validate** — Security tests + regression tests
5. **Notify** — If external impact, publish security advisory
6. **Release** — Patch release with CVE if applicable

## Compliance

- **GDPR:** Audit log retention configurable (`audit_retention_days`)
- **SOC 2:** Structured logging, immutable audit trail, access controls
- **FedRAMP-ready:** Kill switches, policy enforcement, tenant isolation

## Contact

For security questions or to report issues:

- Email: security@citadelsdk.com
- Telegram: @Anthonycass
- Discord: [discord.gg/clawd](https://discord.gg/clawd) (private security channel)
