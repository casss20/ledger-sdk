# 🛡️ Citadel Demo

Self-contained demo of the governance system. No database required.

## Quick Start

```bash
cd /path/to/ledger-sdk
python3 demo/citadel_demo.py
```

## What It Shows

| Demo | Scenario | Result |
|------|----------|--------|
| 1 | AI agent queries database | ✅ Allowed |
| 2 | Agent tries production delete | ❌ Blocked by policy |
| 3 | Kill switch activated | 🛑 Everything halted |
| 4 | Staging delete needs approval | ⏳ Pending human review |
| 5 | 3 agents with different roles | 📊 2 allowed, 1 blocked |
| 6 | Audit chain verification | 🔗 Cryptographic hashes valid |

## Architecture

```
┌─────────────┐     ┌─────────────────┐     ┌──────────────┐
│  AI Agent   │────▶│ Governance Engine │────▶│   Decision   │
│  (K2.6)     │     │   (Policy check)  │     │ (Allow/Block)│
└─────────────┘     └─────────────────┘     └──────────────┘
                            │
                            ▼
                    ┌─────────────────┐
                    │  Audit Logger   │
                    │ (Hash chain)    │
                    └─────────────────┘
```

## Exit Codes

- `0` — All demos passed
- `1` — One or more demos failed
