import { useState, useEffect, createContext, useContext } from "react";
import {
  LayoutDashboard, Hexagon, Shield, Eye, ClipboardList, Settings,
  ChevronLeft, ChevronRight, Activity, Lock, Unlock, Zap,
  Terminal, Radar, AlertTriangle, CheckCircle2, XCircle, Ban,
  TrendingUp, Server, Fingerprint, LogOut, X, ChevronDown, Users,
  FileSearch, EyeOff, Plus, Search, Edit3, Trash2, Save, Plug,
  Cloud, Brain, MessageSquare, Globe, KeyRound, CreditCard,
  LockKeyhole, SlidersHorizontal, Webhook, LockKeyholeOpen,
  MoreHorizontal, Gauge, ChevronUp, Sparkles, Radio, BarChart3
} from "lucide-react";
import {
  AreaChart, Area, XAxis, YAxis, CartesianGrid,
  Tooltip, ResponsiveContainer, RadarChart, PolarGrid,
  PolarAngleAxis, PolarRadiusAxis, Radar as RechartsRadar,
  LineChart, Line
} from "recharts";
import {
  type CitadelRole, type RBACPermissions,
  getPermissions, getRoleLabel, getRoleColor, getRoleDescription, isExecutive
} from "./rbac";



/* ═══════════════════════════════════════════
   RBAC CONTEXT
   ═══════════════════════════════════════════ */
interface RBACCtx { role: CitadelRole; permissions: RBACPermissions; setRole: (r: CitadelRole) => void; }
const RBACContext = createContext<RBACCtx>({ role: "executive", permissions: getPermissions("executive"), setRole: () => {} });
function useRBAC() { return useContext(RBACContext); }
function RBACProvider({ children }: { children: React.ReactNode }) {
  const [role, setRole] = useState<CitadelRole>("executive");
  return <RBACContext.Provider value={{ role, permissions: getPermissions(role), setRole }}>{children}</RBACContext.Provider>;
}
function Can({ permission, children, fallback }: { permission: keyof RBACPermissions; children: React.ReactNode; fallback?: React.ReactNode }) {
  const { permissions } = useRBAC();
  return permissions[permission] ? <>{children}</> : fallback ? <>{fallback}</> : null;
}
function IsExecutive({ children }: { children: React.ReactNode }) {
  const { role } = useRBAC();
  return isExecutive(role) ? <>{children}</> : null;
}

/* ═══════════════════════════════════════════
   TYPES
   ═══════════════════════════════════════════ */
interface Agent {
  id: string; name: string; status: "healthy" | "warning" | "critical" | "offline";
  healthScore: number; tokenSpend: number; tokenBudget: number; actionsToday: number;
  compliance: ("EU AI Act" | "NIST" | "SOC2" | "HIPAA")[]; lastActive: string;
  policies: { id: string; name: string; status: "active" | "pending" | "violated"; framework: string }[];
  owner: string; quarantined: boolean;
}
interface Policy {
  id: string; name: string; description: string; framework: string;
  status: "active" | "draft" | "disabled"; created: string;
  severity: "low" | "medium" | "high" | "critical";
}

/* ═══════════════════════════════════════════
   MOCK DATA
   ═══════════════════════════════════════════ */
const CURRENT_USER = "op-1";

const DATA_1H = Array.from({ length: 12 }, (_, i) => ({
  time: `:${String(i * 5).padStart(2, "0")}`,
  intercepted: 300 + Math.floor(Math.random() * 200),
  blocked: Math.floor(Math.random() * 8),
  safe: 0,
}));
DATA_1H.forEach(d => d.safe = d.intercepted - d.blocked);

const DATA_6H = Array.from({ length: 24 }, (_, i) => ({
  time: `${String(i).padStart(2, "0")}:00`,
  intercepted: [1200,980,750,620,580,890,1450,2100,3200,4800,5200,4900,6100,5800,7200,8100,7600,6900,5400,4200,3600,2800,1900,1400][i] || 1000,
  blocked: [12,8,5,3,4,15,22,18,31,45,38,29,52,41,67,78,55,42,35,28,19,14,9,7][i] || 5,
  safe: 0,
}));
DATA_6H.forEach(d => d.safe = d.intercepted - d.blocked);

const DATA_24H = DATA_6H;

const RADAR_DATA = [
  { axis: "Bias", value: 94 }, { axis: "Hallucination", value: 88 },
  { axis: "Security", value: 97 }, { axis: "PII Protection", value: 99 }, { axis: "Latency", value: 91 },
];

const SPARK_A1 = [42,45,48,52,50,55,58,62,60,65,70,68,72,75,80,78,82,85,80,76,72,68,65,60];
const SPARK_A2 = [30,32,35,38,36,40,42,45,43,48,50,52,55,53,58,60,57,55,52,48,45,42,40,38];
const SPARK_A3 = [80,82,85,88,90,92,95,93,96,98,100,98,95,92,90,88,85,82,80,78,76,74,72,70];
const SPARK_A4 = [20,22,25,28,30,32,35,33,36,38,40,42,45,43,40,38,36,35,33,30,28,26,25,24];
const SPARK_A5 = [95,96,97,98,99,100,99,98,97,96,95,94,93,92,91,90,89,88,87,86,85,84,83,82];
const SPARK_A6 = [35,38,40,42,45,48,50,52,55,53,50,48,52,55,58,60,57,55,52,50,48,45,42,40];
const SPARK_A7 = [0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0];
const SPARK_A8 = [50,52,55,58,60,62,65,63,60,58,62,65,68,70,67,65,62,60,58,55,52,50,48,46];
const SPARKS: Record<string, number[]> = { a1: SPARK_A1, a2: SPARK_A2, a3: SPARK_A3, a4: SPARK_A4, a5: SPARK_A5, a6: SPARK_A6, a7: SPARK_A7, a8: SPARK_A8 };

const INITIAL_AGENTS: Agent[] = [
  { id: "a1", name: "nova-v2", status: "healthy", healthScore: 98, tokenSpend: 42000, tokenBudget: 100000, actionsToday: 8420, compliance: ["EU AI Act", "NIST", "SOC2"], lastActive: "2s ago", owner: "op-1", quarantined: false, policies: [{id:"p1",name:"refund_limit > $1000",status:"active",framework:"SOC2"},{id:"p2",name:"pii_detection_strict",status:"active",framework:"HIPAA"},{id:"p3",name:"eu_ai_act_art14",status:"active",framework:"EU AI Act"}] },
  { id: "a2", name: "forge-v1", status: "healthy", healthScore: 94, tokenSpend: 28000, tokenBudget: 80000, actionsToday: 5630, compliance: ["EU AI Act", "SOC2"], lastActive: "5s ago", owner: "op-1", quarantined: false, policies: [{id:"p4",name:"db_write_approval",status:"active",framework:"SOC2"},{id:"p5",name:"rate_limit_1000rpm",status:"active",framework:"NIST"}] },
  { id: "a3", name: "cipher-v1", status: "warning", healthScore: 72, tokenSpend: 67000, tokenBudget: 75000, actionsToday: 12400, compliance: ["NIST", "SOC2", "HIPAA"], lastActive: "1s ago", owner: "op-2", quarantined: false, policies: [{id:"p6",name:"hipaa_access_control",status:"active",framework:"HIPAA"},{id:"p7",name:"token_budget_alert",status:"violated",framework:"NIST"}] },
  { id: "a4", name: "sentinel-v3", status: "healthy", healthScore: 99, tokenSpend: 15000, tokenBudget: 50000, actionsToday: 3200, compliance: ["EU AI Act", "NIST", "SOC2", "HIPAA"], lastActive: "8s ago", owner: "op-2", quarantined: false, policies: [{id:"p8",name:"kill_switch_ready",status:"active",framework:"EU AI Act"},{id:"p9",name:"audit_all_actions",status:"active",framework:"SOC2"}] },
  { id: "a5", name: "ghost-v1", status: "critical", healthScore: 34, tokenSpend: 91000, tokenBudget: 95000, actionsToday: 18700, compliance: ["SOC2"], lastActive: "now", owner: "op-1", quarantined: true, policies: [{id:"p10",name:"budget_exceeded",status:"violated",framework:"SOC2"},{id:"p11",name:"anomaly_detected",status:"violated",framework:"NIST"}] },
  { id: "a6", name: "atlas-v2", status: "healthy", healthScore: 91, tokenSpend: 33000, tokenBudget: 60000, actionsToday: 7100, compliance: ["EU AI Act", "NIST"], lastActive: "12s ago", owner: "op-3", quarantined: false, policies: [{id:"p12",name:"eu_transparency_l2",status:"active",framework:"EU AI Act"}] },
  { id: "a7", name: "pulse-v1", status: "offline", healthScore: 0, tokenSpend: 0, tokenBudget: 30000, actionsToday: 0, compliance: ["SOC2", "HIPAA"], lastActive: "2h ago", owner: "op-3", quarantined: false, policies: [{id:"p13",name:"auto_recovery",status:"pending",framework:"SOC2"}] },
  { id: "a8", name: "drift-v2", status: "healthy", healthScore: 87, tokenSpend: 19000, tokenBudget: 45000, actionsToday: 4300, compliance: ["NIST", "SOC2"], lastActive: "3s ago", owner: "op-1", quarantined: false, policies: [{id:"p14",name:"ml_drift_threshold",status:"active",framework:"NIST"}] },
];

const INITIAL_POLICIES: Policy[] = [
  { id: "pol1", name: "Block PII in Logs", description: "Redact PII before writing to audit trails.", framework: "HIPAA", status: "active", created: "2024-01-15", severity: "critical" },
  { id: "pol2", name: "Max 100 Requests/Hour", description: "Rate-limit each agent to 100 API calls/hour.", framework: "SOC2", status: "active", created: "2024-02-01", severity: "high" },
  { id: "pol3", name: "EU AI Act Transparency", description: "Require L2 explainability for high-risk decisions.", framework: "EU AI Act", status: "active", created: "2024-03-10", severity: "high" },
  { id: "pol4", name: "Kill-Switch <100ms", description: "Circuit breaker within 100ms of trigger.", framework: "NIST", status: "active", created: "2024-01-20", severity: "critical" },
  { id: "pol5", name: "Dual-Approval Changes", description: "Policy modifications need two admin signatures.", framework: "SOC2", status: "active", created: "2024-04-05", severity: "medium" },
  { id: "pol6", name: "Anomaly Z-Score > 3.0", description: "Flag behavior exceeding 3 std deviations.", framework: "NIST", status: "draft", created: "2024-05-12", severity: "medium" },
];

const AUDIT_LOGS = [
  { id: "l1", timestamp: "2024-12-28 14:32:01.243", agent: "nova-v2", action: "stripe.refund_create", result: "allowed", policy: "refund_limit", latency: "1.2ms", verified: true },
  { id: "l2", timestamp: "2024-12-28 14:32:01.245", agent: "forge-v1", action: "s3.bucket_delete", result: "denied", policy: "destruction_guard", latency: "0.8ms", verified: true },
  { id: "l3", timestamp: "2024-12-28 14:32:01.248", agent: "cipher-v1", action: "db.phi_query", result: "flagged", policy: "hipaa_access", latency: "2.1ms", verified: true },
  { id: "l4", timestamp: "2024-12-28 14:32:01.250", agent: "sentinel-v3", action: "slack.message_send", result: "allowed", policy: "comms_ok", latency: "0.6ms", verified: true },
  { id: "l5", timestamp: "2024-12-28 14:32:01.252", agent: "nova-v2", action: "github.pr_merge", result: "allowed", policy: "ci_approved", latency: "1.0ms", verified: true },
  { id: "l6", timestamp: "2024-12-28 14:32:01.255", agent: "ghost-v1", action: "aws.iam_escalate", result: "denied", policy: "privilege_guard", latency: "0.9ms", verified: true },
  { id: "l7", timestamp: "2024-12-28 14:32:01.258", agent: "atlas-v2", action: "openai.chat_complete", result: "allowed", policy: "token_budget_ok", latency: "3.2ms", verified: true },
  { id: "l8", timestamp: "2024-12-28 14:32:01.260", agent: "drift-v2", action: "db.customer_export", result: "flagged", policy: "gdpr_check", latency: "1.8ms", verified: true },
  { id: "l9", timestamp: "2024-12-28 14:32:01.263", agent: "forge-v1", action: "stripe.invoice_void", result: "allowed", policy: "invoice_guard", latency: "1.1ms", verified: true },
  { id: "l10", timestamp: "2024-12-28 14:32:01.265", agent: "nova-v2", action: "s3.object_delete", result: "denied", policy: "destruction_guard", latency: "0.7ms", verified: true },
  { id: "l11", timestamp: "2024-12-28 14:32:01.268", agent: "cipher-v1", action: "api.key_rotate", result: "allowed", policy: "security_maint", latency: "4.5ms", verified: true },
  { id: "l12", timestamp: "2024-12-28 14:32:01.270", agent: "sentinel-v3", action: "pagerduty.incident", result: "allowed", policy: "incident_response", latency: "2.3ms", verified: true },
];

