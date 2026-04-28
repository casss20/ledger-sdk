import { useState } from 'react';
import { AlertTriangle, ArrowUpRight, BarChart3, DollarSign, Shield, Zap } from 'lucide-react';

import { useBilling } from '../hooks/useBilling';

function formatCents(cents = 0) {
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
  }).format(cents / 100);
}

export default function Billing() {
  const { summary, topUpBudget } = useBilling();
  const [selectedBudgetId, setSelectedBudgetId] = useState<string | null>(null);
  const [topUpDollars, setTopUpDollars] = useState('');
  const [topUpReason, setTopUpReason] = useState('');
  const [topUpError, setTopUpError] = useState<string | null>(null);
  const [topUpSuccess, setTopUpSuccess] = useState(false);

  const data = summary.data;
  const costControls = data?.cost_controls;
  const budgets = costControls?.budgets || [];
  const monthlySpend = costControls?.monthly_spend_cents || 0;
  const largestBudget = budgets[0];
  const budgetUsage = largestBudget
    ? Math.min(100, Math.round((monthlySpend / largestBudget.amount_cents) * 100))
    : 0;
  const selectedBudget = budgets.find((budget) => budget.budget_id === selectedBudgetId);
  const parsedTopUpCents = Math.round(Number(topUpDollars) * 100);
  const validTopUpCents =
    Number.isFinite(parsedTopUpCents) && parsedTopUpCents > 0 ? parsedTopUpCents : 0;

  async function submitTopUp() {
    if (!selectedBudget) return;
    setTopUpError(null);
    if (selectedBudget.scope_type !== 'tenant') {
      setTopUpError('MVP top-up only supports tenant-level budgets.');
      return;
    }
    if (validTopUpCents <= 0) {
      setTopUpError('Enter a positive top-up amount.');
      return;
    }
    if (!topUpReason.trim()) {
      setTopUpError('A reason is required for audit.');
      return;
    }
    try {
      await topUpBudget.mutateAsync({
        budgetId: selectedBudget.budget_id,
        amount_cents: validTopUpCents,
        reason: topUpReason.trim(),
      });
      setSelectedBudgetId(null);
      setTopUpDollars('');
      setTopUpReason('');
      setTopUpSuccess(true);
    } catch (error) {
      setTopUpError(error instanceof Error ? error.message : 'Top-up failed.');
    }
  }

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
          <p className="text-2xl font-bold text-white capitalize mt-1">{data?.plan || 'Enterprise'}</p>
        </div>

        <div className="p-6 rounded-2xl bg-slate-900/50 border border-slate-800 backdrop-blur-sm">
          <div className="flex items-center justify-between mb-4">
            <div className="p-2 rounded-lg bg-emerald-500/10 text-emerald-400">
              <DollarSign size={20} />
            </div>
            <span className="text-xs font-semibold text-slate-500">This month</span>
          </div>
          <h3 className="text-sm font-medium text-slate-400">LLM Spend</h3>
          <p className="text-2xl font-bold text-white mt-1">{formatCents(monthlySpend)}</p>
        </div>

        <div className="p-6 rounded-2xl bg-indigo-600/10 border border-indigo-500/20 backdrop-blur-sm relative overflow-hidden group">
          <div className="relative z-10">
            <h3 className="text-lg font-bold text-white mb-2">Budget Enforcement</h3>
            <p className="text-slate-400 text-sm max-w-md mb-6">Pre-request checks can block, throttle, or require approval before LLM spend happens.</p>
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
        {summary.isLoading ? (
          <p className="text-sm text-slate-500">Loading billing data...</p>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div>
              <p className="text-xs uppercase tracking-wide text-slate-500">API calls</p>
              <p className="text-xl font-semibold text-white mt-1">
                {data?.usage.api_calls ?? 0}
                <span className="text-sm text-slate-500"> / {data?.limits.api_calls ?? 'unlimited'}</span>
              </p>
            </div>
            <div>
              <p className="text-xs uppercase tracking-wide text-slate-500">Active agents</p>
              <p className="text-xl font-semibold text-white mt-1">
                {data?.usage.active_agents ?? 0}
                <span className="text-sm text-slate-500"> / {data?.limits.agents ?? 'unlimited'}</span>
              </p>
            </div>
            <div>
              <p className="text-xs uppercase tracking-wide text-slate-500">Approvals</p>
              <p className="text-xl font-semibold text-white mt-1">
                {data?.usage.approval_requests ?? 0}
                <span className="text-sm text-slate-500"> / {data?.limits.approvals ?? 'unlimited'}</span>
              </p>
            </div>
          </div>
        )}
      </div>

      <div className="p-8 rounded-3xl bg-slate-900/50 border border-slate-800">
        <div className="flex items-center justify-between mb-8">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-lg bg-amber-500/10 text-amber-400">
              <AlertTriangle size={20} />
            </div>
            <h3 className="text-lg font-bold text-white">Cost Budgets</h3>
          </div>
          {largestBudget && (
            <span className="text-xs font-semibold text-slate-500">{budgetUsage}% of first active budget</span>
          )}
        </div>
        {budgets.length === 0 ? (
          <p className="text-sm text-slate-500">No LLM budgets configured yet.</p>
        ) : (
          <div className="space-y-4">
            {budgets.map((budget) => {
              const spend = budget.current_spend_cents ?? monthlySpend;
              const usage = Math.min(100, Math.round((spend / budget.amount_cents) * 100));
              return (
                <div key={budget.budget_id} className="border border-slate-800 rounded-xl p-4">
                  <div className="flex items-center justify-between gap-4">
                    <div>
                      <p className="font-semibold text-white">{budget.name}</p>
                      <p className="text-xs text-slate-500 mt-1">
                        {budget.scope_type}:{budget.scope_value} - {budget.reset_period} - {budget.enforcement_action}
                      </p>
                      <p className="text-xs text-slate-500 mt-1">
                        Remaining {formatCents(budget.remaining_cents ?? Math.max(0, budget.amount_cents - spend))}
                      </p>
                    </div>
                    <div className="text-right">
                      <p className="text-sm font-semibold text-white">{formatCents(budget.amount_cents)}</p>
                      {budget.scope_type === 'tenant' ? (
                        <button
                          className="mt-2 px-3 py-1.5 rounded-lg bg-amber-500/10 text-amber-300 text-xs font-semibold border border-amber-500/20 hover:bg-amber-500/20"
                          onClick={() => {
                            setSelectedBudgetId(budget.budget_id);
                            setTopUpError(null);
                            setTopUpSuccess(false);
                          }}
                        >
                          Top up
                        </button>
                      ) : (
                        <span className="mt-2 block text-[10px] uppercase tracking-wide text-slate-600">Top-up deferred</span>
                      )}
                    </div>
                  </div>
                  <div className="mt-4 h-2 rounded-full bg-slate-800 overflow-hidden">
                    <div className="h-full bg-emerald-500" style={{ width: `${usage}%` }} />
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>

      {topUpSuccess && (
        <p className="text-sm text-emerald-400">Budget top-up recorded and audit trail updated.</p>
      )}

      {selectedBudget && (
        <div className="p-8 rounded-3xl bg-slate-900/50 border border-slate-800">
          <div className="flex items-start justify-between gap-6 mb-6">
            <div>
              <h3 className="text-lg font-bold text-white">Top Up Tenant Budget</h3>
              <p className="text-sm text-slate-500 mt-1">
                Add budget capacity with an audited executive adjustment.
              </p>
            </div>
            <button
              className="text-sm text-slate-500 hover:text-white"
              onClick={() => setSelectedBudgetId(null)}
            >
              Cancel
            </button>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
            <div>
              <p className="text-xs uppercase tracking-wide text-slate-500">Current Budget</p>
              <p className="text-xl font-semibold text-white mt-1">{formatCents(selectedBudget.amount_cents)}</p>
            </div>
            <div>
              <p className="text-xs uppercase tracking-wide text-slate-500">Current Spend</p>
              <p className="text-xl font-semibold text-white mt-1">{formatCents(selectedBudget.current_spend_cents ?? monthlySpend)}</p>
            </div>
            <div>
              <p className="text-xs uppercase tracking-wide text-slate-500">After Top-up</p>
              <p className="text-xl font-semibold text-white mt-1">
                {formatCents(selectedBudget.amount_cents + validTopUpCents)}
              </p>
            </div>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <label className="md:col-span-1">
              <span className="text-xs uppercase tracking-wide text-slate-500">Amount</span>
              <input
                className="mt-2 w-full rounded-xl bg-slate-950 border border-slate-800 px-4 py-3 text-white outline-none focus:border-amber-500"
                inputMode="decimal"
                placeholder="5000.00"
                value={topUpDollars}
                onChange={(event) => setTopUpDollars(event.target.value)}
              />
            </label>
            <label className="md:col-span-2">
              <span className="text-xs uppercase tracking-wide text-slate-500">Reason</span>
              <textarea
                className="mt-2 w-full rounded-xl bg-slate-950 border border-slate-800 px-4 py-3 text-white outline-none focus:border-amber-500"
                placeholder="Required for audit, for example: temporary expansion for Q2 evaluation workload"
                rows={3}
                value={topUpReason}
                onChange={(event) => setTopUpReason(event.target.value)}
              />
            </label>
          </div>
          {topUpError && <p className="mt-4 text-sm text-red-400">{topUpError}</p>}
          <button
            className="mt-6 px-6 py-3 bg-amber-500 hover:bg-amber-400 disabled:bg-slate-800 disabled:text-slate-500 text-slate-950 rounded-xl font-semibold transition-colors"
            disabled={topUpBudget.isPending}
            onClick={submitTopUp}
          >
            {topUpBudget.isPending ? 'Recording top-up...' : 'Record Top-up'}
          </button>
        </div>
      )}
    </div>
  );
}
