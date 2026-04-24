import { Zap, Shield, BarChart3, ArrowUpRight } from 'lucide-react';

export default function Billing() {
  return (
    <div className="p-8 space-y-8 animate-in fade-in duration-500">
      <div>
        <h1 className="text-2xl font-black text-white">Billing & Quotas</h1>
        <p className="text-sm text-slate-500 mt-1">Manage your subscription and monitor governance consumption.</p>
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

        <div className="col-span-2 p-6 rounded-2xl bg-indigo-600/10 border border-indigo-500/20 backdrop-blur-sm relative overflow-hidden group">
          <div className="relative z-10">
            <h3 className="text-lg font-bold text-white mb-2">Upgrade to Enterprise</h3>
            <p className="text-slate-400 text-sm max-w-md mb-6">
              Unlock unlimited API calls, SSO, and 365-day audit retention for large scale governance.
            </p>
            <button className="px-6 py-2 bg-indigo-600 hover:bg-indigo-500 text-white rounded-lg font-medium transition-all flex items-center gap-2 group-hover:gap-3">
              Upgrade Now
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
        <p className="text-sm text-slate-500">Billing data will appear here once connected to Stripe.</p>
      </div>
    </div>
  );
}