/* ── DUAL NAV: Slim Icon-Only Sidebar ── */
const ComplianceBadge = ({ fw }: { fw: string }) => {
  const colors: Record<string, string> = { "EU AI Act": "bg-blue-50 text-blue-700 border-blue-200", "NIST": "bg-purple-50 text-purple-700 border-purple-200", "SOC2": "bg-emerald-50 text-emerald-700 border-emerald-200", "HIPAA": "bg-amber-50 text-amber-700 border-amber-200" };
  return <span className={`px-1.5 py-0.5 rounded text-[9px] font-bold uppercase border ${colors[fw] || "bg-slate-50 text-slate-500"}`}>{fw}</span>;
};

/* ── Slim Icon-Only Sidebar ── */
function SlimSidebar({ activePage, onNavigate }: { activePage: string; onNavigate: (p: string) => void }) {
  const { role } = useRBAC();
  const items = [
    { id: "dashboard", icon: LayoutDashboard, label: "Dashboard" },
    { id: "agents", icon: Server, label: "Agents" },
    { id: "connectors", icon: Plug, label: "Connectors" },
    { id: "policies", icon: Shield, label: "Policies" },
    { id: "approvals", icon: ClipboardList, label: "Approvals" },
    { id: "audit", icon: Eye, label: "Audit" },
    { id: "reports", icon: BarChart3, label: "Reports" },
    { id: "lens", icon: Radar, label: "Lens" },
  ];
  return (
    <aside className="fixed left-0 top-0 bottom-0 z-50 w-[60px] bg-slate-900 border-r border-slate-800/80 flex flex-col items-center select-none">
      {/* Logo */}
      <div className="h-14 flex items-center justify-center shrink-0">
        <Hexagon size={24} strokeWidth={1.5} className="text-[#2B9CFB]" />
      </div>

      {/* Divider */}
      <div className="w-7 h-px bg-slate-800 mb-3" />

      {/* Main nav */}
      <nav className="flex-1 flex flex-col items-center gap-2 w-full px-2">
        {items.map((item) => (
          <button
            key={item.id}
            onClick={() => onNavigate(item.id)}
            title={item.label}
            className={`w-full h-10 rounded-xl flex items-center justify-center transition-all duration-200 relative group ${
              activePage === item.id
                ? "bg-[#2B9CFB]/15 text-[#2B9CFB] border border-[#2B9CFB]/20 shadow-[0_0_12px_rgba(43,156,251,0.15)]"
                : "text-slate-500 hover:text-slate-200 hover:bg-slate-800/60 border border-transparent"
            }`}
          >
            <item.icon size={18} strokeWidth={activePage === item.id ? 2 : 1.5} />
            {/* Tooltip on hover */}
            <span className="absolute left-full ml-3 px-2.5 py-1.5 rounded-lg bg-slate-800 text-slate-200 font-mono text-[10px] font-bold uppercase tracking-wider whitespace-nowrap opacity-0 group-hover:opacity-100 pointer-events-none transition-opacity z-50 border border-slate-700 shadow-xl">
              {item.label}
            </span>
          </button>
        ))}
      </nav>

      {/* Bottom section */}
      <div className="w-full flex flex-col items-center gap-2 pb-4 px-2">
        <div className="w-7 h-px bg-slate-800 mb-1" />
        <button
          onClick={() => onNavigate("settings")}
          title="Settings"
          className={`w-full h-10 rounded-xl flex items-center justify-center transition-all duration-200 group relative ${
            activePage === "settings"
              ? "bg-[#2B9CFB]/15 text-[#2B9CFB] border border-[#2B9CFB]/20 shadow-[0_0_12px_rgba(43,156,251,0.15)]"
              : "text-slate-500 hover:text-slate-200 hover:bg-slate-800/60 border border-transparent"
          }`}
        >
          <Settings size={18} strokeWidth={activePage === "settings" ? 2 : 1.5} />
          <span className="absolute left-full ml-3 px-2.5 py-1.5 rounded-lg bg-slate-800 text-slate-200 font-mono text-[10px] font-bold uppercase tracking-wider whitespace-nowrap opacity-0 group-hover:opacity-100 pointer-events-none transition-opacity z-50 border border-slate-700 shadow-xl">
            Settings
          </span>
        </button>
        {/* Role avatar */}
        <div className="relative group mt-1">
          <div className={`w-8 h-8 rounded-full flex items-center justify-center text-[10px] font-bold font-mono border ${getRoleColor(role)} cursor-default`}>
            {role[0].toUpperCase()}
          </div>
          <span className="absolute left-full ml-3 px-2.5 py-1.5 rounded-lg bg-slate-800 text-slate-200 font-mono text-[10px] font-bold uppercase whitespace-nowrap opacity-0 group-hover:opacity-100 pointer-events-none transition-opacity z-50 border border-slate-700 shadow-xl">
            {getRoleLabel(role)}
          </span>
        </div>
      </div>
    </aside>
  );
}

