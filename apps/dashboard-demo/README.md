# Dashboard Demo

A standalone demo version of the Citadel Dashboard for sales presentations,
conference booths, and onboarding walkthroughs.

## What is different from the real dashboard?

| Feature | Real Dashboard | Demo Dashboard |
|---------|---------------|----------------|
| Backend API | Live HTTP to `api.citadelsdk.com` | In-memory mock data |
| Authentication | Username + password login | Auto-login (no password) |
| Data | Your real tenant data | 4 sample agents, 3 pending approvals |
| Port (dev) | 5173 | 5174 |
| Branding | "CITADEL" | "CITADEL — Demo Environment" |

## Quick Start

```bash
cd apps/dashboard-demo
npm install
npm run dev        # http://localhost:5174
```

## Demo Data

The mock API returns:

- **4 agents**: payment-agent-01 (highly trusted), data-processor-02 (trusted),
  email-agent-03 (standard), experimental-04 (revoked)
- **3 pending approvals**: database access, email blast, report generation
- **Stats**: 12,847 total actions, 3 pending approvals, 142 recent events

## Build

```bash
npm run build      # Output: dist/
npm run preview    # Serve built output on :4174
```

## Files changed from real dashboard

- `src/api/client.ts` — replaced real fetch with mock data
- `src/app/router.tsx` — removed auth guard (no login required)
- `src/pages/Login.tsx` — auto-logs in immediately
- `src/layout/MainLayout.tsx` — added "Demo Environment" badge
- `vite.config.ts` — port 5174
- `package.json` — name `dashboard-demo`, ports updated
- `index.html` — title updated
