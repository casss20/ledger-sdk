import { memo } from 'react';
import {
  Background,
  Controls,
  Handle,
  MarkerType,
  MiniMap,
  Panel,
  Position,
  ReactFlow,
} from 'reactflow';
import type { Edge, Node, NodeProps } from 'reactflow';
import 'reactflow/dist/style.css';
import {
  CheckCircle2,
  FileCheck2,
  Fingerprint,
  GitBranch,
  KeyRound,
  ScrollText,
  ShieldCheck,
  Zap,
} from 'lucide-react';

type TraceabilityStatus = 'verified' | 'active' | 'approved' | 'executed' | 'evidence';

type TraceabilityNodeData = {
  title: string;
  eyebrow: string;
  detail: string;
  meta: string;
  icon: keyof typeof ICONS;
  status: TraceabilityStatus;
};

const ICONS = {
  policy: ScrollText,
  decision: ShieldCheck,
  token: KeyRound,
  approval: CheckCircle2,
  execution: Zap,
  audit: FileCheck2,
  trace: GitBranch,
  fingerprint: Fingerprint,
};

const STATUS_STYLES: Record<TraceabilityStatus, string> = {
  verified: 'border-sky-400/50 shadow-sky-500/10',
  active: 'border-orange-400/60 shadow-orange-500/10',
  approved: 'border-emerald-400/50 shadow-emerald-500/10',
  executed: 'border-indigo-400/50 shadow-indigo-500/10',
  evidence: 'border-slate-400/40 shadow-slate-500/10',
};

const STATUS_DOTS: Record<TraceabilityStatus, string> = {
  verified: 'bg-sky-400',
  active: 'bg-orange-400',
  approved: 'bg-emerald-400',
  executed: 'bg-indigo-400',
  evidence: 'bg-slate-400',
};

function TraceabilityNode({ data, selected }: NodeProps<TraceabilityNodeData>) {
  const Icon = ICONS[data.icon];

  return (
    <div
      className={`
        min-w-[210px] rounded-2xl border bg-slate-950/95 p-4 shadow-2xl
        transition-all duration-200
        ${STATUS_STYLES[data.status]}
        ${selected ? 'ring-2 ring-orange-300/40 scale-[1.02]' : ''}
      `}
    >
      <div className="flex items-start gap-3">
        <div className="grid h-10 w-10 shrink-0 place-items-center rounded-xl border border-orange-500/20 bg-orange-500/10">
          <Icon className="h-5 w-5 text-orange-400" />
        </div>
        <div className="min-w-0">
          <p className="text-[10px] font-black uppercase tracking-[0.18em] text-slate-500">
            {data.eyebrow}
          </p>
          <h3 className="mt-1 truncate text-sm font-black text-slate-100">{data.title}</h3>
          <p className="mt-1 text-xs leading-relaxed text-slate-400">{data.detail}</p>
        </div>
      </div>

      <div className="mt-4 flex items-center justify-between rounded-xl border border-slate-800 bg-slate-900/80 px-3 py-2">
        <span className="font-mono text-[10px] text-slate-500">{data.meta}</span>
        <span className="flex items-center gap-1.5 text-[10px] font-bold uppercase tracking-wide text-slate-400">
          <span className={`h-1.5 w-1.5 rounded-full ${STATUS_DOTS[data.status]}`} />
          {data.status}
        </span>
      </div>

      <Handle type="target" position={Position.Left} className="!h-3 !w-3 !border-slate-950 !bg-orange-400" />
      <Handle type="source" position={Position.Right} className="!h-3 !w-3 !border-slate-950 !bg-orange-400" />
    </div>
  );
}

const nodeTypes = {
  traceability: memo(TraceabilityNode),
};

