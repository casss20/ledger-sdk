# Security Scanning Guide

**Document ID:** SEC-SCAN-001  
**Version:** 1.0  
**Date:** 2026-04-26  

---

## Overview

This guide sets up automated security scanning for the Citadel codebase. We cover:

- **SAST** (Static Application Security Testing) — code-level vulnerabilities
- **DAST** (Dynamic Application Security Testing) — runtime vulnerability scanning
- **Dependency scanning** — known CVEs in third-party packages
- **Container scanning** — Docker image vulnerabilities
- **Secret detection** — prevent credential leaks

---

## 1. SAST — Code Analysis

### Tool: Bandit + Semgrep

**Bandit** (Python-specific):
```bash
# Install
pip install bandit

# Run on the entire runtime
bandit -r apps/runtime/citadel/ -f json -o bandit-report.json

# Or inline
bandit -r apps/runtime/citadel/ -ll
```

**Semgrep** (multi-language, OWASP rules):
```bash
# Install
pip install semgrep

# Run with OWASP Top 10 ruleset
semgrep --config="p/owasp-top-ten" apps/runtime/citadel/

# Run with custom Citadel rules
semgrep --config=.semgrep/ apps/runtime/citadel/
```

**GitHub Actions integration** (`.github/workflows/sast.yml`):
```yaml
name: SAST
on: [push, pull_request]
jobs:
  bandit:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: '3.12' }
      - run: pip install bandit
      - run: bandit -r apps/runtime/citadel/ -ll -ii
  semgrep:
    runs-on: ubuntu-latest
    container:
      image: returntocorp/semgrep
    steps:
      - uses: actions/checkout@v4
      - run: semgrep --config="p/owasp-top-ten" --error apps/runtime/citadel/
```

---

## 2. DAST — Runtime Scanning

### Tool: OWASP ZAP

**Local scan against running API:**
```bash
# Start the API first
uvicorn citadel.api:app --host 127.0.0.1 --port 8000 &

# Run ZAP baseline scan
docker run -t ghcr.io/zaproxy/zaproxy:stable zap-baseline.py \
  -t http://host.docker.internal:8000 \
  -r zap-report.html

# Full scan (takes longer, more thorough)
docker run -t ghcr.io/zaproxy/zaproxy:stable zap-full-scan.py \
  -t http://host.docker.internal:8000 \
  -r zap-full-report.html
```

**CI/CD integration** (`.github/workflows/dast.yml`):
```yaml
name: DAST
on:
  schedule:
    - cron: '0 3 * * 1'  # Weekly Monday 3am
jobs:
  zap:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: docker compose -f docker-compose.yml up -d api
      - run: sleep 30  # Wait for API to start
      - uses: zaproxy/action-baseline@v0.12.0
        with:
          target: 'http://localhost:8000'
          rules_file_name: '.zap/rules.tsv'
```

---

## 3. Dependency Scanning

### Tool: pip-audit + Safety

**pip-audit** (PyPA official):
```bash
pip install pip-audit
pip-audit --requirement=requirements.txt --format=json --output=pip-audit.json
```

**Safety** (commercial, free tier):
```bash
pip install safety
safety check --json --output=safety-report.json
```

**GitHub Actions** (`.github/workflows/deps.yml`):
```yaml
name: Dependency Audit
on: [push, pull_request]
jobs:
  pip-audit:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: pypa/gh-action-pip-audit@v1.0.8
        with:
          inputs: requirements.txt requirements-dev.txt
          require-hashes: true
  safety:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: pyupio/safety-action@v1
        with:
          api-key: ${{ secrets.SAFETY_API_KEY }}
```

**Dependabot** (`.github/dependabot.yml`):
```yaml
version: 2
updates:
  - package-ecosystem: pip
    directory: /
    schedule:
      interval: weekly
    open-pull-requests-limit: 5
    labels: [security, dependencies]
```

---

## 4. Container Scanning

### Tool: Trivy

**Scan Docker image:**
```bash
# Build image
docker build -t citadel-api:latest .

# Scan with Trivy
docker run --rm -v /var/run/docker.sock:/var/run/docker.sock \
  aquasec/trivy image citadel-api:latest --severity HIGH,CRITICAL

# Or install locally
wget https://github.com/aquasecurity/trivy/releases/download/v0.50.0/trivy_0.50.0_Linux-64bit.deb
dpkg -i trivy_0.50.0_Linux-64bit.deb
trivy image citadel-api:latest --severity HIGH,CRITICAL --exit-code 1
```

**GitHub Actions**:
```yaml
- uses: aquasecurity/trivy-action@master
  with:
    image-ref: 'citadel-api:latest'
    format: 'sarif'
    output: 'trivy-results.sarif'
```

---

## 5. Secret Detection

### Tool: GitLeaks + TruffleHog

**GitLeaks** (pre-commit hook):
```bash
# Install
brew install gitleaks  # macOS
# or download from releases

# Run scan
gitleaks detect --source . --verbose --report-format json --report-path gitleaks-report.json

# Pre-commit hook
pre-commit install
cat > .pre-commit-config.yaml << 'EOF'
repos:
  - repo: https://github.com/gitleaks/gitleaks
    rev: v8.18.2
    hooks:
      - id: gitleaks
EOF
```

**TruffleHog** (deep scan):
```bash
docker run --rm -it -v "$PWD:/pwd" trufflesecurity/trufflehog:latest \
  filesystem /pwd --json --only-verified
```

**GitHub Actions**:
```yaml
- uses: gitleaks/gitleaks-action@v2
  env:
    GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
    GITLEAKS_LICENSE: ${{ secrets.GITLEAKS_LICENSE }}
```

---

## 6. Security Dashboard

Consolidate all scans into a single view:

| Tool | Frequency | Critical Threshold |
|------|-----------|-------------------|
| Bandit | Every PR | 0 HIGH issues |
| Semgrep | Every PR | 0 OWASP-Critical |
| ZAP | Weekly | 0 HIGH findings |
| pip-audit | Every PR | 0 known CVEs |
| Trivy | Every build | 0 CRITICAL vulns |
| GitLeaks | Every commit | 0 secrets leaked |

---

## 7. Makefile Targets

Add to `Makefile`:
```makefile
.PHONY: security-scan security-report

security-scan:  ## Run all security scanners
	@echo "Running Bandit..."
	@bandit -r apps/runtime/citadel/ -ll -ii -q
	@echo "Running Semgrep..."
	@semgrep --config="p/owasp-top-ten" --error --quiet apps/runtime/citadel/
	@echo "Running pip-audit..."
	@pip-audit --requirement=requirements.txt
	@echo "Running GitLeaks..."
	@gitleaks detect --source . --no-git --quiet
	@echo "All security checks passed ✅"

security-report:  ## Generate full security report
	@mkdir -p reports/security
	@bandit -r apps/runtime/citadel/ -f json -o reports/security/bandit.json
	@semgrep --config="p/owasp-top-ten" --json -o reports/security/semgrep.json apps/runtime/citadel/
	@pip-audit --requirement=requirements.txt --format=json --output=reports/security/pip-audit.json
	@echo "Reports written to reports/security/"
```

---

## 8. Next Steps

1. Add `.github/workflows/security.yml` to run all scans on every PR
2. Configure GitHub Advanced Security (secret scanning, dependency review)
3. Set up SonarCloud for continuous code quality + security tracking
4. Add security scanning to CI/CD pipeline before production deploys

---

**Document Owner:** Security Engineering  
**Review Cycle:** Quarterly
