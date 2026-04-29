import { AlertTriangle, ArrowUpRight, BarChart3, DollarSign, Shield, Zap } from 'lucide-react';

const budgets = [
  {
    id: 'tenant',
    name: 'Enterprise LLM Cap',
    scope: 'tenant:acme',
    period: 'monthly',
    action: 'block',
    amount: 250000,
    spend: 92500,
  },
  {
    id: 'agent',
    name: 'Research Agent Guardrail',
    scope: 'agent:research-analyst',
    period: 'daily',
    action: 'require_approval',
    amount: 15000,
    spend: 11200,
  },
];

function formatCents(cents: number) {
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
  }).format(cents / 100);
}

export default function Billing() {
  return (
    <div className="p-8 space-y-8 animate-in fade-in duration-500">
      <div>
        <h1 className="text-2xl font-black text-white">Billing, Quotas & Budgets</h1>
        <p className="text-sm text-slate-500 mt-1">Manage subscription limits and LLM spend controls.</p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <div className="p-6 rounded-2xl bg-slate-900/50 border border-slate-800 backdrop-blur-sm">
          <div className="flex items-center justify-between mb-4">
            <div className="p-2 rounded-lg bg-indigo-500/10 text-indigo-400">
              <Zap size={20} />
            </div>
            <span className="px-2 py-1 rounded-lg text-[10px] font-bold uppercase bg-emerald-500/10 text-emerald-500">Active</span>
          </div>
          <h3 className="text-sm font-medium text-slate-400">Current Plan</h3>
          <p className="text-2xl font-bold text-white capitalize mt-1">Enterprise</p>
        </div>

        <div className="p-6 rounded-2xl bg-slate-900/50 border border-slate-800 backdrop-blur-sm">
          <div className="flex items-center justify-between mb-4">
            <div className="p-2 rounded-lg bg-emerald-500/10 text-emerald-400">
              <DollarSign size={20} />
            </div>
            <span className="text-xs font-semibold text-slate-500">This month</span>
          </div>
          <h3 className="text-sm font-medium text-slate-400">LLM Spend</h3>
          <p className="text-2xl font-bold text-white mt-1">{formatCents(92500)}</p>
        </div>

        <div className="p-6 rounded-2xl bg-indigo-600/10 border border-indigo-500/20 backdrop-blur-sm relative overflow-hidden group">
          <div className="relative z-10">
            <h3 className="text-lg font-bold text-white mb-2">Budget Enforcement</h3>
            <p className="text-slate-400 text-sm max-w-md mb-6">
              Pre-request checks can block, throttle, or require approval before LLM spend happens.
            </p>
            <button className="px-6 py-2 bg-indigo-600 hover:bg-indigo-500 text-white rounded-lg font-medium transition-all flex items-center gap-2 group-hover:gap-3">
              Manage Budgets
              <ArrowUpRight size={18} />
            </button>
          </div>
          <div className="absolute -right-8 -bottom-8 text-indigo-500/10 transform rotate-12 group-hover:scale-110 transition-transform duration-700">
            <Shield size={200} />
          </div>
        </div>
      </div>

      <div className="p-8 rounded-3xl bg-slate-900/50 border border-slate-800">
        <div className="flex items-center gap-3 mb-8">
          <div className="p-2 rounded-lg bg-emerald-500/10 text-emerald-400">
            <BarChart3 size={20} />
          </div>
          <h3 className="text-lg font-bold text-white">Consumption Tracking</h3>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div>
            <p className="text-xs uppercase tracking-wide text-slate-500">API calls</p>
            <p className="text-xl font-semibold text-white mt-1">8,420 <span className="text-sm text-slate-500">/ 10,000</span></p>
          </div>
          <div>
            <p className="text-xs uppercase tracking-wide text-slate-500">Active agents</p>
            <p className="text-xl font-semibold text-white mt-1">12 <span className="text-sm text-slate-500">/ 25</span></p>
          </div>
          <div>
            <p className="text-xs uppercase tracking-wide text-slate-500">Approvals</p>
            <p className="text-xl font-semibold text-white mt-1">37 <span className="text-sm text-slate-500">/ 500</span></p>
          </div>
        </div>
      </div>

      <div className="p-8 rounded-3xl bg-slate-900/50 border border-slate-800">
        <div className="flex items-center gap-3 mb-8">
          <div className="p-2 rounded-lg bg-amber-500/10 text-amber-400">
            <AlertTriangle size={20} />
          </div>
          <h3 className="text-lg font-bold text-white">Cost Budgets</h3>
        </div>
        <div className="space-y-4">
          {budgets.map((budget) => {
            const usage = Math.min(100, Math.round((budget.spend / budget.amount) * 100));
            return (
              <div key={budget.id} className="border border-slate-800 rounded-xl p-4">
                <div className="flex items-center justify-between gap-4">
                  <div>
                    <p className="font-semibold text-white">{budget.name}</p>
                    <p className="text-xs text-slate-500 mt-1">
                      {budget.scope} - {budget.period} - {budget.action}
                    </p>
                  </div>
                  <p className="text-sm font-semibold text-white">{formatCents(budget.amount)}</p>
                </div>
                <div className="mt-4 h-2 rounded-full bg-slate-800 overflow-hidden">
                  <div className="h-full bg-emerald-500" style={{ width: `${usage}%` }} />
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
