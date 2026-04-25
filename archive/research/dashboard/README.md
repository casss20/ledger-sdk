# Citadel Dashboard

Modern React dashboard for Citadel SDK - AI governance for agent builders.

## Tech Stack

| Tool | Purpose |
|------|---------|
| **Vite** | Build tool (fast HMR) |
| **React 18** | UI library |
| **TypeScript** | Type safety |
| **Tailwind CSS** | Styling |
| **TanStack Query** | Data fetching + caching |
| **Recharts** | Charts (ready for compliance viz) |
| **Radix UI** | Accessible primitives |
| **Lucide** | Icons |

## Quick Start

```bash
# Install dependencies
npm install

# Start dev server (proxies /CITADEL to localhost:8000)
npm run dev

# Build for production
npm run build

# Preview production build
npm run preview
```

## Features

- Real-time stats grid (auto-refreshes every 2s)
- Pending approvals queue with approve/deny
- Kill switch management (kill/revive features)
- Audit log table with risk badges
- Dark mode UI (enterprise aesthetic)
- Type-safe API hooks

## Environment Variables

```bash
# .env.local
VITE_API_URL=http://localhost:8000/CITADEL
```

## API Proxy

Vite dev server proxies `/CITADEL` to your backend:

```typescript
// vite.config.ts
proxy: {
  "/CITADEL": {
    target: "http://localhost:8000",
    changeOrigin: true,
  },
}
```

## Project Structure

```text
src/
|- components/
|  |- ui/          # Primitive components
|  |- stats-grid.tsx
|  |- approval-queue.tsx
|  |- kill-switches.tsx
|  `- audit-log.tsx
|- lib/
|  |- utils.ts     # cn() helper
|  |- api.ts       # API config + queryClient
|  `- hooks.ts     # TanStack Query hooks
|- App.tsx         # Main dashboard layout
`- main.tsx        # Entry point
```

## License

MIT - Part of [citadel-sdk](https://github.com/casss20/citadel-sdk)