const nodes: Node<TraceabilityNodeData>[] = [
  {
    id: 'policy',
    type: 'traceability',
    position: { x: 20, y: 190 },
    data: {
      eyebrow: 'Policy',
      title: 'High-Value Refund Approval',
      detail: 'Policy version selected during decision evaluation.',
      meta: 'policy_2026_04_24_7',
      icon: 'policy',
      status: 'verified',
    },
  },
  {
    id: 'decision',
    type: 'traceability',
    position: { x: 320, y: 190 },
    data: {
      eyebrow: 'Decision',
      title: 'Allow with Approval Evidence',
      detail: 'Durable governance decision persisted before token issuance.',
      meta: 'gd_01h_trace_7f2',
      icon: 'decision',
      status: 'active',
    },
  },
  {
    id: 'token',
    type: 'traceability',
    position: { x: 620, y: 75 },
    data: {
      eyebrow: 'Capability',
      title: 'Short-Lived gt_cap_',
      detail: 'Scoped execution proof bound to one decision_id.',
      meta: 'gt_cap_9k2...42s',
      icon: 'token',
      status: 'active',
    },
  },
  {
    id: 'approval',
    type: 'traceability',
    position: { x: 620, y: 305 },
    data: {
      eyebrow: 'Approval',
      title: 'Operator Approved',
      detail: 'Human approval state stays joinable through decision_id.',
      meta: 'approved_by operator:admin',
      icon: 'approval',
      status: 'approved',
    },
  },
  {
    id: 'execution',
    type: 'traceability',
    position: { x: 940, y: 190 },
    data: {
      eyebrow: 'Execution',
      title: 'stripe.refund.create',
      detail: 'Runtime gateway introspected token before execution.',
      meta: 'customer:2841',
      icon: 'execution',
      status: 'executed',
    },
  },
  {
    id: 'audit',
    type: 'traceability',
    position: { x: 1240, y: 190 },
    data: {
      eyebrow: 'Audit Evidence',
      title: 'Outcome Correlated',
      detail: 'Audit record links outcome to token, decision, policy, and approval.',
      meta: 'trace_123 / event_hash',
      icon: 'audit',
      status: 'evidence',
    },
  },
];

const edges: Edge[] = [
  {
    id: 'policy-decision',
    source: 'policy',
    target: 'decision',
    label: 'evaluates',
  },
  {
    id: 'decision-token',
    source: 'decision',
    target: 'token',
    label: 'issues',
  },
  {
    id: 'decision-approval',
    source: 'decision',
    target: 'approval',
    label: 'preserves state',
  },
  {
    id: 'token-execution',
    source: 'token',
    target: 'execution',
    label: 'introspected',
  },
  {
    id: 'approval-execution',
    source: 'approval',
    target: 'execution',
    label: 'authorizes',
  },
  {
    id: 'execution-audit',
    source: 'execution',
    target: 'audit',
    label: 'records outcome',
  },
].map((edge) => ({
  ...edge,
  animated: edge.id === 'token-execution',
  markerEnd: { type: MarkerType.ArrowClosed, color: '#fb923c' },
  style: { stroke: '#fb923c', strokeWidth: 2 },
  labelStyle: { fill: '#cbd5e1', fontSize: 11, fontWeight: 700 },
  labelBgStyle: { fill: '#0f172a', fillOpacity: 0.9 },
}));

export function TraceabilityGraph() {
  return (
    <div className="h-[620px] w-full overflow-hidden rounded-[2rem] border border-slate-800/70 bg-slate-950 shadow-2xl shadow-black/30">
      <ReactFlow
        nodes={nodes}
        edges={edges}
        nodeTypes={nodeTypes}
        fitView
        minZoom={0.35}
        maxZoom={1.35}
        proOptions={{ hideAttribution: true }}
      >
        <Background color="#334155" gap={18} size={1} />
        <Controls className="!border-slate-700 !bg-slate-900 !text-slate-200" />
        <MiniMap nodeStrokeWidth={3} zoomable pannable className="!bg-slate-900" />
        <Panel position="top-left" className="rounded-2xl border border-slate-800 bg-slate-950/90 p-4 shadow-xl backdrop-blur">
          <div className="max-w-sm">
            <p className="text-[10px] font-black uppercase tracking-[0.2em] text-orange-400">
              Traceability Graph
            </p>
            <h2 className="mt-1 text-lg font-black text-white">Policy to execution lineage</h2>
            <p className="mt-1 text-xs leading-relaxed text-slate-400">
              Follow the joinable path from policy version to decision, token, approval,
              runtime execution, and audit evidence.
            </p>
          </div>
        </Panel>
      </ReactFlow>
    </div>
  );
}
