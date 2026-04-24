import React, { useState } from 'react';
import { 
  Shield, 
  Activity as ActivityIcon, 
  AlertCircle, 
  TrendingUp,
  Fingerprint,
  Zap
} from 'lucide-react';
import { 
  ActivityStream, 
  ApprovalQueue, 
  KillSwitch,
  ActivityEvent,
  ApprovalRequest 
} from '@citadel/widget-library';

// Mock Data
const MOCK_EVENTS: ActivityEvent[] = [
  { id: '1', timestamp: new Date().toISOString(), severity: 'CRITICAL', type: 'token.revoked', summary: 'Production Token Revoked', agentId: 'nova-v2', actionable: true },
  { id: '2', timestamp: new Date(Date.now() - 1000 * 60 * 15).toISOString(), severity: 'HIGH', type: 'execution.blocked', summary: 'S3 Delete Blocked by Policy', agentId: 'forge-v1', actionable: true },
  { id: '3', timestamp: new Date(Date.now() - 1000 * 60 * 45).toISOString(), severity: 'MEDIUM', type: 'decision.created', summary: 'Manual Approval Required', agentId: 'cipher-v1', actionable: true },
  { id: '4', timestamp: new Date(Date.now() - 1000 * 60 * 120).toISOString(), severity: 'LOW', type: 'execution.allowed', summary: 'Database Write Permitted', agentId: 'nova-v2', actionable: false },
];

const MOCK_APPROVALS: ApprovalRequest[] = [
  { 
    id: 'app_1', 
    action: 'stripe.refund_create', 
    resource: 'ch_3Nabc...', 
    actorId: 'support-agent', 
    timestamp: new Date().toISOString(), 
    riskScore: 0.85, 
    reason: 'High-value refund requested by autonomous agent without customer ticket link.' 
  },
  { 
    id: 'app_2', 
    action: 'github.repo_delete', 
    resource: 'citadel-sdk-internal', 
    actorId: 'cleaner-bot', 
    timestamp: new Date(Date.now() - 1000 * 60 * 10).toISOString(), 
    riskScore: 0.98, 
    reason: 'Destructive action on critical infrastructure repository.' 
  },
];

export const Overview: React.FC = () => {
  const [isLocked, setIsLocked] = useState(false);

  return (
    <div className="space-y-8 animate-in fade-in duration-700">
      {/* Hero Stats */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {[
          { label: 'Posture Score', value: '94', icon: Shield, color: 'text-emerald-500', trend: '+2%' },
          { label: 'Active Policies', value: '128', icon: Fingerprint, color: 'text-blue-500', trend: 'Stable' },
          { label: 'Blocked Actions', value: '42', icon: AlertCircle, color: 'text-orange-500', trend: '+12' },
          { label: 'Audit Velocity', value: '1.2k', icon: TrendingUp, color: 'text-indigo-500', trend: 'per/hr' },
        ].map((stat, i) => (
          <div key={i} className="p-6 rounded-3xl bg-slate-900/40 border border-slate-800/50 backdrop-blur-sm group hover:border-slate-700 transition-all">
            <div className="flex items-center justify-between mb-4">
              <div className={cn("p-2 rounded-xl bg-slate-800/50 border border-slate-700/50", stat.color)}>
                <stat.icon size={20} />
              </div>
              <span className="text-[10px] font-bold text-slate-500 uppercase tracking-widest">{stat.trend}</span>
            </div>
            <p className="text-2xl font-black text-white tabular-nums">{stat.value}</p>
            <p className="text-xs font-medium text-slate-500 mt-1">{stat.label}</p>
          </div>
        ))}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
        {/* Left Column: Activity & Approvals */}
        <div className="lg:col-span-8 space-y-8">
          <div className="p-1 rounded-[2rem] bg-gradient-to-b from-slate-800/50 to-transparent">
            <div className="p-6 rounded-[1.9rem] bg-slate-950/90 backdrop-blur-xl">
              <ApprovalQueue 
                requests={MOCK_APPROVALS} 
                onApprove={(id) => console.log('Approved', id)}
                onReject={(id) => console.log('Rejected', id)}
              />
            </div>
          </div>

          <div className="p-6 rounded-3xl bg-slate-900/20 border border-slate-800/30">
            <ActivityStream events={MOCK_EVENTS} />
          </div>
        </div>

        {/* Right Column: Controls & Context */}
        <div className="lg:col-span-4 space-y-8">
          <KillSwitch 
            isActive={isLocked} 
            onToggle={async (state) => {
              await new Promise(r => setTimeout(r, 1000));
              setIsLocked(state);
            }} 
          />

          <div className="p-6 rounded-3xl bg-slate-900/40 border border-slate-800/50 backdrop-blur-sm">
            <div className="flex items-center gap-2 mb-6">
              <Zap size={18} className="text-indigo-400" />
              <h3 className="text-sm font-bold text-slate-200 uppercase tracking-tight">Active Integrations</h3>
            </div>
            <div className="space-y-4">
              {[
                { name: 'Stripe Gateway', status: 'Protected', color: 'bg-emerald-500' },
                { name: 'GitHub CI/CD', status: 'Protected', color: 'bg-emerald-500' },
                { name: 'AWS S3 Core', status: 'Monitoring', color: 'bg-blue-500' },
                { name: 'Slack Bot', status: 'Bypassed', color: 'bg-slate-500' },
              ].map((item, i) => (
                <div key={i} className="flex items-center justify-between p-3 rounded-2xl bg-slate-950/50 border border-slate-800/50">
                  <span className="text-xs font-medium text-slate-300">{item.name}</span>
                  <div className="flex items-center gap-2">
                    <span className="text-[10px] font-bold text-slate-500 uppercase tracking-tight">{item.status}</span>
                    <div className={cn("w-2 h-2 rounded-full", item.color)} />
                  </div>
                </div>
              ))}
            </div>
            <button className="w-full mt-6 py-3 rounded-xl bg-slate-800 hover:bg-slate-700 text-xs font-bold text-slate-300 transition-all">
              Manage All Connections
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

// Helper for classes (re-defined here since we are in a single file)
function cn(...inputs: any[]) {
  return inputs.filter(Boolean).join(' ');
}
