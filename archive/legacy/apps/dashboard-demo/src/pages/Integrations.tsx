import React from 'react';
import { Zap, ArrowRight } from 'lucide-react';

const integrations = [
  {
    name: 'K2.6 (Moonshot AI)',
    description: 'Governed agents, tasks, and workflows',
    status: 'stable',
    category: 'Agent Framework',
  },
  {
    name: 'LangGraph',
    description: 'Governed nodes and state graphs',
    status: 'stable',
    category: 'Agent Framework',
  },
  {
    name: 'Codex (OpenAI)',
    description: 'Code generation with security review',
    status: 'stable',
    category: 'Code Generation',
  },
  {
    name: 'Claude Code (Anthropic)',
    description: 'Agent actions with governance checkpoints',
    status: 'stable',
    category: 'Code Generation',
  },
  {
    name: 'Stripe Gateway',
    description: 'Payment operations with approval workflows',
    status: 'protected',
    category: 'Payment',
  },
  {
    name: 'GitHub CI/CD',
    description: 'Repository operations governance',
    status: 'protected',
    category: 'DevOps',
  },
];

export const Integrations: React.FC = () => {
  return (
    <div className="space-y-6 animate-in fade-in duration-500">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-black text-white">Integrations</h1>
          <p className="text-sm text-slate-500 mt-1">Connected frameworks and services</p>
        </div>
        <Zap size={20} className="text-slate-500" />
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {integrations.map((integration, i) => (
          <div key={i} className="p-6 rounded-2xl bg-slate-900/40 border border-slate-800/50 hover:border-slate-700/50 transition-all group cursor-pointer">
            <div className="flex items-start justify-between mb-4">
              <div className="w-10 h-10 rounded-xl bg-indigo-500/10 flex items-center justify-center">
                <Zap size={20} className="text-indigo-400" />
              </div>
              <div className="flex items-center gap-2">
                <span className={`px-2 py-0.5 rounded text-[10px] font-bold uppercase ${
                  integration.status === 'stable'
                    ? 'bg-emerald-500/10 text-emerald-500'
                    : 'bg-blue-500/10 text-blue-500'
                }`}>
                  {integration.status}
                </span>
              </div>
            </div>
            <h3 className="text-sm font-bold text-slate-200 mb-1">{integration.name}</h3>
            <p className="text-xs text-slate-500 mb-3">{integration.description}</p>
            <div className="flex items-center justify-between">
              <span className="text-[10px] font-bold text-slate-500 uppercase">{integration.category}</span>
              <ArrowRight size={14} className="text-slate-500 group-hover:text-slate-300 transition-colors" />
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};
