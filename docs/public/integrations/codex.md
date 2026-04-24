# Citadel × Codex (OpenAI) Integration

Govern OpenAI Codex code generation with security review, policy enforcement, and audit trails.

## Installation

```bash
pip install citadel-sdk openai
```

## Quick Start

```python
import citadel
from citadel.integrations.codex import GovernedCodex

# 1. Create governed Codex instance
codex = GovernedCodex(
    citadel_client=citadel.CitadelClient(),
    name="code-generator",
    description="Generates code with safety review",
)

# 2. Generate code with automatic governance
result = await codex.generate(
    prompt="Write a function to validate email addresses",
    language="python",
    actor_id="developer-1",
)

# 3. Review result
if result["status"] == "executed":
    print(result["code"])
    print(f"Security score: {result['security_score']}")
elif result["status"] == "blocked":
    print(f"Blocked: {result['reason']}")
elif result["status"] == "pending_approval":
    print(f"Awaiting approval: {result['approval_id']}")
```

## GovernedCodex

Wraps Codex code generation with multi-layer security.

```python
from citadel.integrations.codex import GovernedCodex

codex = GovernedCodex(
    citadel_client=client,
    name="my-codex",                 # Unique identifier
    description="What it does",      # Human-readable
    language="python",               # Default language
    max_tokens=2000,                 # Generation limit
    security_review=True,            # Enable security scanning
    metadata={                       # Policy context
        "team": "backend",
        "repo": "api-service",
    },
)
```

### Methods

| Method | Description |
|--------|-------------|
| `generate(prompt, language, actor_id)` | Generate code with governance |
| `review_code(code, language)` | Security review only |
| `execute_code(code, context)` | Execute with sandbox controls |
| `get_security_rules()` | List active security policies |

## Security Review

Automatic security scanning on all generated code:

```python
# Security checks run automatically on generate()
result = await codex.generate(
    prompt="Write a SQL query function",
    language="python",
)

# Access security report
report = result["security_report"]
print(f"Score: {report['score']}/100")
print(f"Issues: {report['issues']}")
# Issues include: SQL injection, unsafe eval, hardcoded secrets, etc.
```

### Security Rules

Default rules detect:

| Pattern | Severity | Description |
|---------|----------|-------------|
| `eval(` / `exec(` | CRITICAL | Arbitrary code execution |
| `subprocess.call` | HIGH | Shell injection risk |
| `os.system` | HIGH | Command injection |
| SQL string concat | HIGH | SQL injection |
| Hardcoded secrets | CRITICAL | API keys in code |
| `pickle.loads` | HIGH | Deserialization attacks |
| `__import__` | MEDIUM | Dynamic imports |
| `requests` without timeout | LOW | DoS potential |

## Code Execution Controls

Execute generated code in a governed sandbox:

```python
result = await codex.execute_code(
    code=generated_code,
    context={
        "allowed_modules": ["json", "re", "datetime"],
        "timeout": 5,
        "max_memory": "128MB",
    },
    actor_id="developer-1",
)
```

**Execution policies:**
- Blocked modules: `os`, `subprocess`, `socket`, `ctypes`
- Network access: Disabled by default
- File system: Read-only, restricted paths
- CPU/memory limits: Enforced

## Approval Workflows

Force human approval for sensitive code:

```python
# All code changes require approval
codex = GovernedCodex(
    citadel_client=client,
    name="production-codex",
    requires_approval=True,  # Global approval gate
)

# Or per-generation override
result = await codex.generate(
    prompt="Update payment processing",
    requires_approval=True,  # This specific generation
)
```

## CodexGovernanceServer

FastAPI server for external governance:

```python
from fastapi import FastAPI
from citadel.integrations.codex import CodexGovernanceServer

app = FastAPI()
governance = CodexGovernanceServer(citadel_client=client)
app.include_router(governance.router, prefix="/codex")
```

**Endpoints:**

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/codex/generate` | POST | Generate code with governance |
| `/codex/review` | POST | Security review code |
| `/codex/execute` | POST | Execute with sandbox |
| `/codex/security-rules` | GET | Active security rules |
| `/codex/compliance` | GET | Audit report |

## Example: CI/CD Integration

```python
# In your CI pipeline
async def validate_code_changes(diff):
    codex = GovernedCodex(
        citadel_client=client,
        name="ci-validator",
    )
    
    # Check if any generated code in diff
    for file in diff:
        if file.is_generated:
            result = await codex.review_code(
                code=file.content,
                language=file.language,
            )
            
            if result["security_score"] < 80:
                raise SecurityError(
                    f"Security score {result['security_score']} below threshold"
                )
            
            if result["requires_approval"]:
                await flag_for_review(file, result["approval_id"])
```

## Example: Safe Code Generation

```python
async def generate_api_endpoint(spec):
    """Generate a FastAPI endpoint with full governance."""
    codex = GovernedCodex(
        citadel_client=client,
        name="api-generator",
        language="python",
        security_review=True,
    )
    
    prompt = f"""
    Write a FastAPI endpoint that:
    - Path: {spec['path']}
    - Method: {spec['method']}
    - Validates input with Pydantic
    - Uses parameterized queries (no SQL injection)
    - Returns proper HTTP status codes
    """
    
    result = await codex.generate(
        prompt=prompt,
        actor_id="backend-team",
    )
    
    if result["status"] != "executed":
        raise GenerationError(result["reason"])
    
    # Double-check security
    report = result["security_report"]
    if report["score"] < 90:
        await request_security_review(result["code"])
    
    return result["code"]
```

## Compliance & Audit

All code generation is logged:
- Prompt (hashed if sensitive)
- Generated code (stored with hash)
- Security report
- Policy decision
- Actor identity
- Timestamp and audit chain

## Error Handling

```python
from citadel.core.sdk import ActionBlocked, ApprovalRequired

try:
    result = await codex.generate(...)
except ActionBlocked as e:
    # Policy blocked — maybe prompt was malicious
    logger.warning(f"Blocked: {e.reason}")
except ApprovalRequired as e:
    # Human review needed
    await notify_security_team(e.approval_id)
except SecurityError as e:
    # Code failed security review
    await reject_and_log(e.details)
```

## Configuration

Environment variables:

```bash
# Citadel
CITADEL_URL=http://localhost:8000
CITADEL_API_KEY=your-key

# OpenAI
OPENAI_API_KEY=your-openai-key
OPENAI_ORG_ID=your-org
```

## See Also

- [OpenAI Codex Documentation](https://platform.openai.com/docs/guides/codex)
- [Security Best Practices](../guides/security-best-practices.md)
- [Claude Code Integration](claude-code.md)
