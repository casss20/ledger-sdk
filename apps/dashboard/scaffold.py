import os

files = {
    "src/main.tsx": """import React from "react";
import ReactDOM from "react-dom/client";
import { BrowserRouter } from "react-router-dom";
import { App } from "./app/App";
import "./styles/index.css";

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <BrowserRouter>
      <App />
    </BrowserRouter>
  </React.StrictMode>
);
""",
    "src/app/App.tsx": """import { AppRouter } from "./router";
import { AppProviders } from "./providers";

export function App() {
  return (
    <AppProviders>
      <AppRouter />
    </AppProviders>
  );
}
""",
    "src/app/providers.tsx": """import type { ReactNode } from "react";

type Props = {
  children: ReactNode;
};

export function AppProviders({ children }: Props) {
  return <>{children}</>;
}
""",
    "src/app/router.tsx": """import { Navigate, Route, Routes } from "react-router-dom";
import { DashboardLayout } from "../layout/DashboardLayout";
import { OverviewPage } from "../pages/Overview";
import { ApprovalsPage } from "../pages/Approvals";
import { ActivityPage } from "../pages/Activity";
import { AuditExplorerPage } from "../pages/AuditExplorer";
import { PoliciesPage } from "../pages/Policies";
import { AgentsPage } from "../pages/Agents";
import { IncidentsPage } from "../pages/Incidents";
import { EmergencyPage } from "../pages/Emergency";
import { SettingsPage } from "../pages/Settings";

export function AppRouter() {
  return (
    <Routes>
      <Route element={<DashboardLayout />}>
        <Route path="/" element={<Navigate to="/overview" replace />} />
        <Route path="/overview" element={<OverviewPage />} />
        <Route path="/approvals" element={<ApprovalsPage />} />
        <Route path="/activity" element={<ActivityPage />} />
        <Route path="/audit" element={<AuditExplorerPage />} />
        <Route path="/policies" element={<PoliciesPage />} />
        <Route path="/agents" element={<AgentsPage />} />
        <Route path="/incidents" element={<IncidentsPage />} />
        <Route path="/emergency" element={<EmergencyPage />} />
        <Route path="/settings" element={<SettingsPage />} />
      </Route>
    </Routes>
  );
}
""",
    "src/layout/DashboardLayout.tsx": """import { Outlet } from "react-router-dom";
import { Sidebar } from "./Sidebar";
import { Topbar } from "./Topbar";

export function DashboardLayout() {
  return (
    <div className="dashboard-shell">
      <Sidebar />
      <div className="main-shell">
        <Topbar />
        <main className="main-content">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
""",
    "src/layout/Sidebar.tsx": """import { NavLink } from "react-router-dom";
import { navItems } from "../data/nav";

export function Sidebar() {
  return (
    <aside className="sidebar">
      <div className="sidebar__brand">
        <div className="sidebar__logo">L</div>
        <div>
          <strong>Ledger</strong>
          <p>Governance Console</p>
        </div>
      </div>

      <nav className="sidebar__nav" aria-label="Primary navigation">
        {navItems.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            className={({ isActive }) =>
              `sidebar__link ${isActive ? "is-active" : ""}`
            }
          >
            <span className="sidebar__icon">{item.icon}</span>
            <span>{item.label}</span>
          </NavLink>
        ))}
      </nav>

      <div className="sidebar__footer">
        <div className="workspace-chip">Forge / Production</div>
        <button className="btn btn-secondary btn-block">Toggle theme</button>
      </div>
    </aside>
  );
}
""",
    "src/layout/Topbar.tsx": """export function Topbar() {
  return (
    <header className="topbar">
      <div>
        <h1>Ledger Governance</h1>
        <p>Runtime controls and audit visibility</p>
      </div>

      <div className="topbar__actions">
        <input
          className="search-input"
          placeholder="Search trace, agent, policy..."
        />
        <button className="btn btn-secondary">Last 24 hours</button>
        <button className="btn btn-primary">Export</button>
      </div>
    </header>
  );
}
""",
    "src/layout/PageShell.tsx": """import type { ReactNode } from "react";

type Props = {
  title: string;
  description?: string;
  actions?: ReactNode;
  children: ReactNode;
};

export function PageShell({ title, description, actions, children }: Props) {
  return (
    <section className="page-shell">
      <div className="page-shell__header">
        <div>
          <h2>{title}</h2>
          {description ? <p>{description}</p> : null}
        </div>
        {actions ? <div>{actions}</div> : null}
      </div>
      <div className="page-shell__body">{children}</div>
    </section>
  );
}
""",
    "src/components/ui/Button.tsx": """import type { ButtonHTMLAttributes } from "react";

type Variant = "primary" | "secondary" | "danger";

type Props = ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: Variant;
};

export function Button({ variant = "primary", className = "", ...props }: Props) {
  return <button className={`btn btn-${variant} ${className}`.trim()} {...props} />;
}
""",
    "src/components/ui/Card.tsx": """import type { ReactNode } from "react";

type Props = {
  title?: string;
  children: ReactNode;
};

export function Card({ title, children }: Props) {
  return (
    <section className="card">
      {title ? <div className="card__title">{title}</div> : null}
      <div className="card__body">{children}</div>
    </section>
  );
}
""",
    "src/components/dashboard/KpiCard.tsx": """type Props = {
  label: string;
  value: string;
  delta?: string;
  tone?: "neutral" | "success" | "warning" | "danger";
};

export function KpiCard({ label, value, delta, tone = "neutral" }: Props) {
  return (
    <section className={`card kpi-card tone-${tone}`}>
      <div className="kpi-card__label">{label}</div>
      <div className="kpi-card__value metric-value">{value}</div>
      {delta ? <div className="kpi-card__delta">{delta}</div> : null}
    </section>
  );
}
""",
    "src/components/dashboard/StatusPill.tsx": """type Props = {
  status: "approved" | "pending" | "blocked";
};

export function StatusPill({ status }: Props) {
  const map = {
    approved: "status-badge status-approved",
    pending: "status-badge status-pending",
    blocked: "status-badge status-blocked",
  };

  return <span className={map[status]}>{status}</span>;
}
""",
    "src/components/approvals/ApprovalFilters.tsx": """export function ApprovalFilters() {
  return (
    <div className="filter-row card">
      <div className="filter-row__group">
        <input className="search-input" placeholder="Search requests" />
        <select className="select-input">
          <option>All risks</option>
          <option>Critical</option>
          <option>High</option>
          <option>Medium</option>
          <option>Low</option>
        </select>
        <select className="select-input">
          <option>All statuses</option>
          <option>Pending</option>
          <option>Approved</option>
          <option>Blocked</option>
        </select>
      </div>
      <button className="btn btn-secondary">Clear filters</button>
    </div>
  );
}
""",
    "src/components/approvals/ApprovalTable.tsx": """import { approvals } from "../../data/mock-approvals";
import { StatusPill } from "../dashboard/StatusPill";

export function ApprovalTable() {
  return (
    <div className="table-shell">
      <table className="data-table">
        <thead>
          <tr>
            <th>Status</th>
            <th>Risk</th>
            <th>Agent</th>
            <th>Requested action</th>
            <th>Target</th>
            <th>Policy source</th>
            <th>Requested at</th>
            <th>Waiting</th>
            <th>Decision</th>
          </tr>
        </thead>
        <tbody>
          {approvals.map((row) => (
            <tr key={row.id}>
              <td><StatusPill status={row.status} /></td>
              <td>{row.risk}</td>
              <td>{row.agent}</td>
              <td>{row.action}</td>
              <td>{row.target}</td>
              <td>{row.policy}</td>
              <td className="data-time">{row.requestedAt}</td>
              <td className="data-num">{row.waiting}</td>
              <td>{row.decision}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
""",
    "src/components/activity/ActivityFeed.tsx": """import { activityEvents } from "../../data/mock-activity";
import { Card } from "../ui/Card";

export function ActivityFeed() {
  return (
    <div className="stack-lg">
      {activityEvents.map((event) => (
        <Card key={event.id} title={event.title}>
          <div className="event-row">
            <p>{event.description}</p>
            <span className="data-time">{event.time}</span>
          </div>
        </Card>
      ))}
    </div>
  );
}
""",
    "src/components/audit/AuditFilters.tsx": """export function AuditFilters() {
  return (
    <div className="filter-row card">
      <div className="filter-row__group">
        <input className="search-input" placeholder="Search trace ID, actor, target" />
        <select className="select-input">
          <option>All environments</option>
          <option>Production</option>
          <option>Staging</option>
        </select>
        <select className="select-input">
          <option>All outcomes</option>
          <option>Allowed</option>
          <option>Blocked</option>
          <option>Escalated</option>
        </select>
      </div>
      <button className="btn btn-secondary">Export JSON</button>
    </div>
  );
}
""",
    "src/components/audit/AuditTable.tsx": """import { auditEvents } from "../../data/mock-audit";

export function AuditTable() {
  return (
    <div className="table-shell">
      <table className="data-table">
        <thead>
          <tr>
            <th>Time</th>
            <th>Actor</th>
            <th>Action</th>
            <th>Target</th>
            <th>Outcome</th>
            <th>Trace ID</th>
          </tr>
        </thead>
        <tbody>
          {auditEvents.map((row) => (
            <tr key={row.id}>
              <td className="data-time">{row.time}</td>
              <td>{row.actor}</td>
              <td>{row.action}</td>
              <td>{row.target}</td>
              <td>{row.outcome}</td>
              <td className="data-num">{row.traceId}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
""",
    "src/components/emergency/KillSwitchPanel.tsx": """export function KillSwitchPanel() {
  return (
    <section className="card emergency-panel">
      <div className="emergency-panel__eyebrow">Emergency controls</div>
      <h3>Revoke all active agent permissions</h3>
      <p>
        Immediately suspend execution access for connected agents across the selected scope.
      </p>

      <div className="stack-md">
        <label className="field">
          <span>Scope</span>
          <select className="select-input">
            <option>All agents / production</option>
            <option>Selected agents only</option>
            <option>GitHub integration only</option>
            <option>Payments only</option>
          </select>
        </label>

        <label className="field">
          <span>Type REVOKE ALL</span>
          <input className="text-input" placeholder="REVOKE ALL" />
        </label>
      </div>

      <div className="emergency-panel__actions">
        <button className="btn btn-danger">Execute kill switch</button>
      </div>
    </section>
  );
}
""",
    "src/pages/Overview.tsx": """import { KpiCard } from "../components/dashboard/KpiCard";
import { Card } from "../components/ui/Card";
import { kpis } from "../data/kpis";
import { PageShell } from "../layout/PageShell";

export function OverviewPage() {
  return (
    <PageShell
      title="Overview"
      description="Current posture, workload, and recent risk."
    >
      <div className="kpi-grid">
        {kpis.map((item) => (
          <KpiCard key={item.label} {...item} />
        ))}
      </div>

      <div className="overview-grid">
        <Card title="Pending reviews">Queue summary and highest-risk pending items.</Card>
        <Card title="Recent critical activity">Chronological feed of urgent events.</Card>
        <Card title="Kill switch status">Current emergency state and scope.</Card>
      </div>
    </PageShell>
  );
}
""",
    "src/pages/Approvals.tsx": """import { ApprovalFilters } from "../components/approvals/ApprovalFilters";
import { ApprovalTable } from "../components/approvals/ApprovalTable";
import { PageShell } from "../layout/PageShell";

export function ApprovalsPage() {
  return (
    <PageShell
      title="Approval Queue"
      description="Review and decide high-risk agent actions."
      actions={<button className="btn btn-secondary">Export CSV</button>}
    >
      <div className="stack-lg">
        <ApprovalFilters />
        <ApprovalTable />
      </div>
    </PageShell>
  );
}
""",
    "src/pages/Activity.tsx": """import { ActivityFeed } from "../components/activity/ActivityFeed";
import { PageShell } from "../layout/PageShell";

export function ActivityPage() {
  return (
    <PageShell
      title="Activity Stream"
      description="Live operational events across agents and policies."
    >
      <ActivityFeed />
    </PageShell>
  );
}
""",
    "src/pages/AuditExplorer.tsx": """import { AuditFilters } from "../components/audit/AuditFilters";
import { AuditTable } from "../components/audit/AuditTable";
import { PageShell } from "../layout/PageShell";

export function AuditExplorerPage() {
  return (
    <PageShell
      title="Audit Explorer"
      description="Search, filter, and export traceable governance events."
    >
      <div className="stack-lg">
        <AuditFilters />
        <AuditTable />
      </div>
    </PageShell>
  );
}
""",
    "src/pages/Policies.tsx": """import { Card } from "../components/ui/Card";
import { PageShell } from "../layout/PageShell";

export function PoliciesPage() {
  return (
    <PageShell title="Policies" description="Policy packs, thresholds, and change history.">
      <Card title="Policy registry">Policy management surface goes here.</Card>
    </PageShell>
  );
}
""",
    "src/pages/Agents.tsx": """import { Card } from "../components/ui/Card";
import { PageShell } from "../layout/PageShell";

export function AgentsPage() {
  return (
    <PageShell title="Agents" description="Registry, scopes, and recent behavior.">
      <Card title="Agent registry">Agent inventory surface goes here.</Card>
    </PageShell>
  );
}
""",
    "src/pages/Incidents.tsx": """import { Card } from "../components/ui/Card";
import { PageShell } from "../layout/PageShell";

export function IncidentsPage() {
  return (
    <PageShell title="Incidents" description="Escalations, anomalies, and response status.">
      <Card title="Incident timeline">Incident response surface goes here.</Card>
    </PageShell>
  );
}
""",
    "src/pages/Emergency.tsx": """import { KillSwitchPanel } from "../components/emergency/KillSwitchPanel";
import { PageShell } from "../layout/PageShell";

export function EmergencyPage() {
  return (
    <PageShell
      title="Emergency"
      description="Restrict or suspend risky execution paths."
    >
      <KillSwitchPanel />
    </PageShell>
  );
}
""",
    "src/pages/Settings.tsx": """import { Card } from "../components/ui/Card";
import { PageShell } from "../layout/PageShell";

export function SettingsPage() {
  return (
    <PageShell title="Settings" description="Access, integrations, notifications, and retention.">
      <Card title="Workspace settings">Settings surface goes here.</Card>
    </PageShell>
  );
}
""",
    "src/data/nav.ts": """export const navItems = [
  { label: "Overview", to: "/overview", icon: "◫" },
  { label: "Approvals", to: "/approvals", icon: "◎" },
  { label: "Activity", to: "/activity", icon: "◌" },
  { label: "Audit Explorer", to: "/audit", icon: "▣" },
  { label: "Policies", to: "/policies", icon: "◇" },
  { label: "Agents", to: "/agents", icon: "△" },
  { label: "Incidents", to: "/incidents", icon: "!" },
  { label: "Emergency", to: "/emergency", icon: "⛶" },
  { label: "Settings", to: "/settings", icon: "⋯" },
];
""",
    "src/data/kpis.ts": """export const kpis = [
  { label: "Pending reviews", value: "18", delta: "+3 today", tone: "warning" },
  { label: "Blocked actions", value: "42", delta: "+8%", tone: "danger" },
  { label: "Approved actions", value: "1,284", delta: "+4.2%", tone: "success" },
  { label: "Active agents", value: "27", delta: "2 restricted", tone: "neutral" },
  { label: "Critical incidents", value: "3", delta: "Needs review", tone: "danger" },
] as const;
""",
    "src/features/approvals/types.ts": """export type ApprovalItem = {
  id: string;
  status: "approved" | "pending" | "blocked";
  risk: "Low" | "Medium" | "High" | "Critical";
  agent: string;
  action: string;
  target: string;
  policy: string;
  requestedAt: string;
  waiting: string;
  decision: string;
  traceId?: string;
  owner?: string;
};
""",
    "src/data/mock-approvals.ts": """import type { ApprovalItem } from "../features/approvals/types";

export const approvals: ApprovalItem[] = [
  {
    id: "apr_001",
    status: "pending",
    risk: "Critical",
    agent: "Payments-Agent-01",
    action: "Issue refund above threshold",
    target: "Stripe / Customer #2841",
    policy: "payments.refund.limit",
    requestedAt: "2026-04-23 01:58",
    waiting: "12m",
    decision: "Awaiting review",
  },
  {
    id: "apr_002",
    status: "blocked",
    risk: "High",
    agent: "Outreach-Agent-02",
    action: "Send unapproved outbound email",
    target: "CRM / Prospect batch",
    policy: "communications.approval.required",
    requestedAt: "2026-04-23 01:42",
    waiting: "Resolved",
    decision: "Blocked by policy",
  },
  {
    id: "apr_003",
    status: "approved",
    risk: "Medium",
    agent: "Repo-Agent-07",
    action: "Merge docs update",
    target: "GitHub / governance-docs",
    policy: "repo.write.review",
    requestedAt: "2026-04-23 01:30",
    waiting: "4m",
    decision: "Approved by operator",
  },
];
""",
    "src/data/mock-activity.ts": """export const activityEvents = [
  {
    id: "evt_1",
    title: "Policy blocked payment workflow",
    description: "payments.refund.limit stopped a refund above the approved threshold.",
    time: "2m ago",
  },
  {
    id: "evt_2",
    title: "Human review requested",
    description: "Repo-Agent-07 requested approval for a protected branch write.",
    time: "7m ago",
  },
  {
    id: "evt_3",
    title: "Kill switch health check passed",
    description: "Emergency control availability verified for production workspace.",
    time: "15m ago",
  },
];
""",
    "src/data/mock-audit.ts": """export const auditEvents = [
  {
    id: "aud_1",
    time: "2026-04-23 01:58:04",
    actor: "Payments-Agent-01",
    action: "request.refund",
    target: "stripe.customer.2841",
    outcome: "Escalated",
    traceId: "trc_9ad4f2",
  },
  {
    id: "aud_2",
    time: "2026-04-23 01:42:33",
    actor: "Outreach-Agent-02",
    action: "send.email",
    target: "crm.batch.18",
    outcome: "Blocked",
    traceId: "trc_8bc113",
  },
  {
    id: "aud_3",
    time: "2026-04-23 01:31:18",
    actor: "Repo-Agent-07",
    action: "github.merge",
    target: "governance-docs.main",
    outcome: "Allowed",
    traceId: "trc_73ca21",
  },
];
""",
    "src/styles/index.css": """:root,
[data-theme="light"] {
  --font-sans: "Satoshi", -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
  --font-mono: "IBM Plex Mono", "SFMono-Regular", Consolas, monospace;

  --text-xs: 12px;
  --text-sm: 14px;
  --text-base: 16px;
  --text-lg: 20px;
  --text-xl: 28px;

  --line-height-tight: 1.2;
  --line-height-base: 1.55;

  --space-1: 4px;
  --space-2: 8px;
  --space-3: 12px;
  --space-4: 16px;
  --space-5: 20px;
  --space-6: 24px;
  --space-8: 32px;
  --space-10: 40px;
  --space-12: 48px;
  --space-16: 64px;

  --radius-sm: 8px;
  --radius-md: 12px;
  --radius-lg: 16px;
  --radius-xl: 20px;
  --radius-pill: 999px;

  --color-bg: #F6F7F9;
  --color-surface: #FFFFFF;
  --color-surface-2: #F1F3F6;
  --color-surface-3: #E9EDF2;
  --color-border: #D6DCE5;

  --color-text: #111827;
  --color-text-muted: #4B5563;
  --color-text-faint: #6B7280;
  --color-text-inverse: #F9FBFD;

  --color-primary: #1F3A5F;
  --color-primary-hover: #18314F;
  --color-primary-active: #12263E;
  --color-primary-tint: #E8EEF6;

  --color-success: #0F8A5F;
  --color-success-tint: #E7F6F0;

  --color-warning: #B7791F;
  --color-warning-tint: #FBF3E6;

  --color-danger: #B42318;
  --color-danger-tint: #FDECEA;

  --shadow-sm: 0 1px 2px rgba(16, 24, 40, 0.04);
  --shadow-md: 0 6px 18px rgba(16, 24, 40, 0.08);
  --shadow-lg: 0 18px 40px rgba(16, 24, 40, 0.12);

  --focus-ring: 0 0 0 3px rgba(31, 58, 95, 0.22);
}

[data-theme="dark"] {
  --color-bg: #0D1117;
  --color-surface: #111827;
  --color-surface-2: #161E29;
  --color-surface-3: #1D2633;
  --color-border: #2A3545;

  --color-text: #F3F6FA;
  --color-text-muted: #C4CDD8;
  --color-text-faint: #93A1B2;
  --color-text-inverse: #0D1117;

  --color-primary: #8FB3D9;
  --color-primary-hover: #A6C2E1;
  --color-primary-active: #769CC5;
  --color-primary-tint: #162434;

  --color-success: #3FB98B;
  --color-success-tint: #11281F;

  --color-warning: #E3A64A;
  --color-warning-tint: #2A2114;

  --color-danger: #E26D5A;
  --color-danger-tint: #2D1716;

  --shadow-sm: 0 1px 2px rgba(0, 0, 0, 0.25);
  --shadow-md: 0 8px 24px rgba(0, 0, 0, 0.32);
  --shadow-lg: 0 18px 40px rgba(0, 0, 0, 0.4);

  --focus-ring: 0 0 0 3px rgba(143, 179, 217, 0.28);
}

* { box-sizing: border-box; }
html, body, #root { height: 100%; margin: 0; }
body {
  font-family: var(--font-sans);
  font-size: var(--text-base);
  line-height: var(--line-height-base);
  color: var(--color-text);
  background: var(--color-bg);
  -webkit-font-smoothing: antialiased;
  text-rendering: optimizeLegibility;
}
button, input, select { font: inherit; }

.dashboard-shell {
  display: grid;
  grid-template-columns: 248px 1fr;
  height: 100dvh;
  overflow: hidden;
}

.sidebar {
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  padding: var(--space-4);
  background: var(--color-surface);
  border-right: 1px solid var(--color-border);
}

.sidebar__brand {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  margin-bottom: var(--space-6);
}

.sidebar__brand p {
  margin: 2px 0 0;
  color: var(--color-text-muted);
  font-size: var(--text-sm);
}

.sidebar__logo {
  width: 40px;
  height: 40px;
  display: grid;
  place-items: center;
  border-radius: 12px;
  background: var(--color-primary-tint);
  color: var(--color-primary);
  font-weight: 700;
}

.sidebar__nav {
  display: grid;
  gap: var(--space-2);
}

.sidebar__link {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  padding: 12px 14px;
  border-radius: var(--radius-md);
  color: var(--color-text-muted);
  text-decoration: none;
}

.sidebar__link.is-active {
  background: var(--color-primary-tint);
  color: var(--color-primary);
  font-weight: 600;
}

.sidebar__footer {
  display: grid;
  gap: var(--space-3);
}

.workspace-chip {
  padding: 10px 12px;
  border-radius: var(--radius-md);
  background: var(--color-surface-2);
  color: var(--color-text-muted);
  font-size: var(--text-sm);
}

.main-shell {
  display: grid;
  grid-template-rows: 72px 1fr;
  min-width: 0;
}

.topbar {
  position: sticky;
  top: 0;
  z-index: 10;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-4);
  padding: 0 var(--space-6);
  background: rgba(255, 255, 255, 0.78);
  backdrop-filter: blur(14px);
  border-bottom: 1px solid var(--color-border);
}

[data-theme="dark"] .topbar {
  background: rgba(17, 24, 39, 0.72);
}

.topbar h1,
.page-shell__header h2 {
  margin: 0;
  font-size: var(--text-xl);
  line-height: var(--line-height-tight);
}

.topbar p,
.page-shell__header p {
  margin: 4px 0 0;
  color: var(--color-text-muted);
  font-size: var(--text-sm);
}

.topbar__actions {
  display: flex;
  align-items: center;
  gap: var(--space-3);
}

.main-content {
  overflow-y: auto;
  padding: var(--space-8);
}

.page-shell,
.page-shell__body,
.stack-lg,
.stack-md {
  display: grid;
}

.page-shell,
.page-shell__body,
.stack-lg { gap: var(--space-6); }
.stack-md { gap: var(--space-4); }

.page-shell__header {
  display: flex;
  align-items: start;
  justify-content: space-between;
  gap: var(--space-4);
}

.card {
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-sm);
}

.card__title {
  padding: var(--space-4) var(--space-4) 0;
  font-size: var(--text-sm);
  font-weight: 600;
}

.card__body {
  padding: var(--space-4);
}

.kpi-grid {
  display: grid;
  grid-template-columns: repeat(5, minmax(0, 1fr));
  gap: var(--space-4);
}

.kpi-card__label {
  color: var(--color-text-muted);
  font-size: var(--text-sm);
}

.kpi-card__value {
  margin-top: var(--space-3);
  font-size: 32px;
  font-weight: 700;
}

.kpi-card__delta {
  margin-top: var(--space-3);
  color: var(--color-text-muted);
  font-size: var(--text-sm);
}

.overview-grid {
  display: grid;
  grid-template-columns: 1.2fr 1fr 0.9fr;
  gap: var(--space-4);
}

.filter-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-4);
  padding: var(--space-4);
}

.filter-row__group {
  display: flex;
  gap: var(--space-3);
  flex-wrap: wrap;
}

.search-input,
.text-input,
.select-input {
  min-height: 44px;
  padding: 0 14px;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  background: var(--color-surface);
  color: var(--color-text);
}

.search-input { min-width: 280px; }
.select-input { min-width: 160px; }

.btn {
  min-height: 44px;
  padding: 0 16px;
  border: 0;
  border-radius: var(--radius-md);
  cursor: pointer;
  transition: 200ms ease;
}

.btn-primary {
  background: var(--color-primary);
  color: var(--color-text-inverse);
}

.btn-secondary {
  background: var(--color-surface-2);
  color: var(--color-text);
  border: 1px solid var(--color-border);
}

.btn-danger {
  background: var(--color-danger);
  color: #fff;
}

.btn-block { width: 100%; }

.table-shell {
  overflow-x: auto;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  background: var(--color-surface);
}

.data-table {
  width: 100%;
  border-collapse: collapse;
  font-size: var(--text-sm);
}

.data-table th,
.data-table td {
  padding: 18px 16px;
  border-bottom: 1px solid var(--color-border);
  text-align: left;
  vertical-align: middle;
}

.data-table th {
  position: sticky;
  top: 0;
  background: var(--color-surface);
  color: var(--color-text-muted);
  font-size: var(--text-xs);
  text-transform: uppercase;
  letter-spacing: 0.04em;
}

.metric-value,
.data-time,
.data-num {
  font-variant-numeric: tabular-nums lining-nums;
}

.status-badge {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 6px 10px;
  border-radius: var(--radius-pill);
  font-size: var(--text-xs);
  font-weight: 600;
  text-transform: capitalize;
}

.status-approved {
  background: var(--color-success-tint);
  color: var(--color-success);
}

.status-pending {
  background: var(--color-warning-tint);
  color: var(--color-warning);
}

.status-blocked {
  background: var(--color-danger-tint);
  color: var(--color-danger);
}

.event-row {
  display: flex;
  justify-content: space-between;
  align-items: start;
  gap: var(--space-4);
}

.event-row p { margin: 0; }

.field {
  display: grid;
  gap: var(--space-2);
}

.field span,
.emergency-panel__eyebrow {
  color: var(--color-text-muted);
  font-size: var(--text-xs);
  text-transform: uppercase;
  letter-spacing: 0.04em;
}

.emergency-panel {
  max-width: 720px;
}

.emergency-panel h3 {
  margin: var(--space-2) 0 var(--space-3);
}

.emergency-panel p {
  margin: 0 0 var(--space-5);
  color: var(--color-text-muted);
}

.emergency-panel__actions {
  margin-top: var(--space-5);
}

@media (max-width: 1200px) {
  .kpi-grid,
  .overview-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 920px) {
  .dashboard-shell {
    grid-template-columns: 1fr;
  }

  .sidebar {
    display: none;
  }

  .topbar,
  .main-content {
    padding-inline: var(--space-4);
  }

  .kpi-grid,
  .overview-grid,
  .filter-row {
    grid-template-columns: 1fr;
  }

  .topbar,
  .filter-row,
  .page-shell__header,
  .topbar__actions,
  .filter-row__group,
  .event-row {
    flex-direction: column;
    align-items: stretch;
  }

  .search-input,
  .select-input {
    min-width: 0;
    width: 100%;
  }
}
"""
}

for path, content in files.items():
    full_path = os.path.join(os.getcwd(), path)
    os.makedirs(os.path.dirname(full_path), exist_ok=True)
    with open(full_path, "w", encoding="utf-8") as f:
        f.write(content)

print("Scaffold complete.")
