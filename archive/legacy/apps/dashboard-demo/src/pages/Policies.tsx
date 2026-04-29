import React from 'react';
import { Lock, Shield, CheckCircle } from 'lucide-react';

export const Policies: React.FC = () => {
  const policies = [
    {
      name: 'Production Token Revocation',
      description: 'Automatically revoke tokens after suspicious activity',
      status: 'active',
      type: 'security',
    },
    {
      name: 'S3 Delete Protection',
      description: 'Block destructive S3 operations without approval',
      status: 'active',
      type: 'data',
    },
    {
      name: 'High-Value Refund Approval',
      description: 'Require manual approval for refunds over $1000',
      status: 'active',
      type: 'financial',
    },
    {
      name: 'Repository Delete Block',
      description: 'Prevent autonomous agents from deleting repositories',
      status: 'active',
      type: 'infrastructure',
    },
    {
      name: 'Rate Limiting',
      description: 'Enforce 100 requests per minute per tenant',
      status: 'active',
      type: 'performance',
    },
  ];

  return (
    <div className="space-y-6 animate-in fade-in duration-500">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-black text-white">Governance Policies</h1>
          <p className="text-sm text-slate-500 mt-1">Active security and governance rules</p>
        </div>
        <Lock size={20} className="text-slate-500" />
      </div>

      <div className="grid grid-cols-1 gap-4">
        {policies.map((policy, i) => (
          <div key={i} className="p-6 rounded-2xl bg-slate-900/40 border border-slate-800/50 hover:border-slate-700/50 transition-all">
            <div className="flex items-start justify-between">
              <div className="flex items-start gap-4">
                <div className="w-10 h-10 rounded-xl bg-orange-500/10 flex items-center justify-center flex-shrink-0">
                  <Shield size={20} className="text-orange-500" />
                </div>
                <div>
                  <div className="flex items-center gap-2 mb-1">
                    <h3 className="text-sm font-bold text-slate-200">{policy.name}</h3>
                    <span className="px-2 py-0.5 rounded text-[10px] font-bold uppercase bg-emerald-500/10 text-emerald-500">
                      {policy.status}
                    </span>
                  </div>
                  <p className="text-xs text-slate-500">{policy.description}</p>
                  <div className="flex items-center gap-2 mt-3">
                    <span className="text-[10px] font-bold text-slate-500 uppercase">{policy.type}</span>
                  </div>
                </div>
              </div>
              <CheckCircle size={16} className="text-emerald-500 flex-shrink-0" />
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};
