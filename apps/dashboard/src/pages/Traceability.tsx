import { GitBranch, KeyRound, ScrollText, ShieldCheck } from 'lucide-react';
import { TraceabilityGraph } from '../components/traceability/TraceabilityGraph';

const lineageFacts = [
  {
    label: 'Decision spine',
    value: 'decision_id',
    detail: 'Primary join key across token, runtime outcome, and audit events.',
    icon: ShieldCheck,
  },
  {
    label: 'Policy evidence',
    value: 'policy_version',
    detail: 'Captures the exact policy set used when the decision was made.',
    icon: ScrollText,
  },
  {
    label: 'Scoped proof',
    value: 'gt_cap_',
    detail: 'Short-lived capability token tied to one governance decision.',
    icon: KeyRound,
  },
  {
    label: 'Runtime correlation',
    value: 'trace_id',
    detail: 'Connects execution logs, dashboard events, and audit evidence.',
    icon: GitBranch,
  },
];

export const Traceability = () => {
  return (
    <div className="space-y-8 animate-in fade-in duration-700">
      <div className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
        <div>
          <p className="text-[10px] font-black uppercase tracking-[0.22em] text-orange-500">
            Runtime Evidence
          </p>
          <h1 className="mt-2 text-3xl font-black tracking-tight text-white">
            Traceability Graph
          </h1>
          <p className="mt-2 max-w-3xl text-sm leading-6 text-slate-500">
            See how Citadel connects a policy version to a persisted decision,
            short-lived execution token, approval state, protected runtime action,
            and hash-chained audit evidence.
          </p>
        </div>
        <div className="rounded-full border border-orange-500/20 bg-orange-500/10 px-4 py-2 text-xs font-bold uppercase tracking-wide text-orange-400">
          Runtime lineage model
        </div>
      </div>

      <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-4">
        {lineageFacts.map((fact) => (
          <div
            key={fact.value}
            className="rounded-2xl border border-slate-800/60 bg-slate-900/40 p-5 shadow-xl shadow-black/10"
          >
            <div className="flex items-start gap-3">
              <div className="grid h-10 w-10 shrink-0 place-items-center rounded-xl bg-orange-500/10 text-orange-400">
                <fact.icon size={19} />
              </div>
              <div>
                <p className="text-[10px] font-black uppercase tracking-[0.16em] text-slate-500">
                  {fact.label}
                </p>
                <h3 className="mt-1 font-mono text-sm font-bold text-slate-100">{fact.value}</h3>
              </div>
            </div>
            <p className="mt-4 text-xs leading-5 text-slate-500">{fact.detail}</p>
          </div>
        ))}
      </div>

      <TraceabilityGraph />
    </div>
  );
};
