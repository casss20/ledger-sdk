# CI/CD Setup Guide

## Required Secrets

Go to: **GitHub Settings > Secrets and variables > Actions**

### 1. Fly.io (API Deployment)

```
Name:  FLY_API_TOKEN
Value: <your-fly-token>
```

Get your token:
```bash
flyctl auth token
```

### 2. Vercel (Frontend Deployment)

```
Name:  VERCEL_TOKEN
Value: <your-vercel-token>
```

Get your token:
```bash
vercel login
vercel tokens create
```

Optional (for linking projects):
```
VERCEL_ORG_ID=<your-org-id>
VERCEL_PROJECT_ID=<dashboard-project-id>
VERCEL_PROJECT_ID_LANDING=<landing-project-id>
```

Get these from `.vercel/project.json` after running `vercel link`.

## What the CI/CD does

1. **Tests** — Runs backend tests with Postgres + frontend builds
2. **Deploy API** — Pushes to Fly.io on master/main pushes
3. **Deploy Dashboard** — Pushes to Vercel
4. **Deploy Landing** — Pushes to Vercel
5. **Deploy Docs** — Pushes to Vercel

## Manual Trigger

You can also trigger manually from GitHub:
Actions tab → CI / CD → Run workflow
