import { memo, useMemo } from 'react';
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
  CircleSlash2,
  Clock3,
  FileCheck2,
  Fingerprint,
  GitBranch,
  KeyRound,
  ScrollText,
  ShieldCheck,
  Zap,
} from 'lucide-react';
import type { TraceabilityGraphResponse } from '../../api/client';

type TraceabilityStatus =
  | 'verified'
  | 'active'
  | 'approved'
  | 'executed'
  | 'evidence'
  | 'pending'
  | 'blocked';

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
  pending: Clock3,
  blocked: CircleSlash2,
};

const STATUS_STYLES: Record<TraceabilityStatus, string> = {
  verified: 'border-sky-400/50 shadow-sky-500/10',
  active: 'border-orange-400/60 shadow-orange-500/10',
  approved: 'border-emerald-400/50 shadow-emerald-500/10',
  executed: 'border-indigo-400/50 shadow-indigo-500/10',
  evidence: 'border-slate-400/40 shadow-slate-500/10',
  pending: 'border-amber-400/50 shadow-amber-500/10',
  blocked: 'border-rose-400/50 shadow-rose-500/10',
};

const STATUS_DOTS: Record<TraceabilityStatus, string> = {
  verified: 'bg-sky-400',
  active: 'bg-orange-400',
  approved: 'bg-emerald-400',
  executed: 'bg-indigo-400',
  evidence: 'bg-slate-400',
  pending: 'bg-amber-400',
  blocked: 'bg-rose-400',
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

const FALLBACK_GRAPH: TraceabilityGraphResponse = {
  source: 'reference',
  decision_id: 'gd_01h_trace_7f2',
  trace_id: 'trace_123',
  nodes: [
    {
      id: 'policy',
      type: 'policy',
      title: 'High-Value Refund Approval',
      detail: 'Policy version selected during decision evaluation.',
      meta: { policy_version: 'policy_2026_04_24_7' },
      status: 'verified',
    },
    {
      id: 'decision',
      type: 'decision',
      title: 'Allow with Approval Evidence',
      detail: 'Durable governance decision persisted before token issuance.',
      meta: { decision_id: 'gd_01h_trace_7f2' },
      status: 'active',
    },
    {
      id: 'token',
      type: 'token',
      title: 'Short-Lived gt_cap_',
      detail: 'Scoped execution proof bound to one decision_id.',
      meta: { token_id: 'gt_cap_9k2...42s' },
      status: 'active',
    },
    {
      id: 'approval',
      type: 'approval',
      title: 'Operator Approved',
      detail: 'Human approval state stays joinable through decision_id.',
      meta: { approved_by: 'operator:admin' },
      status: 'approved',
    },
    {
      id: 'execution',
      type: 'execution',
      title: 'stripe.refund.create',
      detail: 'Runtime gateway introspected token before execution.',
      meta: { resource: 'customer:2841' },
      status: 'executed',
    },
    {
      id: 'audit',
      type: 'audit',
      title: 'Outcome Correlated',
      detail: 'Audit record links outcome to token, decision, policy, and approval.',
      meta: { trace_id: 'trace_123', event_hash: 'event_hash' },
      status: 'evidence',
    },
  ],
  edges: [
    { id: 'policy-decision', source: 'policy', target: 'decision', label: 'evaluates', status: 'active' },
    { id: 'decision-token', source: 'decision', target: 'token', label: 'issues', status: 'active' },
    { id: 'decision-approval', source: 'decision', target: 'approval', label: 'preserves state', status: 'active' },
    { id: 'token-execution', source: 'token', target: 'execution', label: 'introspected', status: 'active' },
    { id: 'approval-execution', source: 'approval', target: 'execution', label: 'authorizes', status: 'active' },
    { id: 'execution-audit', source: 'execution', target: 'audit', label: 'records outcome', status: 'active' },
  ],
};

const TYPE_POSITIONS: Record<string, { x: number; y: number }> = {
  policy: { x: 20, y: 190 },
  decision: { x: 320, y: 190 },
  token: { x: 620, y: 75 },
  approval: { x: 620, y: 305 },
  execution: { x: 940, y: 190 },
  audit: { x: 1240, y: 190 },
};

const TYPE_LABELS: Record<string, string> = {
  policy: 'Policy',
  decision: 'Decision',
  token: 'Capability',
  approval: 'Approval',
  execution: 'Execution',
  audit: 'Audit Evidence',
};

function normalizeStatus(status?: string): TraceabilityStatus {
  const value = (status || '').toLowerCase();

  if (['verified'].includes(value)) return 'verified';
  if (['active', 'allow', 'allowed'].includes(value)) return 'active';
  if (['approved', 'auto_approved'].includes(value)) return 'approved';
  if (['executed', 'execution'].includes(value)) return 'executed';
  if (['pending', 'require_approval', 'escalate'].includes(value)) return 'pending';
  if (['blocked', 'deny', 'denied', 'revoked', 'expired', 'rejected'].includes(value)) return 'blocked';

  return 'evidence';
}

function iconForType(type: string): keyof typeof ICONS {
  if (type in ICONS) {
    return type as keyof typeof ICONS;
  }
  return 'trace';
}

function metaPreview(meta: Record<string, unknown>) {
  const preferredKeys = [
    'decision_id',
    'token_id',
    'policy_version',
    'event_hash',
    'trace_id',
    'resource',
    'approved_by',
  ];
  const key = preferredKeys.find((item) => meta[item]);
  const raw = key ? String(meta[key]) : Object.values(meta).find(Boolean)?.toString();

  if (!raw) return 'live evidence';
  return raw.length > 34 ? `${raw.slice(0, 25)}...${raw.slice(-5)}` : raw;
}

type TraceabilityGraphProps = {
  graph?: TraceabilityGraphResponse;
};

export function TraceabilityGraph({ graph }: TraceabilityGraphProps) {
  const activeGraph = graph?.nodes.length ? graph : FALLBACK_GRAPH;
  const isLive = activeGraph.source === 'live' && Boolean(graph?.nodes.length);

  const nodes = useMemo<Node<TraceabilityNodeData>[]>(() => {
    const typeCounts: Record<string, number> = {};

    return activeGraph.nodes.map((node, index) => {
      const base = TYPE_POSITIONS[node.type] || { x: 120 + index * 260, y: 190 };
      const seen = typeCounts[node.type] || 0;
      typeCounts[node.type] = seen + 1;

      return {
        id: node.id,
        type: 'traceability',
        position: {
          x: base.x,
          y: base.y + seen * 128,
        },
        data: {
          eyebrow: TYPE_LABELS[node.type] || node.type,
          title: node.title,
          detail: node.detail,
          meta: metaPreview(node.meta || {}),
          icon: iconForType(node.type),
          status: normalizeStatus(node.status),
        },
      };
    });
  }, [activeGraph]);

  const edges = useMemo<Edge[]>(() => {
    return activeGraph.edges.map((edge) => ({
      ...edge,
      animated: edge.label.toLowerCase().includes('introspect'),
      markerEnd: { type: MarkerType.ArrowClosed, color: '#fb923c' },
      style: { stroke: '#fb923c', strokeWidth: 2 },
      labelStyle: { fill: '#cbd5e1', fontSize: 11, fontWeight: 700 },
      labelBgStyle: { fill: '#0f172a', fillOpacity: 0.9 },
    }));
  }, [activeGraph]);

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
            <p className="mt-3 inline-flex rounded-full border border-orange-500/20 bg-orange-500/10 px-3 py-1 text-[10px] font-black uppercase tracking-[0.16em] text-orange-300">
              {isLive ? 'Live backend lineage' : 'Reference fallback'}
            </p>
          </div>
        </Panel>
      </ReactFlow>
    </div>
  );
}