/* ── COMMAND BAR (top) ── */
function CommandBar({ killSwitchActive, onToggleKillSwitch, onNavigate, activePage }: {
  killSwitchActive: boolean; onToggleKillSwitch: () => void; onNavigate: (p: string) => void; activePage: string;
}) {
  const { role, permissions, setRole } = useRBAC();
  const [guardMode, setGuardMode] = useState<"idle" | "confirming" | "executing">("idle");
  const [guardTimer, setGuardTimer] = useState<ReturnType<typeof setTimeout> | null>(null);
  const [showRoleMenu, setShowRoleMenu] = useState(false);

  const breadcrumbs: Record<string, string> = { dashboard: "Dashboard", agents: "Agent Swarm", connectors: "Connectors", policies: "Policy Vault", approvals: "Approvals", audit: "Audit Stream", lens: "Citadel Lens", settings: "Settings" };

  const handleKill = () => {
    if (!permissions.canTriggerKillSwitch) return;
    if (killSwitchActive) { onToggleKillSwitch(); setGuardMode("idle"); return; }
    if (guardMode === "idle") { setGuardMode("confirming"); const t = setTimeout(() => setGuardMode("idle"), 4000); setGuardTimer(t); }
    else if (guardMode === "confirming") { if (guardTimer) clearTimeout(guardTimer); setGuardMode("executing"); setTimeout(() => { onToggleKillSwitch(); setGuardMode("idle"); }, 600); }
  };

  useEffect(() => () => { if (guardTimer) clearTimeout(guardTimer); }, [guardTimer]);

  return (
    <header className="h-14 glass-strong border-b border-slate-200/50 flex items-center justify-between px-4 sticky top-0 z-30">
      {/* Left: Breadcrumbs + Search */}
      <div className="flex items-center gap-4">
        <div className="flex items-center gap-2">
          <span className="font-mono text-[11px] text-slate-400">Citadel</span>
          <ChevronRight size={12} className="text-slate-300" />
          <span className="font-display text-sm font-semibold text-slate-800">{breadcrumbs[activePage] || activePage}</span>
        </div>
        <div className="h-5 w-px bg-slate-200" />
        <div className="flex items-center gap-2 bg-slate-100/60 rounded-lg px-3 py-1.5 border border-slate-200/60">
          <Search size={13} className="text-slate-400" />
          <input placeholder="Search agents, policies, audit..." className="bg-transparent text-xs text-slate-600 outline-none w-48 placeholder:text-slate-400" />
        </div>
      </div>

      {/* Right: Status + Kill + Role */}
      <div className="flex items-center gap-3">
        <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-white/60 border border-slate-200/60">
          <span className="relative flex h-2 w-2">
            <span className={`absolute inline-flex h-full w-full rounded-full opacity-75 ${killSwitchActive ? "bg-red-400 animate-pulse-red" : "bg-cluely-400 animate-pulse-glow"}`} />
            <span className={`relative inline-flex rounded-full h-2 w-2 ${killSwitchActive ? "bg-red-500" : "bg-cluely-500"}`} />
          </span>
          <span className="font-mono text-[10px] text-slate-500">{killSwitchActive ? "LOCKED" : "OPERATIONAL"}</span>
        </div>

        <Can permission="canTriggerKillSwitch" fallback={
          <div className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-slate-100 text-slate-400 text-[10px] font-mono font-bold uppercase cursor-not-allowed">
            <Lock size={11} /> Kill Switch
          </div>
        }>
          <button onClick={handleKill} disabled={guardMode === "executing"}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg font-mono text-[10px] font-bold uppercase transition-all ${
              killSwitchActive ? "bg-emerald-50 text-emerald-600 border border-emerald-200" :
              guardMode === "confirming" ? "bg-red-500 text-white animate-pulse" :
              guardMode === "executing" ? "bg-red-700 text-red-100" :
              "bg-red-50 text-red-500 border border-red-200 hover:bg-red-100"
            }`}>
            {killSwitchActive ? <Unlock size={11} /> : guardMode === "confirming" ? <AlertTriangle size={11} /> : <Lock size={11} />}
            {killSwitchActive ? "UNLOCK" : guardMode === "confirming" ? "CONFIRM" : guardMode === "executing" ? "..." : "KILL"}
          </button>
        </Can>

        {/* Role Switcher */}
        <div className="relative">
          <button onClick={() => setShowRoleMenu(!showRoleMenu)}
            className={`flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg border text-[10px] font-bold font-mono uppercase transition-all ${getRoleColor(role)}`}>
            {getRoleLabel(role)}<ChevronDown size={10} />
          </button>
          {showRoleMenu && (
            <>
              <div className="fixed inset-0 z-40" onClick={() => setShowRoleMenu(false)} />
              <div className="absolute right-0 top-full mt-1 w-48 bg-white rounded-xl border border-slate-200 shadow-lg z-50 overflow-hidden">
                {(["operator", "admin", "executive", "auditor"] as CitadelRole[]).map((r) => (
                  <button key={r} onClick={() => { setRole(r); setShowRoleMenu(false); }}
                    className={`w-full text-left px-3 py-2.5 hover:bg-slate-50 transition-colors flex items-center gap-2 ${role === r ? "bg-blue-50/40" : ""}`}>
                    <div className={`w-1.5 h-1.5 rounded-full ${r === "executive" ? "bg-amber-400" : r === "admin" ? "bg-purple-400" : r === "operator" ? "bg-blue-400" : "bg-slate-400"}`} />
                    <span className="font-display text-[11px] font-bold text-slate-700">{getRoleLabel(r)}</span>
                    {role === r && <CheckCircle2 size={12} className="ml-auto text-cluely-500" />}
                  </button>
                ))}
              </div>
            </>
          )}
        </div>
      </div>
    </header>
  );
}

/* ═══════════════════════════════════════════
   DASHBOARD WIDGETS
   ═══════════════════════════════════════════ */
function KpiCards({ agents }: { agents: Agent[] }) {
  const { permissions } = useRBAC();
  const visible = permissions.canActivateAnyAgent ? agents : agents.filter(a => a.owner === CURRENT_USER);
  const cards = [
    { label: "Posture", value: "94.2", sub: "/100", icon: Shield, color: "text-emerald-600", accent: "bg-emerald-500" },
    { label: "Agents", value: `${visible.filter(a => a.status === "healthy").length}/${visible.length}`, sub: visible.filter(a => a.quarantined).length > 0 ? `${visible.filter(a => a.quarantined).length} iso` : "healthy", icon: Server, color: "text-cluely-600", accent: "bg-cluely-500" },
    { label: "Actions", value: visible.filter(a => !a.quarantined).reduce((s, a) => s + a.actionsToday, 0).toLocaleString(), sub: "today", icon: TrendingUp, color: "text-indigo-600", accent: "bg-indigo-500" },
    { label: "Blocked", value: "516", sub: "0.86%", icon: Ban, color: "text-red-500", accent: "bg-red-500" },
    { label: "Pending", value: "3", sub: "approvals", icon: ClipboardList, color: "text-amber-600", accent: "bg-amber-500" },
    { label: "Latency", value: "1.4ms", sub: "p99 4.2ms", icon: Zap, color: "text-cyan-600", accent: "bg-cyan-500" },
  ];
  return (
    <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3">
      {cards.map((c) => (
        <div key={c.label} className="glass-blueprint rounded-xl p-4 glow-cluely-subtle">
          <div className="flex items-center gap-2 mb-3">
            <div className={`w-1.5 h-1.5 rounded-full ${c.accent}`} />
            <span className="font-mono text-[9px] text-slate-400 uppercase tracking-wider">{c.label}</span>
          </div>
          <p className={`font-display text-xl font-bold tabular-nums ${c.color}`}>{c.value}</p>
          <p className="font-mono text-[10px] text-slate-400 mt-0.5">{c.sub}</p>
        </div>
      ))}
    </div>
  );
}

function GovernanceHeartbeat() {
  const [timeRange, setTimeRange] = useState<"1h" | "6h" | "24h">("6h");
  const chartData = timeRange === "1h" ? DATA_1H : timeRange === "6h" ? DATA_6H : DATA_24H;
  return (
    <div className="glass-blueprint rounded-2xl overflow-hidden glow-cluely-subtle">
      <div className="px-5 py-3.5 border-b border-slate-200/40 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Activity size={15} className="text-cluely-500" />
          <h3 className="font-display text-sm font-bold text-slate-800 uppercase tracking-tight">Governance Heartbeat</h3>
          <span className="font-mono text-[10px] text-slate-400">Actions intercepted</span>
        </div>
        <div className="flex items-center gap-0.5 bg-slate-100/60 rounded-lg p-0.5">
          {(["1h", "6h", "24h"] as const).map((r) => (
            <button key={r} onClick={() => setTimeRange(r)}
              className={`px-3 py-1 rounded-md font-mono text-[10px] font-bold transition-all ${timeRange === r ? "bg-white text-slate-700 shadow-sm border border-slate-200" : "text-slate-400 hover:text-slate-600"}`}>{r}</button>
          ))}
        </div>
      </div>
      <div className="p-5">
        <div className="flex items-center gap-5 mb-3">
          {[{ c: "bg-cluely-400", l: "Intercepted" }, { c: "bg-red-400", l: "Blocked" }, { c: "bg-emerald-400", l: "Safe" }].map(i => (
            <div key={i.l} className="flex items-center gap-1.5"><div className={`w-2.5 h-1 rounded-full ${i.c}`} /><span className="font-mono text-[9px] text-slate-500">{i.l}</span></div>
          ))}
        </div>
        <ResponsiveContainer width="100%" height={220}>
          <AreaChart data={chartData} margin={{ top: 5, right: 5, left: -20, bottom: 0 }}>
            <defs>
              <linearGradient id="sg" x1="0" y1="0" x2="0" y2="1"><stop offset="5%" stopColor="#34d399" stopOpacity={0.18} /><stop offset="95%" stopColor="#34d399" stopOpacity={0} /></linearGradient>
              <linearGradient id="ig" x1="0" y1="0" x2="0" y2="1"><stop offset="5%" stopColor="#60a5fa" stopOpacity={0.12} /><stop offset="95%" stopColor="#60a5fa" stopOpacity={0} /></linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" vertical={false} />
            <XAxis dataKey="time" tick={{ fill: "#94a3b8", fontSize: 9, fontFamily: "JetBrains Mono" }} axisLine={false} tickLine={false} />
            <YAxis tick={{ fill: "#94a3b8", fontSize: 9, fontFamily: "JetBrains Mono" }} axisLine={false} tickLine={false} />
            <Tooltip contentStyle={{ background: "#fff", border: "1px solid #e2e8f0", borderRadius: "10px", fontFamily: "JetBrains Mono", fontSize: "10px" }} />
            <Area type="monotone" dataKey="intercepted" stroke="#3b82f6" strokeWidth={2} fill="url(#ig)" dot={false} />
            <Area type="monotone" dataKey="safe" stroke="#10b981" strokeWidth={1.5} fill="url(#sg)" dot={false} />
            <Area type="monotone" dataKey="blocked" stroke="#ef4444" strokeWidth={2} fill="none" dot={{ r: 2.5, fill: "#ef4444" }} />
          </AreaChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}

function MiniSparkline({ data, color }: { data: number[]; color: string }) {
  const chartData = data.map((v, i) => ({ i, v }));
  return (
    <div style={{ width: 80, height: 28 }}>
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={chartData} margin={{ top: 2, right: 2, left: 2, bottom: 2 }}>
          <Line type="monotone" dataKey="v" stroke={color} strokeWidth={1.5} dot={false} />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}

function SwarmOverview({ agents, onAgentClick, onQuarantine }: { agents: Agent[]; onAgentClick: (a: Agent) => void; onQuarantine: (id: string) => void }) {
  const { role, permissions } = useRBAC();
  const [filter, setFilter] = useState<"all" | "healthy" | "warning" | "critical" | "quarantined">("all");
  const visible = permissions.canActivateAnyAgent ? agents : agents.filter(a => a.owner === CURRENT_USER);
  const filtered = visible.filter(a => filter === "all" ? true : filter === "quarantined" ? a.quarantined : filter === "critical" ? a.status === "critical" || a.status === "offline" : a.status === filter);
  const counts = { all: visible.length, healthy: visible.filter(a => a.status === "healthy" && !a.quarantined).length, warning: visible.filter(a => a.status === "warning" && !a.quarantined).length, critical: visible.filter(a => (a.status === "critical" || a.status === "offline") && !a.quarantined).length, quarantined: visible.filter(a => a.quarantined).length };

  return (
    <div className="glass-blueprint rounded-2xl overflow-hidden glow-cluely-subtle">
      <div className="px-5 py-3.5 border-b border-slate-200/40 flex items-center justify-between flex-wrap gap-3">
        <div className="flex items-center gap-3">
          <Server size={15} className="text-cluely-500" />
          <h3 className="font-display text-sm font-bold text-slate-800 uppercase tracking-tight">Swarm Overview</h3>
          <span className="font-mono text-[10px] text-slate-400">{visible.length} agents</span>
        </div>
        <div className="flex items-center gap-0.5 bg-slate-100/60 rounded-lg p-0.5">
          {(["all", "healthy", "warning", "critical", "quarantined"] as const).map(f => (
            <button key={f} onClick={() => setFilter(f)} className={`px-2.5 py-1 rounded-md font-mono text-[9px] font-bold transition-all ${filter === f ? "bg-white text-slate-700 shadow-sm border border-slate-200" : "text-slate-400 hover:text-slate-600"}`}>
              {f === "quarantined" ? "ISO" : f.toUpperCase()} {counts[f]}
            </button>
          ))}
        </div>
      </div>
      <div className="p-5">
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-3">
          {filtered.map((agent) => {
            const isOwn = agent.owner === CURRENT_USER;
            const canClick = permissions.canActivateAnyAgent || (permissions.canActivateOwnAgent && isOwn);
            const isQ = agent.quarantined;
            const sparkData = SPARKS[agent.id] || [];
            const sparkColor = isQ ? "#ef4444" : agent.status === "healthy" ? "#10b981" : agent.status === "warning" ? "#f59e0b" : "#94a3b8";
            return (
              <div key={agent.id} onClick={() => canClick && onAgentClick(agent)}
                className={`p-4 rounded-xl border transition-all ${canClick ? "cursor-pointer" : ""} ${
                  isQ ? "bg-red-50/30 border-red-300/50" :
                  agent.status === "healthy" ? "bg-white/50 border-emerald-200/40 hover:border-emerald-300/60 hover:shadow-sm" :
                  agent.status === "warning" ? "bg-white/50 border-amber-200/40 hover:border-amber-300/60 hover:shadow-sm" :
                  agent.status === "critical" ? "bg-white/50 border-red-200/40 hover:border-red-300/60 hover:shadow-sm" :
                  "bg-white/40 border-slate-200/40"
                }`}>
                <div className="flex items-center justify-between mb-2">
                  <div className="flex items-center gap-2">
                    <div className={`w-1.5 h-1.5 rounded-full ${isQ ? "bg-red-500" : agent.status === "healthy" ? "bg-emerald-400" : agent.status === "warning" ? "bg-amber-400 animate-pulse-amber" : agent.status === "critical" ? "bg-red-400 animate-pulse-red" : "bg-slate-400"}`} />
                    <span className="font-mono text-xs font-bold text-slate-800">{agent.name}</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <MiniSparkline data={sparkData} color={sparkColor} />
                    {isQ && <Lock size={10} className="text-red-500" />}
                  </div>
                </div>
                <div className="flex items-center justify-between mb-2">
                  <span className="font-mono text-[9px] text-slate-400 uppercase">Health</span>
                  <span className={`font-mono text-xs font-bold ${isQ ? "text-red-600" : agent.healthScore >= 90 ? "text-emerald-600" : agent.healthScore >= 70 ? "text-amber-600" : "text-red-600"}`}>{isQ ? "0" : agent.healthScore}<span className="text-slate-400 font-normal">/100</span></span>
                </div>
                <div className="h-1 bg-slate-200 rounded-full overflow-hidden mb-3">
                  <div className={`h-full rounded-full ${isQ ? "bg-red-400" : agent.healthScore >= 90 ? "bg-emerald-400" : agent.healthScore >= 70 ? "bg-amber-400" : "bg-red-400"}`} style={{ width: isQ ? "100%" : `${agent.healthScore}%` }} />
                </div>
                <div className="flex items-center justify-between">
                  <span className="font-mono text-[10px] text-slate-500">{isQ ? "0" : agent.actionsToday.toLocaleString()} act</span>
                  <div className="flex gap-1">{agent.compliance.map(c => <ComplianceBadge key={c} fw={c} />)}</div>
                </div>
                <Can permission={isOwn ? "canDeactivateOwnAgent" : "canDeactivateAnyAgent"}>
                  <button onClick={(e) => { e.stopPropagation(); onQuarantine(agent.id); }}
                    className={`mt-2 w-full py-1 rounded-lg font-mono text-[9px] font-bold uppercase tracking-wider border transition-all ${
                      isQ ? "bg-emerald-50 text-emerald-600 border-emerald-200 hover:bg-emerald-100" : "bg-red-50 text-red-500 border-red-200 hover:bg-red-100"
                    }`}>{isQ ? "Restore" : "Quarantine"}</button>
                </Can>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}

function CitadelLens() {
  return (
    <div className="glass-blueprint rounded-2xl overflow-hidden glow-cluely-subtle">
      <div className="px-5 py-3.5 border-b border-slate-200/40 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Radar size={15} className="text-cluely-500" />
          <h3 className="font-display text-sm font-bold text-slate-800 uppercase tracking-tight">Citadel Lens</h3>
        </div>
        <div className="flex items-center gap-1.5">
          <div className="w-1.5 h-1.5 rounded-full bg-emerald-500" />
          <span className="font-mono text-[10px] text-emerald-600 font-bold">93.8</span>
        </div>
      </div>
      <div className="p-5">
        <div style={{ height: 180 }}>
          <ResponsiveContainer width="100%" height={180}>
            <RadarChart data={RADAR_DATA} cx="50%" cy="50%" outerRadius="65%">
              <PolarGrid stroke="#e2e8f0" strokeDasharray="3 3" />
              <PolarAngleAxis dataKey="axis" tick={{ fill: "#64748b", fontSize: 9, fontFamily: "JetBrains Mono" }} />
              <PolarRadiusAxis angle={90} domain={[0, 100]} tick={{ fill: "#cbd5e1", fontSize: 8 }} axisLine={false} />
              <RechartsRadar name="Alignment" dataKey="value" stroke="#3b9ae5" fill="#3b9ae5" fillOpacity={0.1} strokeWidth={2} dot={{ r: 3, fill: "#3b9ae5" }} />
            </RadarChart>
          </ResponsiveContainer>
        </div>
        <div className="space-y-1.5 mt-2">
          {RADAR_DATA.map(item => (
            <div key={item.axis} className="flex items-center gap-2">
              <span className="font-mono text-[10px] text-slate-500 w-20">{item.axis}</span>
              <div className="flex-1 h-1.5 bg-slate-100 rounded-full overflow-hidden">
                <div className="h-full rounded-full bg-gradient-to-r from-cluely-500 to-emerald-400" style={{ width: `${item.value}%` }} />
              </div>
              <span className={`font-mono text-xs font-bold w-6 text-right ${item.value >= 95 ? "text-emerald-600" : "text-cluely-600"}`}>{item.value}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}


/* ═══════════════════════════════════════════
   AUDIT LEDGER (Financial Ledger Style)
   ═══════════════════════════════════════════ */
function AuditStream() {
  const { permissions } = useRBAC();
  const icon = (r: string) => r === "allowed" ? <CheckCircle2 size={10} className="text-emerald-500 shrink-0" /> : r === "denied" ? <Ban size={10} className="text-red-500 shrink-0" /> : <AlertTriangle size={10} className="text-amber-500 shrink-0" />;
  const resultClass = (r: string) => r === "allowed" ? "text-emerald-700" : r === "denied" ? "text-red-700 font-bold" : "text-amber-700";
  return (
    <div className="glass-blueprint rounded-2xl overflow-hidden glow-cluely-subtle">
      <div className="px-5 py-3.5 border-b border-slate-200/40 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Terminal size={15} className="text-cluely-500" />
          <h3 className="font-display text-sm font-bold text-slate-800 uppercase tracking-tight">Audit Ledger</h3>
          <span className="font-mono text-[10px] text-slate-400">Immutable log — SHA-256 verified</span>
        </div>
        <div className="flex items-center gap-2">
          <span className="font-mono text-[10px] text-slate-400">{AUDIT_LOGS.length} entries</span>
          <div className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
        </div>
      </div>
      <div className="bg-slate-900 rounded-b-2xl overflow-hidden">
        <div className="px-4 py-2 flex items-center gap-2 border-b border-slate-700/60">
          <span className="w-2 h-2 rounded-full bg-[#FF5F57]" />
          <span className="w-2 h-2 rounded-full bg-[#FFBD2E]" />
          <span className="w-2 h-2 rounded-full bg-[#28C840]" />
          <span className="ml-3 font-mono text-[10px] text-slate-600">citadel@governance-audit:~</span>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr className="border-b border-slate-700/60">
                <th className="text-left py-2 px-3 font-mono text-[9px] text-slate-500 uppercase tracking-wider">#</th>
                <th className="text-left py-2 px-2 font-mono text-[9px] text-slate-500 uppercase tracking-wider">V</th>
                <th className="text-left py-2 px-2 font-mono text-[9px] text-slate-500 uppercase tracking-wider">Res</th>
                <th className="text-left py-2 px-2 font-mono text-[9px] text-slate-500 uppercase tracking-wider">Timestamp</th>
                <th className="text-left py-2 px-2 font-mono text-[9px] text-slate-500 uppercase tracking-wider">Agent</th>
                <th className="text-left py-2 px-2 font-mono text-[9px] text-slate-500 uppercase tracking-wider">Action</th>
                <th className="text-left py-2 px-2 font-mono text-[9px] text-slate-500 uppercase tracking-wider">Result</th>
                <th className="text-left py-2 px-2 font-mono text-[9px] text-slate-500 uppercase tracking-wider">Policy</th>
                <th className="text-right py-2 px-3 font-mono text-[9px] text-slate-500 uppercase tracking-wider">Latency</th>
              </tr>
            </thead>
            <tbody className="font-mono text-[11px]">
              {AUDIT_LOGS.map((log, idx) => (
                <tr key={log.id} className="ledger-row border-b border-slate-800/40 transition-colors">
                  <td className="py-2 px-3 text-slate-600">{String(idx + 1).padStart(4, "0")}</td>
                  <td className="py-2 px-2">{log.verified ? <CheckCircle2 size={10} className="text-emerald-500" /> : <XCircle size={10} className="text-slate-600" />}</td>
                  <td className="py-2 px-2">{icon(log.result)}</td>
                  <td className="py-2 px-2 text-slate-500">{log.timestamp}</td>
                  <td className="py-2 px-2 text-cluely-400">{log.agent}</td>
                  <td className="py-2 px-2 text-slate-300">{log.action}</td>
                  <td className={`py-2 px-2 uppercase ${resultClass(log.result)}`}>{log.result}</td>
                  <td className="py-2 px-2 text-slate-500">{log.policy}</td>
                  <td className="py-2 px-3 text-right text-slate-500">{log.latency}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <div className="px-4 py-2 border-t border-slate-700/60 flex items-center gap-2">
          <span className="text-slate-600">$</span><span className="animate-blink text-emerald-400">_</span>
        </div>
      </div>
    </div>
  );
}

/* ═══════════════════════════════════════════
   AGENT DRAWER (Slide-over)
   ═══════════════════════════════════════════ */
function AgentDrawer({ agent, onClose, onQuarantine }: { agent: Agent | null; onClose: () => void; onQuarantine: (id: string) => void }) {
  const { permissions } = useRBAC();
  if (!agent) return null;
  const isOwn = agent.owner === CURRENT_USER;
  const canQ = permissions.canDeactivateAnyAgent || (permissions.canDeactivateOwnAgent && isOwn);

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      {/* Backdrop */}
      <div className="absolute inset-0 bg-black/25 backdrop-blur-sm" onClick={onClose} />
      {/* Centered Modal */}
      <div className="relative z-10 w-full max-w-lg mx-4 glass-blueprint rounded-2xl shadow-2xl animate-fade-in overflow-hidden glow-cluely-subtle">
        {/* Header */}
        <div className="h-14 flex items-center justify-between px-6 border-b border-slate-200/60 shrink-0">
          <div className="flex items-center gap-3">
            <div className={`w-2.5 h-2.5 rounded-full ${agent.quarantined ? "bg-red-500" : agent.status === "healthy" ? "bg-emerald-400" : agent.status === "warning" ? "bg-amber-400" : agent.status === "critical" ? "bg-red-400" : "bg-slate-400"}`} />
            <h3 className="font-display font-bold text-slate-900">{agent.name}</h3>
            <span className={`font-mono text-[9px] px-2 py-0.5 rounded-full uppercase border ${agent.quarantined ? "bg-red-50 text-red-600 border-red-200" : agent.status === "healthy" ? "bg-emerald-50 text-emerald-600 border-emerald-200" : "bg-amber-50 text-amber-600 border-amber-200"}`}>{agent.quarantined ? "ISOLATED" : agent.status}</span>
          </div>
          <button onClick={onClose} className="p-1.5 rounded-lg hover:bg-slate-100 text-slate-400"><X size={16} /></button>
        </div>
        {/* Body */}
        <div className="p-6 space-y-5 max-h-[70vh] overflow-y-auto scrollbar-thin">
          {agent.quarantined && (
            <div className="p-4 rounded-xl bg-red-50 border border-red-200 flex items-center gap-3">
              <Lock size={16} className="text-red-500" />
              <div><p className="font-display text-sm font-bold text-red-700">Agent Isolated</p><p className="font-mono text-[10px] text-red-500">All traffic blocked. No actions permitted.</p></div>
            </div>
          )}
          <div>
            <div className="flex justify-between mb-1"><span className="font-mono text-[9px] text-slate-500 uppercase">Health Score</span>
              <span className={`font-mono text-lg font-bold ${agent.quarantined ? "text-red-600" : agent.healthScore >= 90 ? "text-emerald-600" : "text-amber-600"}`}>{agent.quarantined ? "0" : `${agent.healthScore}`}<span className="text-slate-400">/100</span></span>
            </div>
            <div className="h-2 bg-slate-100 rounded-full overflow-hidden"><div className={`h-full rounded-full ${agent.quarantined ? "bg-red-400" : agent.healthScore >= 90 ? "bg-emerald-400" : agent.healthScore >= 70 ? "bg-amber-400" : "bg-red-400"}`} style={{ width: agent.quarantined ? "100%" : `${agent.healthScore}%` }} /></div>
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div className="p-3 rounded-xl bg-slate-50 border border-slate-200/60">
              <p className="font-mono text-[9px] text-slate-500 uppercase">Tokens</p>
              <p className="font-mono text-sm font-bold text-slate-800 mt-1">{agent.tokenSpend.toLocaleString()}<span className="text-slate-400"> / {agent.tokenBudget.toLocaleString()}</span></p>
            </div>
            <div className="p-3 rounded-xl bg-slate-50 border border-slate-200/60">
              <p className="font-mono text-[9px] text-slate-500 uppercase">Actions</p>
              <p className="font-mono text-sm font-bold text-slate-800 mt-1">{agent.quarantined ? "0" : agent.actionsToday.toLocaleString()}</p>
            </div>
            <div className="p-3 rounded-xl bg-slate-50 border border-slate-200/60">
              <p className="font-mono text-[9px] text-slate-500 uppercase">Owner</p>
              <p className="font-mono text-sm font-bold text-slate-800 mt-1">{agent.owner}</p>
            </div>
            <div className="p-3 rounded-xl bg-slate-50 border border-slate-200/60">
              <p className="font-mono text-[9px] text-slate-500 uppercase">Compliance</p>
              <div className="flex flex-wrap gap-1 mt-1">{agent.compliance.map(c => <ComplianceBadge key={c} fw={c} />)}</div>
            </div>
          </div>
          <div>
            <h4 className="font-display text-xs font-bold text-slate-700 uppercase mb-2 flex items-center gap-2"><Fingerprint size={12} className="text-[#2B9CFB]" />Policy Chain</h4>
            <div className="space-y-1.5">
              {agent.policies.map((p, i) => (
                <div key={p.id} className="flex items-center gap-2 p-2.5 rounded-xl bg-slate-50 border border-slate-200/40">
                  <span className="font-mono text-[9px] text-slate-400 w-4">{i + 1}</span>
                  <div className={`w-1.5 h-1.5 rounded-full ${p.status === "active" ? "bg-emerald-400" : p.status === "violated" ? "bg-red-400" : "bg-amber-400"}`} />
                  <div className="flex-1 min-w-0"><p className="font-mono text-xs text-slate-700 truncate">{p.name}</p><p className="font-mono text-[9px] text-slate-400">{p.framework}</p></div>
                </div>
              ))}
            </div>
          </div>
          <div className="flex gap-2 pt-1">
            {canQ && (
              <button onClick={() => { onQuarantine(agent.id); onClose(); }}
                className={`flex-1 py-2 rounded-xl font-display text-[10px] font-bold uppercase tracking-wider border transition-all ${agent.quarantined ? "bg-emerald-50 text-emerald-700 border-emerald-200 hover:bg-emerald-100" : "bg-red-50 text-red-600 border-red-200 hover:bg-red-100"}`}>
                {agent.quarantined ? "Restore Agent" : "Quarantine"}
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

/* ═══════════════════════════════════════════
   SECURITY GATE MODAL
   ═══════════════════════════════════════════ */
function SecurityGateModal({ isOpen, onClose, onUnlock, action }: { isOpen: boolean; onClose: () => void; onUnlock: () => void; action: string }) {
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [verifying, setVerifying] = useState(false);
  const handleVerify = () => {
    setVerifying(true); setError("");
    setTimeout(() => {
      if (password === "admin123") { setVerifying(false); setPassword(""); onUnlock(); onClose(); }
      else { setVerifying(false); setError("Invalid credentials. Access denied."); }
    }, 800);
  };
  if (!isOpen) return null;
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      <div className="absolute inset-0 bg-black/30 backdrop-blur-sm" onClick={onClose} />
      <div className="relative z-10 bg-white rounded-2xl border border-slate-200/60 shadow-2xl w-full max-w-sm p-6 animate-fade-in">
        <div className="flex items-center gap-3 mb-5">
          <div className="p-2.5 rounded-xl bg-cluely-50 border border-cluely-200"><LockKeyhole size={18} className="text-cluely-600" /></div>
          <div><h3 className="font-display text-base font-bold text-slate-900">Security Gate</h3><p className="font-mono text-[10px] text-slate-500">{action}</p></div>
        </div>
        <p className="text-xs text-slate-600 mb-3">Admin authentication required to proceed.</p>
        <div className="mb-3">
          <label className="font-mono text-[9px] text-slate-500 uppercase block mb-1">Passcode</label>
          <input type="password" value={password} onChange={e => { setPassword(e.target.value); setError(""); }} placeholder="••••••••"
            onKeyDown={e => e.key === "Enter" && handleVerify()} className="w-full px-3 py-2 rounded-xl border border-slate-200 bg-slate-50 text-sm font-mono outline-none focus:border-cluely-400 focus:ring-2 focus:ring-cluely-100" />
        </div>
        {error && <div className="mb-3 p-2.5 rounded-xl bg-red-50 border border-red-200 flex items-center gap-2"><AlertTriangle size={12} className="text-red-500" /><span className="text-xs text-red-600">{error}</span></div>}
        <div className="flex gap-2">
          <button onClick={onClose} className="flex-1 py-2 rounded-xl bg-slate-100 text-slate-600 font-display text-[10px] font-bold uppercase hover:bg-slate-200">Cancel</button>
          <button onClick={handleVerify} disabled={verifying || !password} className="flex-1 py-2 rounded-xl bg-cluely-500 text-white font-display text-[10px] font-bold uppercase hover:bg-cluely-600 transition-all disabled:opacity-50">{verifying ? "Verifying..." : "Verify"}</button>
        </div>
        <p className="text-center mt-2 font-mono text-[9px] text-slate-400">Demo: admin123</p>
      </div>
    </div>
  );
}


/* ═══════════════════════════════════════════
   PAGES: POLICY VAULT
   ═══════════════════════════════════════════ */
function PoliciesPage() {
  const { permissions } = useRBAC();
  const [policies, setPolicies] = useState(INITIAL_POLICIES);
  const [showGate, setShowGate] = useState(false);
  const [gateAction, setGateAction] = useState("");
  const [pendingAction, setPendingAction] = useState<(() => void) | null>(null);
  const [isUnlocked, setIsUnlocked] = useState(false);
  const [showAddForm, setShowAddForm] = useState(false);
  const [newPolicy, setNewPolicy] = useState({ name: "", description: "", framework: "SOC2", severity: "medium" as Policy["severity"] });

  const requireGate = (desc: string, action: () => void) => {
    if (isUnlocked) { action(); return; }
    setGateAction(desc); setPendingAction(() => action); setShowGate(true);
  };
  const handleUnlock = () => { setIsUnlocked(true); if (pendingAction) pendingAction(); setPendingAction(null); setTimeout(() => setIsUnlocked(false), 5 * 60 * 1000); };
  const toggleStatus = (id: string) => requireGate(`Toggle policy`, () => setPolicies(prev => prev.map(p => p.id === id ? { ...p, status: p.status === "active" ? "disabled" : "active" as Policy["status"] } : p)));
  const deletePolicy = (id: string) => requireGate(`Delete policy`, () => setPolicies(prev => prev.filter(p => p.id !== id)));
  const addPolicy = () => requireGate("Add policy", () => {
    const id = `pol${Date.now()}`;
    setPolicies(prev => [...prev, { id, name: newPolicy.name, description: newPolicy.description, framework: newPolicy.framework, status: "draft", created: new Date().toISOString().split("T")[0], severity: newPolicy.severity }]);
    setShowAddForm(false); setNewPolicy({ name: "", description: "", framework: "SOC2", severity: "medium" });
  });

  return (
    <div className="animate-fade-in space-y-5">
      <div className="flex items-center justify-between">
        <div><h2 className="font-display text-xl font-bold text-slate-900">Policy Vault</h2><p className="font-mono text-xs text-slate-500 mt-0.5">Governance rules and enforcement policies.</p></div>
        <div className="flex items-center gap-3">
          {isUnlocked && <span className="flex items-center gap-1 px-2.5 py-1 rounded-full bg-emerald-50 border border-emerald-200 text-emerald-600 font-mono text-[9px] font-bold uppercase"><Unlock size={10} /> Unlocked</span>}
          <Can permission="canEdit">
            <button onClick={() => setShowAddForm(true)} className="flex items-center gap-1.5 px-4 py-2 rounded-xl bg-cluely-500 text-white font-display text-xs font-bold uppercase hover:bg-cluely-600 transition-all shadow-sm"><Plus size={14} /> New</button>
          </Can>
        </div>
      </div>
      {showAddForm && (
        <div className="glass-blueprint rounded-2xl p-6 glow-cluely-subtle">
          <h3 className="font-display text-sm font-bold text-slate-800 mb-4">New Policy</h3>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
            <div><label className="font-mono text-[10px] text-slate-500 uppercase block mb-1">Name</label><input value={newPolicy.name} onChange={e => setNewPolicy({ ...newPolicy, name: e.target.value })} placeholder="e.g., Max Token Budget" className="w-full px-3 py-2 rounded-xl border border-slate-200 bg-slate-50/50 text-sm outline-none focus:border-cluely-400 focus:ring-2 focus:ring-cluely-100" /></div>
            <div><label className="font-mono text-[10px] text-slate-500 uppercase block mb-1">Framework</label><select value={newPolicy.framework} onChange={e => setNewPolicy({ ...newPolicy, framework: e.target.value })} className="w-full px-3 py-2 rounded-xl border border-slate-200 bg-slate-50/50 text-sm outline-none"><option>SOC2</option><option>EU AI Act</option><option>NIST</option><option>HIPAA</option></select></div>
            <div className="md:col-span-2"><label className="font-mono text-[10px] text-slate-500 uppercase block mb-1">Description</label><input value={newPolicy.description} onChange={e => setNewPolicy({ ...newPolicy, description: e.target.value })} placeholder="What this policy enforces..." className="w-full px-3 py-2 rounded-xl border border-slate-200 bg-slate-50/50 text-sm outline-none" /></div>
          </div>
          <div className="flex gap-2">
            <button onClick={() => setShowAddForm(false)} className="px-5 py-2 rounded-xl bg-slate-100 text-slate-600 font-display text-[10px] font-bold uppercase hover:bg-slate-200">Cancel</button>
            <button onClick={() => requireGate("Add policy", addPolicy)} disabled={!newPolicy.name.trim()} className="px-5 py-2 rounded-xl bg-cluely-500 text-white font-display text-[10px] font-bold uppercase hover:bg-cluely-600 disabled:opacity-50">Save</button>
          </div>
        </div>
      )}
      <div className="glass-blueprint rounded-2xl overflow-hidden glow-cluely-subtle">
        <div className="px-5 py-3 border-b border-slate-200/30 flex justify-between"><span className="font-mono text-[10px] text-slate-500">{policies.length} policies</span><span className="font-mono text-[10px] text-slate-400">{policies.filter(p => p.status === "active").length} active</span></div>
        <div className="divide-y divide-slate-100/50">
          {policies.map(p => (
            <div key={p.id} className="px-5 py-3.5 flex items-center gap-4 hover:bg-slate-50/30 transition-colors">
              <div className={`w-2 h-2 rounded-full shrink-0 ${p.status === "active" ? "bg-emerald-400" : p.status === "draft" ? "bg-amber-400" : "bg-slate-300"}`} />
              <div className="flex-1 min-w-0">
                <p className="font-mono text-sm font-semibold text-slate-800">{p.name}</p>
                <p className="font-mono text-[10px] text-slate-500 mt-0.5">{p.description}</p>
                <div className="flex gap-2 mt-1">
                  <span className="font-mono text-[9px] px-1.5 py-0.5 rounded bg-slate-100 text-slate-500">{p.framework}</span>
                  <span className={`font-mono text-[9px] px-1.5 py-0.5 rounded-full border ${p.severity === "critical" ? "bg-red-50 text-red-600 border-red-200" : p.severity === "high" ? "bg-amber-50 text-amber-600 border-amber-200" : "bg-blue-50 text-blue-600 border-blue-200"}`}>{p.severity}</span>
                  <span className="font-mono text-[9px] text-slate-400">{p.created}</span>
                </div>
              </div>
              <span className={`font-mono text-[10px] px-2 py-0.5 rounded-full border font-bold ${p.status === "active" ? "bg-emerald-50 text-emerald-600 border-emerald-200" : p.status === "draft" ? "bg-amber-50 text-amber-600 border-amber-200" : "bg-slate-50 text-slate-500 border-slate-200"}`}>{p.status}</span>
              <Can permission="canEdit">
                <div className="flex items-center gap-0.5">
                  <button onClick={() => toggleStatus(p.id)} className="p-1.5 rounded-lg hover:bg-amber-50 text-slate-400 hover:text-amber-600"><Ban size={13} /></button>
                  <button onClick={() => deletePolicy(p.id)} className="p-1.5 rounded-lg hover:bg-red-50 text-slate-400 hover:text-red-600"><Trash2 size={13} /></button>
                </div>
              </Can>
            </div>
          ))}
        </div>
      </div>
      <SecurityGateModal isOpen={showGate} onClose={() => { setShowGate(false); setPendingAction(null); }} onUnlock={handleUnlock} action={gateAction} />
    </div>
  );
}

/* ═══════════════════════════════════════════
   PAGES: CONNECTORS
   ═══════════════════════════════════════════ */
function ConnectorsPage() {
  const [connectors, setConnectors] = useState([
    { id: "c1", name: "AWS Bedrock", provider: "Amazon", icon: "Cloud", desc: "Managed foundation model access via AWS.", connected: true },
    { id: "c2", name: "OpenAI", provider: "OpenAI", icon: "Brain", desc: "GPT-4, GPT-4 Turbo, and embeddings.", connected: true },
    { id: "c3", name: "Anthropic Claude", provider: "Anthropic", icon: "MessageSquare", desc: "Claude 3 Opus, Sonnet, Haiku.", connected: false },
    { id: "c4", name: "Azure OpenAI", provider: "Microsoft", icon: "Cloud", desc: "Enterprise OpenAI in your Azure tenant.", connected: false },
    { id: "c5", name: "Google Vertex", provider: "Google", icon: "Globe", desc: "Gemini and PaLM via Google Cloud.", connected: false },
    { id: "c6", name: "Cohere", provider: "Cohere", icon: "Brain", desc: "Command and Embed for enterprise RAG.", connected: false },
  ]);
  const [connectingId, setConnectingId] = useState<string | null>(null);
  const [apiKey, setApiKey] = useState("");
  const iconMap: Record<string, React.ElementType> = { Cloud, Brain, MessageSquare, Globe };
  const handleConnect = (id: string) => { if (!apiKey.trim()) return; setConnectors(prev => prev.map(c => c.id === id ? { ...c, connected: true } : c)); setConnectingId(null); setApiKey(""); };

  return (
    <div className="animate-fade-in space-y-6">
      <div><h2 className="font-display text-xl font-bold text-slate-900">Connectors</h2><p className="font-mono text-xs text-slate-500 mt-1">Add and manage LLM provider connections.</p></div>
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {connectors.map(c => {
          const Icon = iconMap[c.icon] || Cloud;
          return (
            <div key={c.id} className="glass-blueprint rounded-2xl p-6 glow-cluely-subtle flex flex-col">
              <div className="flex items-center gap-3 mb-4">
                <div className={`p-2.5 rounded-xl border ${c.connected ? "bg-emerald-50 border-emerald-200" : "bg-slate-50 border-slate-200"}`}><Icon size={20} className={c.connected ? "text-emerald-600" : "text-slate-600"} /></div>
                <div><h3 className="font-display text-sm font-bold text-slate-800">{c.name}</h3><p className="font-mono text-[10px] text-slate-400">{c.provider}</p></div>
                {c.connected && <span className="ml-auto flex items-center gap-1 px-2 py-0.5 rounded-full bg-emerald-50 border border-emerald-200 text-emerald-600 font-mono text-[8px] font-bold uppercase"><CheckCircle2 size={8} /> On</span>}
              </div>
              <p className="text-xs text-slate-600 mb-4 flex-1">{c.desc}</p>
              {connectingId === c.id ? (
                <div className="space-y-2">
                  <input value={apiKey} onChange={e => setApiKey(e.target.value)} placeholder="API key or IAM role ARN" className="w-full px-3 py-2 rounded-lg border border-slate-200 bg-slate-50 text-xs font-mono outline-none" />
                  <div className="flex gap-2">
                    <button onClick={() => { setConnectingId(null); setApiKey(""); }} className="flex-1 py-2 rounded-lg bg-slate-100 text-slate-600 font-mono text-[10px] font-bold uppercase hover:bg-slate-200">Cancel</button>
                    <button onClick={() => handleConnect(c.id)} disabled={!apiKey.trim()} className="flex-1 py-2 rounded-lg bg-cluely-500 text-white font-mono text-[10px] font-bold uppercase hover:bg-cluely-600 disabled:opacity-50">Connect</button>
                  </div>
                </div>
              ) : (
                <button onClick={() => setConnectingId(c.id)} className={`w-full py-2 rounded-xl font-display text-xs font-bold uppercase tracking-wider border transition-all ${c.connected ? "bg-slate-50 text-slate-500 border-slate-200 hover:bg-slate-100" : "bg-cluely-50 text-cluely-700 border-cluely-200 hover:bg-cluely-100"}`}>{c.connected ? "Manage" : "Connect"}</button>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}


/* ═══════════════════════════════════════════
   PAGES: SETTINGS (with Executive-only Billing)
   ═══════════════════════════════════════════ */
function SettingsPage() {
  const { role } = useRBAC();
  const availableTabs = [
    { id: "general" as const, label: "General", icon: SlidersHorizontal },
    { id: "security" as const, label: "Security", icon: LockKeyhole },
    { id: "team" as const, label: "Team", icon: Users },
    ...(isExecutive(role) ? [{ id: "billing" as const, label: "Billing", icon: CreditCard }] : []),
  ];
  const [tab, setTab] = useState(availableTabs[0].id);

  return (
    <div className="animate-fade-in space-y-5">
      <div><h2 className="font-display text-xl font-bold text-slate-900">Settings</h2><p className="font-mono text-xs text-slate-500 mt-1">Configure your Citadel deployment.</p></div>
      <div className="flex gap-0.5 bg-slate-100/60 rounded-xl p-1 w-fit">
        {availableTabs.map(t => (
          <button key={t.id} onClick={() => setTab(t.id)}
            className={`flex items-center gap-2 px-4 py-2 rounded-lg font-display text-xs font-bold transition-all ${tab === t.id ? "bg-white text-slate-800 shadow-sm border border-slate-200" : "text-slate-500 hover:text-slate-700"}`}>
            <t.icon size={14} /> {t.label}
          </button>
        ))}
      </div>

      {tab === "general" && (
        <div className="glass-blueprint rounded-2xl p-6 max-w-2xl glow-cluely-subtle space-y-5">
          <h3 className="font-display text-sm font-bold text-slate-800 uppercase tracking-tight">Organization</h3>
          {[{ label: "Organization Name", val: "Acme Corp" }, { label: "Contact Email", val: "security@acme.com" }, { label: "Timezone", val: "UTC" }].map(f => (
            <div key={f.label}><label className="font-mono text-[10px] text-slate-500 uppercase block mb-1">{f.label}</label>
              <input defaultValue={f.val} className="w-full px-4 py-2.5 rounded-xl border border-slate-200 bg-slate-50/50 text-sm outline-none focus:border-cluely-400 focus:ring-2 focus:ring-cluely-100" /></div>
          ))}
          <div><label className="font-mono text-[10px] text-slate-500 uppercase block mb-1">Notification Webhook</label>
            <div className="flex gap-2"><input defaultValue="https://hooks.slack.com/services/T00/B00/xxx" className="flex-1 px-4 py-2.5 rounded-xl border border-slate-200 bg-slate-50/50 text-sm font-mono outline-none" /><button className="px-4 py-2.5 rounded-xl bg-cluely-500 text-white font-display text-xs font-bold hover:bg-cluely-600">Test</button></div>
          </div>
        </div>
      )}

      {tab === "security" && (
        <div className="glass-blueprint rounded-2xl p-6 max-w-2xl glow-cluely-subtle space-y-4">
          <h3 className="font-display text-sm font-bold text-slate-800 uppercase tracking-tight">Security</h3>
          {[
            { label: "Multi-Factor Auth", desc: "Require MFA for admin actions", status: "Enabled", ok: true, icon: KeyRound },
            { label: "Session Timeout", desc: "Auto-logout after 30 min idle", status: "30 min", ok: true, icon: LockKeyhole },
            { label: "Audit Logging", desc: "All actions to immutable trail", status: "Active", ok: true, icon: Webhook },
          ].map(item => (
            <div key={item.label} className="flex items-center justify-between p-4 rounded-xl bg-slate-50 border border-slate-200/60">
              <div className="flex items-center gap-3">
                <div className="p-2 rounded-lg bg-blue-50 border border-blue-200"><item.icon size={15} className="text-cluely-600" /></div>
                <div><p className="font-mono text-sm font-semibold text-slate-800">{item.label}</p><p className="font-mono text-[10px] text-slate-500">{item.desc}</p></div>
              </div>
              <span className={`font-mono text-[10px] px-2.5 py-1 rounded-full border font-bold ${item.ok ? "bg-emerald-50 text-emerald-600 border-emerald-200" : "bg-slate-50 text-slate-500 border-slate-200"}`}>{item.status}</span>
            </div>
          ))}
          <div><label className="font-mono text-[10px] text-slate-500 uppercase block mb-1">API Key</label>
            <div className="flex gap-2"><input defaultValue="sk-citadel-••••••••••••••••••••••••" disabled className="flex-1 px-4 py-2.5 rounded-xl border border-slate-200 bg-slate-100 text-sm font-mono text-slate-400" />
              <button className="px-4 py-2.5 rounded-xl bg-amber-50 text-amber-700 border border-amber-200 font-display text-xs font-bold uppercase hover:bg-amber-100">Rotate</button></div>
          </div>
        </div>
      )}

      {tab === "team" && (
        <div className="glass-blueprint rounded-2xl overflow-hidden max-w-3xl glow-cluely-subtle">
          <div className="px-5 py-3.5 border-b border-slate-200/30 flex justify-between items-center">
            <h3 className="font-display text-sm font-bold text-slate-800 uppercase tracking-tight">Team Members</h3>
            <Can permission="canManageUsers">
              <button className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-cluely-50 text-cluely-600 border border-cluely-200 font-mono text-[10px] font-bold uppercase hover:bg-cluely-100"><Plus size={11} /> Invite</button>
            </Can>
          </div>
          <div className="divide-y divide-slate-100/50">
            {[{ name: "Sarah Chen", role: "executive" as CitadelRole, email: "sarah@acme.com", active: "2m ago" }, { name: "Marcus Johnson", role: "admin" as CitadelRole, email: "marcus@acme.com", active: "1h ago" }, { name: "Alex Rivera", role: "operator" as CitadelRole, email: "alex@acme.com", active: "Now" }, { name: "Priya Patel", role: "auditor" as CitadelRole, email: "priya@acme.com", active: "3h ago" }].map(m => (
              <div key={m.email} className="px-5 py-3.5 flex items-center gap-4 hover:bg-slate-50/30 transition-colors">
                <div className="w-8 h-8 rounded-full bg-cluely-100 border border-cluely-200 flex items-center justify-center"><span className="font-mono text-[10px] font-bold text-cluely-700">{m.name.split(" ").map(n => n[0]).join("")}</span></div>
                <div className="flex-1"><p className="font-mono text-sm font-semibold text-slate-800">{m.name}</p><p className="font-mono text-[10px] text-slate-400">{m.email}</p></div>
                <span className={`px-2 py-0.5 rounded-full text-[10px] font-bold border ${getRoleColor(m.role)}`}>{getRoleLabel(m.role)}</span>
                <span className="font-mono text-[10px] text-slate-400">{m.active}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {tab === "billing" && (
        <IsExecutive>
          <div className="glass-blueprint rounded-2xl p-6 max-w-2xl glow-cluely-subtle space-y-5">
            <h3 className="font-display text-sm font-bold text-slate-800 uppercase tracking-tight">Billing & Usage</h3>
            <div className="p-5 rounded-xl bg-cluely-50/40 border border-cluely-200/60">
              <div className="flex justify-between mb-1"><span className="font-mono text-[10px] text-cluely-600 uppercase">Plan</span><span className="font-mono text-xs font-bold text-cluely-700">Enterprise</span></div>
              <p className="font-mono text-sm text-slate-700">$2,499 / month</p><p className="font-mono text-[10px] text-slate-500">Billed annually. Next: Jan 15, 2025.</p>
            </div>
            {[{ label: "API Calls", val: "8.4M / 10M", pct: 84, from: "from-cluely-400", to: "to-cluely-600" }, { label: "Storage", val: "1.2 TB / 2 TB", pct: 60, from: "from-emerald-400", to: "to-emerald-600" }].map(bar => (
              <div key={bar.label}><div className="flex justify-between mb-1"><span className="font-mono text-[10px] text-slate-500 uppercase">{bar.label}</span><span className="font-mono text-xs font-bold text-slate-700">{bar.val}</span></div>
                <div className="h-2 bg-slate-100 rounded-full overflow-hidden"><div className={`h-full bg-gradient-to-r ${bar.from} ${bar.to} rounded-full`} style={{ width: `${bar.pct}%` }} /></div>
              </div>
            ))}
            <div className="flex gap-2 pt-2">
              <button className="flex-1 py-2 rounded-xl bg-slate-100 text-slate-600 font-display text-xs font-bold uppercase hover:bg-slate-200">Invoices</button>
              <button className="flex-1 py-2 rounded-xl bg-cluely-500 text-white font-display text-xs font-bold uppercase hover:bg-cluely-600">Upgrade</button>
            </div>
          </div>
        </IsExecutive>
      )}
    </div>
  );
}


/* ═══════════════════════════════════════════
   QUICK ACTIONS DOCK (bottom floating)
   ═══════════════════════════════════════════ */
function QuickActionsDock({ onAddAgent, onNewPolicy, onRunCheck }: { onAddAgent: () => void; onNewPolicy: () => void; onRunCheck: () => void }) {
  const { permissions } = useRBAC();
  const [visible, setVisible] = useState(false);

  return (
    <div className="fixed bottom-6 left-1/2 -translate-x-1/2 z-40 flex items-center gap-2">
      {visible && (
        <div className="flex items-center gap-2 animate-slide-up">
          <Can permission="canEdit">
            <button onClick={() => { onNewPolicy(); setVisible(false); }} className="flex items-center gap-2 px-4 py-2.5 rounded-2xl glass-blueprint text-slate-700 font-display text-xs font-bold uppercase shadow-lg hover:bg-white/70 transition-all border border-cluely-200/60">
              <Shield size={14} className="text-cluely-500" /> New Policy
            </button>
          </Can>
          <Can permission="canActivateOwnAgent">
            <button onClick={() => { onAddAgent(); setVisible(false); }} className="flex items-center gap-2 px-4 py-2.5 rounded-2xl glass-blueprint text-slate-700 font-display text-xs font-bold uppercase shadow-lg hover:bg-white/70 transition-all border border-cluely-200/60">
              <Server size={14} className="text-cluely-500" /> Add Agent
            </button>
          </Can>
          <button onClick={() => { onRunCheck(); setVisible(false); }} className="flex items-center gap-2 px-4 py-2.5 rounded-2xl glass-blueprint text-slate-700 font-display text-xs font-bold uppercase shadow-lg hover:bg-white/70 transition-all border border-cluely-200/60">
            <Zap size={14} className="text-cluely-500" /> Run Check
          </button>
        </div>
      )}
      <button onClick={() => setVisible(!visible)}
        className={`w-12 h-12 rounded-full flex items-center justify-center shadow-lg transition-all ${visible ? "bg-cluely-500 text-white rotate-45" : "bg-white text-cluely-600 border border-cluely-200/60"}`}>
        <Plus size={20} />
      </button>
    </div>
  );
}

/* ═══════════════════════════════════════════
   PAGE: DASHBOARD
   ═══════════════════════════════════════════ */
function ReportsPage({ agents }: { agents: Agent[] }) {
  const { role } = useRBAC();
  const scanResults = [
    { label: "Governance Posture", value: "94.2/100", grade: "A", detail: "Strong compliance posture across all frameworks." },
    { label: "EU AI Act Coverage", value: "92%", grade: "A", detail: "12 of 13 articles fully addressed." },
    { label: "NIST RMF Score", value: "88/100", grade: "B+", detail: "GOVERN and MAP functions at 95%." },
    { label: "SOC2 Type II", value: "96%", grade: "A", detail: "32 of 33 controls passing." },
    { label: "HIPAA Readiness", value: "100%", grade: "A+", detail: "All 8 safeguards verified." },
    { label: "Agent Health", value: `${agents.filter(a => a.status === "healthy").length}/${agents.length}`, grade: agents.filter(a => a.status === "healthy").length >= 6 ? "A" : "B", detail: `${agents.filter(a => a.status !== "healthy").length} agents need attention.` },
    { label: "Kill Switch Latency", value: "47ms", grade: "A+", detail: "Mean 47ms · P99 89ms · Target <100ms" },
    { label: "Audit Chain Integrity", value: "VERIFIED", grade: "A+", detail: "SHA-256 + JCS · All hashes valid." },
    { label: "Token Budget Risk", value: "MEDIUM", grade: "B", detail: "3 agents approaching 90% spend." },
    { label: "Anomaly Score", value: "0.34", grade: "A+", detail: "Z-score well below threshold of 3.0." },
  ];
  return (
    <div className="animate-fade-in space-y-5">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="font-display text-xl font-bold text-slate-900">Compliance Report</h2>
          <p className="font-mono text-xs text-slate-500 mt-1">Generated: {new Date().toISOString().replace("T", " ").slice(0, 19)} UTC · Role: {role}</p>
        </div>
        <span className="flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-emerald-50 border border-emerald-200 text-emerald-600 font-mono text-[10px] font-bold uppercase">
          <CheckCircle2 size={10} /> All Checks Passed
        </span>
      </div>
      <div className="glass-blueprint rounded-2xl overflow-hidden glow-cluely-subtle">
        <div className="px-5 py-3 border-b border-slate-200/40 grid grid-cols-12 gap-2">
          <span className="col-span-4 font-mono text-[10px] text-slate-500 uppercase tracking-wider">Check</span>
          <span className="col-span-2 font-mono text-[10px] text-slate-500 uppercase tracking-wider">Result</span>
          <span className="col-span-1 font-mono text-[10px] text-slate-500 uppercase tracking-wider text-center">Grade</span>
          <span className="col-span-5 font-mono text-[10px] text-slate-500 uppercase tracking-wider">Detail</span>
        </div>
        <div className="divide-y divide-slate-100/50">
          {scanResults.map((r, i) => (
            <div key={i} className="px-5 py-3 grid grid-cols-12 gap-2 items-center hover:bg-slate-50/30 transition-colors">
              <span className="col-span-4 font-mono text-xs text-slate-700">{r.label}</span>
              <span className="col-span-2 font-mono text-sm font-bold text-slate-800">{r.value}</span>
              <span className="col-span-1 flex justify-center"><span className={`px-2 py-0.5 rounded-full font-mono text-[10px] font-bold ${r.grade.startsWith("A") ? "bg-emerald-50 text-emerald-600 border border-emerald-200" : r.grade.startsWith("B") ? "bg-amber-50 text-amber-600 border border-amber-200" : "bg-red-50 text-red-600 border border-red-200"}`}>{r.grade}</span></span>
              <span className="col-span-5 font-mono text-[10px] text-slate-500">{r.detail}</span>
            </div>
          ))}
        </div>
      </div>
      <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
        {[
          { label: "Total Actions Scanned", value: "12,047,300" },
          { label: "Violations Found", value: "0" },
          { label: "Last Scan Duration", value: "1.2s" },
        ].map(s => (
          <div key={s.label} className="glass-blueprint rounded-xl p-4 text-center glow-cluely-subtle">
            <p className="font-mono text-[10px] text-slate-500 uppercase tracking-wider">{s.label}</p>
            <p className="font-display text-lg font-bold text-slate-800 mt-1">{s.value}</p>
          </div>
        ))}
      </div>
    </div>
  );
}

function DashboardPage({ agents, onAgentClick, onQuarantine }: { agents: Agent[]; onAgentClick: (a: Agent) => void; onQuarantine: (id: string) => void }) {
  return (
    <div className="space-y-5 animate-fade-in">
      <KpiCards agents={agents} />
      <div className="grid grid-cols-1 xl:grid-cols-3 gap-5">
        <div className="xl:col-span-2"><GovernanceHeartbeat /></div>
        <div><CitadelLens /></div>
      </div>
      <SwarmOverview agents={agents} onAgentClick={onAgentClick} onQuarantine={onQuarantine} />
      <AuditStream />
    </div>
  );
}

/* ═══════════════════════════════════════════
   PAGE: AGENT SWARM (Full)
   ═══════════════════════════════════════════ */
function AgentsPage({ agents, onAgentClick, onQuarantine }: { agents: Agent[]; onAgentClick: (a: Agent) => void; onQuarantine: (id: string) => void }) {
  return (
    <div className="space-y-5 animate-fade-in">
      <div className="flex items-center justify-between">
        <div><h2 className="font-display text-xl font-bold text-slate-900">Agent Swarm</h2><p className="font-mono text-xs text-slate-500 mt-1">Full registry with sparkline activity.</p></div>
      </div>
      <SwarmOverview agents={agents} onAgentClick={onAgentClick} onQuarantine={onQuarantine} />
    </div>
  );
}

/* ═══════════════════════════════════════════
   PAGE: PLACEHOLDER
   ═══════════════════════════════════════════ */
/* ═══════════════════════════════════════════
   PAGE: APPROVALS (Full Governance Queue)
   ═══════════════════════════════════════════ */
interface ApprovalRequest {
  id: string; agent: string; action: string; risk: "low" | "medium" | "high" | "critical";
  requestedBy: string; timestamp: string; status: "pending" | "approved" | "denied" | "escalated";
  reason: string; framework: string; autoBlocked: boolean;
}

const INITIAL_APPROVALS: ApprovalRequest[] = [
  { id: "apr1", agent: "ghost-v1", action: "aws.iam_role_attach:AdminAccess", risk: "critical", requestedBy: "ghost-v1", timestamp: "14:31:22", status: "pending", reason: "Agent requesting full admin role attachment to EC2 instance profile. Privilege escalation risk.", framework: "SOC2 CC6.3", autoBlocked: true },
  { id: "apr2", agent: "cipher-v1", action: "db.customer_table.export:all_rows", risk: "high", requestedBy: "cipher-v1", timestamp: "14:28:45", status: "pending", reason: "Bulk export of customer PII detected. GDPR Article 25 violation if unapproved.", framework: "GDPR Art.25", autoBlocked: true },
  { id: "apr3", agent: "nova-v2", action: "stripe.refund_create:$4,200", risk: "medium", requestedBy: "nova-v2", timestamp: "14:25:10", status: "pending", reason: "Refund exceeds $1,000 policy threshold. Customer dispute #4921.", framework: "SOC2 PI1.3", autoBlocked: true },
  { id: "apr4", agent: "atlas-v2", action: "openai.file_upload:customer_chats.json", risk: "high", requestedBy: "atlas-v2", timestamp: "14:20:33", status: "pending", reason: "Uploading customer conversation data to third-party LLM. Data residency risk.", framework: "HIPAA 164.514", autoBlocked: true },
  { id: "apr5", agent: "forge-v1", action: "s3.bucket_delete:production-backups", risk: "critical", requestedBy: "forge-v1", timestamp: "14:15:08", status: "pending", reason: "Destruction guard triggered. Bucket contains 7-year audit trail backups.", framework: "SOC2 CC7.2", autoBlocked: true },
  { id: "apr6", agent: "drift-v2", action: "slack.channel_join:#executive-finance", risk: "medium", requestedBy: "drift-v2", timestamp: "14:10:55", status: "approved", reason: "Agent granted read-only access to public finance channel for reporting.", framework: "SOC2 CC6.1", autoBlocked: false },
  { id: "apr7", agent: "sentinel-v3", action: "pagerduty.incident_create:sev-2", risk: "low", requestedBy: "sentinel-v3", timestamp: "13:58:12", status: "approved", reason: "Automated incident response for elevated error rate on nova-v2.", framework: "NIST RS.AN-1", autoBlocked: false },
  { id: "apr8", agent: "ghost-v1", action: "api.rate_limit_override:5000rpm", risk: "high", requestedBy: "ghost-v1", timestamp: "13:45:30", status: "denied", reason: "Rate limit override request denied. Agent already at 98% token budget.", framework: "SOC2 CC8.1", autoBlocked: true },
  { id: "apr9", agent: "cipher-v1", action: "db.phi_query:patient_records_2024", risk: "critical", requestedBy: "cipher-v1", timestamp: "13:30:18", status: "escalated", reason: "HIPAA §164.502 access to PHI. Escalated to Chief Compliance Officer.", framework: "HIPAA 164.502", autoBlocked: true },
  { id: "apr10", agent: "atlas-v2", action: "github.repo_fork:private-compliance-docs", risk: "medium", requestedBy: "atlas-v2", timestamp: "13:15:42", status: "denied", reason: "Forking of private compliance repository blocked. Insider threat protocol.", framework: "SOC2 CC6.2", autoBlocked: true },
];

function ApprovalsPage() {
  const { role, permissions } = useRBAC();
  const [requests, setRequests] = useState(INITIAL_APPROVALS);
  const [filter, setFilter] = useState<"all" | "pending" | "approved" | "denied" | "escalated">("pending");
  const [selected, setSelected] = useState<ApprovalRequest | null>(null);

  const canDecide = permissions.canEdit;
  const filtered = requests.filter(r => filter === "all" ? true : r.status === filter);
  const counts = {
    all: requests.length,
    pending: requests.filter(r => r.status === "pending").length,
    approved: requests.filter(r => r.status === "approved").length,
    denied: requests.filter(r => r.status === "denied").length,
    escalated: requests.filter(r => r.status === "escalated").length,
  };

  const handleDecision = (id: string, decision: "approved" | "denied" | "escalated") => {
    setRequests(prev => prev.map(r => r.id === id ? { ...r, status: decision } : r));
    setSelected(null);
  };

  const riskColor = (r: string) => {
    if (r === "critical") return "bg-red-50 text-red-700 border-red-200";
    if (r === "high") return "bg-amber-50 text-amber-700 border-amber-200";
    if (r === "medium") return "bg-blue-50 text-blue-700 border-blue-200";
    return "bg-slate-50 text-slate-600 border-slate-200";
  };
  const statusDot = (s: string) => {
    if (s === "pending") return "bg-amber-400 animate-pulse-amber";
    if (s === "approved") return "bg-emerald-400";
    if (s === "denied") return "bg-red-400";
    return "bg-purple-400";
  };

  return (
    <div className="animate-fade-in space-y-5">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="font-display text-xl font-bold text-slate-900">Approval Queue</h2>
          <p className="font-mono text-xs text-slate-500 mt-1">Governance decisions requiring human review.</p>
        </div>
        <div className="flex items-center gap-2">
          {counts.pending > 0 && (
            <span className="flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-amber-50 border border-amber-200 text-amber-700 font-mono text-[10px] font-bold uppercase">
              <AlertTriangle size={10} /> {counts.pending} pending
            </span>
          )}
        </div>
      </div>

      {/* Filter tabs */}
      <div className="flex items-center gap-0.5 bg-slate-100/60 rounded-lg p-0.5 w-fit">
        {(["all", "pending", "approved", "denied", "escalated"] as const).map(f => (
          <button key={f} onClick={() => setFilter(f)}
            className={`px-3 py-1.5 rounded-md font-mono text-[10px] font-bold transition-all ${filter === f ? "bg-white text-slate-700 shadow-sm border border-slate-200" : "text-slate-400 hover:text-slate-600"}`}>
            {f.toUpperCase()} ({counts[f]})
          </button>
        ))}
      </div>

      {/* Queue */}
      <div className="space-y-2">
        {filtered.map(req => (
          <div key={req.id}
            onClick={() => setSelected(req)}
            className={`glass-blueprint rounded-xl p-4 transition-all cursor-pointer hover:shadow-md ${
              req.status === "pending" ? "border-l-2 border-l-amber-400" :
              req.status === "approved" ? "border-l-2 border-l-emerald-400" :
              req.status === "denied" ? "border-l-2 border-l-red-400" :
              "border-l-2 border-l-purple-400"
            }`}>
            <div className="flex items-start justify-between gap-4">
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 mb-1">
                  <div className={`w-1.5 h-1.5 rounded-full ${statusDot(req.status)}`} />
                  <span className="font-mono text-xs font-bold text-slate-800">{req.agent}</span>
                  <span className="font-mono text-[9px] text-slate-400">{req.timestamp}</span>
                  {req.autoBlocked && (
                    <span className="font-mono text-[8px] px-1.5 py-0.5 rounded bg-red-50 text-red-500 border border-red-200 uppercase">auto-blocked</span>
                  )}
                </div>
                <p className="font-mono text-sm text-slate-700 font-medium">{req.action}</p>
                <p className="font-mono text-[11px] text-slate-500 mt-1">{req.reason}</p>
                <div className="flex items-center gap-2 mt-2">
                  <span className={`px-2 py-0.5 rounded text-[9px] font-bold uppercase border ${riskColor(req.risk)}`}>{req.risk}</span>
                  <span className="font-mono text-[9px] text-slate-400">{req.framework}</span>
                  <span className={`px-2 py-0.5 rounded-full text-[9px] font-bold uppercase border ${req.status === "pending" ? "bg-amber-50 text-amber-600 border-amber-200" : req.status === "approved" ? "bg-emerald-50 text-emerald-600 border-emerald-200" : req.status === "denied" ? "bg-red-50 text-red-600 border-red-200" : "bg-purple-50 text-purple-600 border-purple-200"}`}>{req.status}</span>
                </div>
              </div>
              {/* Actions */}
              {req.status === "pending" && canDecide && (
                <div className="flex items-center gap-1.5 shrink-0">
                  <button onClick={e => { e.stopPropagation(); handleDecision(req.id, "approved"); }}
                    className="px-3 py-1.5 rounded-lg bg-emerald-50 text-emerald-600 border border-emerald-200 font-mono text-[10px] font-bold uppercase hover:bg-emerald-100 transition-all">
                    <CheckCircle2 size={12} className="inline mr-1" />Approve
                  </button>
                  <button onClick={e => { e.stopPropagation(); handleDecision(req.id, "denied"); }}
                    className="px-3 py-1.5 rounded-lg bg-red-50 text-red-500 border border-red-200 font-mono text-[10px] font-bold uppercase hover:bg-red-100 transition-all">
                    <Ban size={12} className="inline mr-1" />Deny
                  </button>
                  <button onClick={e => { e.stopPropagation(); handleDecision(req.id, "escalated"); }}
                    className="px-3 py-1.5 rounded-lg bg-purple-50 text-purple-600 border border-purple-200 font-mono text-[10px] font-bold uppercase hover:bg-purple-100 transition-all">
                    <ChevronUp size={12} className="inline mr-1" />Escalate
                  </button>
                </div>
              )}
            </div>
          </div>
        ))}
        {filtered.length === 0 && (
          <div className="glass-blueprint rounded-xl p-8 text-center">
            <CheckCircle2 size={32} className="text-emerald-400 mx-auto mb-2" />
            <p className="font-display text-sm font-bold text-slate-600">Queue Clear</p>
            <p className="font-mono text-[10px] text-slate-400">No {filter} approvals at this time.</p>
          </div>
        )}
      </div>

      {/* Detail Modal */}
      {selected && (
        <div className="fixed inset-0 z-50 flex items-center justify-center">
          <div className="absolute inset-0 bg-black/25 backdrop-blur-sm" onClick={() => setSelected(null)} />
          <div className="relative z-10 w-full max-w-lg mx-4 glass-blueprint rounded-2xl shadow-2xl animate-fade-in overflow-hidden">
            <div className="h-14 flex items-center justify-between px-6 border-b border-slate-200/60">
              <div className="flex items-center gap-3">
                <span className={`w-2.5 h-2.5 rounded-full ${statusDot(selected.status)}`} />
                <h3 className="font-display font-bold text-slate-900">Approval Request</h3>
              </div>
              <button onClick={() => setSelected(null)} className="p-1.5 rounded-lg hover:bg-slate-100 text-slate-400"><X size={16} /></button>
            </div>
            <div className="p-6 space-y-4">
              <div className="grid grid-cols-2 gap-3">
                <div className="p-3 rounded-xl bg-slate-50 border border-slate-200/60">
                  <p className="font-mono text-[9px] text-slate-500 uppercase">Agent</p>
                  <p className="font-mono text-sm font-bold text-slate-800 mt-1">{selected.agent}</p>
                </div>
                <div className="p-3 rounded-xl bg-slate-50 border border-slate-200/60">
                  <p className="font-mono text-[9px] text-slate-500 uppercase">Risk Level</p>
                  <p className="font-mono text-sm font-bold text-slate-800 mt-1">{selected.risk.toUpperCase()}</p>
                </div>
                <div className="p-3 rounded-xl bg-slate-50 border border-slate-200/60">
                  <p className="font-mono text-[9px] text-slate-500 uppercase">Framework</p>
                  <p className="font-mono text-sm font-bold text-slate-800 mt-1">{selected.framework}</p>
                </div>
                <div className="p-3 rounded-xl bg-slate-50 border border-slate-200/60">
                  <p className="font-mono text-[9px] text-slate-500 uppercase">Auto-Blocked</p>
                  <p className="font-mono text-sm font-bold mt-1">{selected.autoBlocked ? <span className="text-red-600">YES</span> : <span className="text-emerald-600">NO</span>}</p>
                </div>
              </div>
              <div className="p-3 rounded-xl bg-slate-50 border border-slate-200/60">
                <p className="font-mono text-[9px] text-slate-500 uppercase">Action</p>
                <p className="font-mono text-sm font-bold text-slate-800 mt-1">{selected.action}</p>
              </div>
              <div className="p-3 rounded-xl bg-slate-50 border border-slate-200/60">
                <p className="font-mono text-[9px] text-slate-500 uppercase">Reason</p>
                <p className="font-mono text-xs text-slate-700 mt-1">{selected.reason}</p>
              </div>
              {selected.status === "pending" && canDecide && (
                <div className="flex gap-2 pt-2">
                  <button onClick={() => handleDecision(selected.id, "approved")}
                    className="flex-1 py-2.5 rounded-xl bg-emerald-50 text-emerald-700 border border-emerald-200 font-display text-xs font-bold uppercase hover:bg-emerald-100 transition-all"><CheckCircle2 size={14} className="inline mr-1" />Approve</button>
                  <button onClick={() => handleDecision(selected.id, "denied")}
                    className="flex-1 py-2.5 rounded-xl bg-red-50 text-red-600 border border-red-200 font-display text-xs font-bold uppercase hover:bg-red-100 transition-all"><Ban size={14} className="inline mr-1" />Deny</button>
                  <button onClick={() => handleDecision(selected.id, "escalated")}
                    className="flex-1 py-2.5 rounded-xl bg-purple-50 text-purple-700 border border-purple-200 font-display text-xs font-bold uppercase hover:bg-purple-100 transition-all"><ChevronUp size={14} className="inline mr-1" />Escalate</button>
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

function PlaceholderPage({ title, desc }: { title: string; desc: string }) {
  const { role } = useRBAC();
  return (
    <div className="animate-fade-in">
      <div className="mb-6"><h2 className="font-display text-xl font-bold text-slate-900">{title}</h2><p className="font-mono text-xs text-slate-500 mt-1">{desc}</p></div>
      <div className="glass-blueprint p-12 text-center glow-cluely-subtle">
        <Hexagon size={40} className="text-slate-300 mx-auto mb-3" />
        <p className="font-display text-base font-bold text-slate-500">{title}</p>
        <p className="font-mono text-xs text-slate-400 mt-1">{role === "auditor" ? "Read-only. No modifications permitted." : "Under development."}</p>
      </div>
    </div>
  );
}

/* ═══════════════════════════════════════════
   MAIN APP
   ═══════════════════════════════════════════ */
export default function App() {
  const [activePage, setActivePage] = useState("dashboard");
  const [killSwitchActive, setKillSwitchActive] = useState(false);
  const [agents, setAgents] = useState(INITIAL_AGENTS);
  const [selectedAgent, setSelectedAgent] = useState<Agent | null>(null);

  const handleQuarantine = (id: string) => {
    setAgents(prev => prev.map(a => a.id === id ? { ...a, quarantined: !a.quarantined, actionsToday: a.quarantined ? (a.id === "a5" ? 18700 : 8000) : 0 } : a));
  };

  const renderPage = () => {
    switch (activePage) {
      case "dashboard": return <DashboardPage agents={agents} onAgentClick={setSelectedAgent} onQuarantine={handleQuarantine} />;
      case "agents": return <AgentsPage agents={agents} onAgentClick={setSelectedAgent} onQuarantine={handleQuarantine} />;
      case "connectors": return <ConnectorsPage />;
      case "policies": return <PoliciesPage />;
      case "reports": return <ReportsPage agents={agents} />;
      case "approvals": return <ApprovalsPage />;
      case "audit": return <div className="animate-fade-in"><AuditStream /></div>;
      case "lens": return <div className="animate-fade-in"><CitadelLens /></div>;
      case "incidents": return <PlaceholderPage title="Incidents" desc="Security incident tracking." />;
      case "settings": return <SettingsPage />;
      default: return <DashboardPage agents={agents} onAgentClick={setSelectedAgent} onQuarantine={handleQuarantine} />;
    }
  };

  return (
    <RBACProvider>
      <div className="min-h-screen relative">
        <div className="fixed inset-0 bg-grid-blueprint opacity-50 pointer-events-none" />
        <SlimSidebar activePage={activePage} onNavigate={setActivePage} />
        <div style={{ marginLeft: 60 }}>
          <CommandBar killSwitchActive={killSwitchActive} onToggleKillSwitch={() => setKillSwitchActive(!killSwitchActive)} onNavigate={setActivePage} activePage={activePage} />
          <main className="p-5 pb-24 relative z-10 max-w-[1440px] mx-auto">{renderPage()}</main>
        </div>
        {selectedAgent && <AgentDrawer agent={selectedAgent} onClose={() => setSelectedAgent(null)} onQuarantine={handleQuarantine} />}
        <QuickActionsDock onAddAgent={() => setActivePage("connectors")} onNewPolicy={() => setActivePage("policies")} onRunCheck={() => setActivePage("reports")} />
      </div>
    </RBACProvider>
  );
}
