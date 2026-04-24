import { useCallback, useEffect, useState } from 'react';
import {
  ReactFlow,
  Background,
  Controls,
  MiniMap,
  addEdge,
  useNodesState,
  useEdgesState,
  Panel,
  Node,
  Edge,
  Connection,
} from 'reactflow';
import 'reactflow/dist/style.css';
import { CustomNode } from './custom-node';
import { ApprovalEdge } from './approval-edge';
import { KillSwitchNode } from './kill-switch-node';
import { useCITADELStats } from '@/lib/hooks';
import { Button } from '@/components/ui/button';
import { Layers, Maximize2, Minus, Plus } from 'lucide-react';

const nodeTypes = {
  custom: CustomNode,
  killswitch: KillSwitchNode,
};

const edgeTypes = {
  approval: ApprovalEdge,
};

// Initial nodes showing governance flow
const initialNodes: Node[] = [
  {
    id: 'agent',
    type: 'custom',
    position: { x: 100, y: 200 },
    data: {
      label: 'Agent',
      icon: 'Bot',
      color: '#8b5cf6',
      description: 'AI Agent initiates action',
      status: 'active',
    },
  },
  {
    id: 'risk-check',
    type: 'custom',
    position: { x: 300, y: 200 },
    data: {
      label: 'Risk Check',
      icon: 'Shield',
      color: '#f59e0b',
      description: 'Classify LOW/MEDIUM/HIGH risk',
      status: 'processing',
    },
  },
  {
    id: 'kill-switch',
    type: 'killswitch',
    position: { x: 500, y: 100 },
    data: {
      label: 'Kill Switches',
      switches: [
        { name: 'email_send', active: false },
        { name: 'stripe_charge', active: true },
        { name: 'db_write', active: false },
      ],
    },
  },
  {
    id: 'approval-queue',
    type: 'custom',
    position: { x: 500, y: 300 },
    data: {
      label: 'Approval Queue',
      icon: 'Users',
      color: '#3b82f6',
      description: '3 pending approvals',
      status: 'pending',
      badge: '3',
    },
  },
  {
    id: 'rate-limit',
    type: 'custom',
    position: { x: 500, y: 200 },
    data: {
      label: 'Rate Limiter',
      icon: 'Gauge',
      color: '#06b6d4',
      description: '100/hour remaining',
      status: 'ok',
    },
  },
  {
    id: 'action-email',
    type: 'custom',
    position: { x: 750, y: 150 },
    data: {
      label: 'Send Email',
      icon: 'Mail',
      color: '#ef4444',
      description: 'HIGH risk â€¢ HARD approval',
      status: 'blocked',
      group: 'communication',
    },
  },
  {
    id: 'action-stripe',
    type: 'custom',
    position: { x: 750, y: 250 },
    data: {
      label: 'Stripe Charge',
      icon: 'CreditCard',
      color: '#22c55e',
      description: 'HIGH risk â€¢ HARD approval',
      status: 'blocked',
      group: 'payment',
    },
  },
  {
    id: 'action-db',
    type: 'custom',
    position: { x: 750, y: 350 },
    data: {
      label: 'DB Write',
      icon: 'Database',
      color: '#3b82f6',
      description: 'MEDIUM risk â€¢ HARD approval',
      status: 'allowed',
      group: 'database',
    },
  },
  {
    id: 'audit-log',
    type: 'custom',
    position: { x: 950, y: 250 },
    data: {
      label: 'Audit Log',
      icon: 'FileText',
      color: '#6b7280',
      description: 'Tamper-proof hash chain',
      status: 'active',
    },
  },
];

const initialEdges: Edge[] = [
  {
    id: 'e1',
    source: 'agent',
    target: 'risk-check',
    animated: true,
    style: { stroke: '#8b5cf6' },
  },
  {
    id: 'e2',
    source: 'risk-check',
    target: 'rate-limit',
    animated: true,
    style: { stroke: '#f59e0b' },
  },
  {
    id: 'e3',
    source: 'rate-limit',
    target: 'kill-switch',
    animated: true,
    style: { stroke: '#06b6d4' },
  },
  {
    id: 'e4',
    source: 'rate-limit',
    target: 'approval-queue',
    type: 'approval',
    animated: true,
    data: { label: 'HARD approval needed' },
  },
  {
    id: 'e5',
    source: 'approval-queue',
    target: 'action-email',
    type: 'approval',
    animated: true,
    data: { label: 'Approved' },
    style: { stroke: '#22c55e' },
  },
  {
    id: 'e6',
    source: 'approval-queue',
    target: 'action-stripe',
    type: 'approval',
    animated: false,
    style: { stroke: '#ef4444', strokeDasharray: '5,5' },
  },
  {
    id: 'e7',
    source: 'approval-queue',
    target: 'action-db',
    type: 'approval',
    animated: true,
    style: { stroke: '#22c55e' },
  },
  {
    id: 'e8',
    source: 'action-email',
    target: 'audit-log',
    animated: true,
    style: { stroke: '#6b7280' },
  },
  {
    id: 'e9',
    source: 'action-stripe',
    target: 'audit-log',
    animated: false,
    style: { stroke: '#6b7280', strokeDasharray: '5,5' },
  },
  {
    id: 'e10',
    source: 'action-db',
    target: 'audit-log',
    animated: true,
    style: { stroke: '#22c55e' },
  },
];

// Collapsible groups (like Weft)
const GROUPS = {
  communication: {
    label: 'Communication',
    nodes: ['action-email'],
    color: '#ef4444',
  },
  payment: {
    label: 'Payment',
    nodes: ['action-stripe'],
    color: '#22c55e',
  },
  database: {
    label: 'Database',
    nodes: ['action-db'],
    color: '#3b82f6',
  },
};

export function GovernanceGraph() {
  const [nodes, setNodes, onNodesChange] = useNodesState(initialNodes);
  const [edges, setEdges, onEdgesChange] = useEdgesState(initialEdges);
  const [collapsedGroups, setCollapsedGroups] = useState<string[]>([]);
  const { data: stats } = useCITADELStats();

  const onConnect = useCallback(
    (connection: Connection) => setEdges((eds) => addEdge(connection, eds)),
    [setEdges]
  );

  // Toggle group collapse (like Weft)
  const toggleGroup = (groupId: string) => {
    const group = GROUPS[groupId as keyof typeof GROUPS];
    if (!group) return;

    if (collapsedGroups.includes(groupId)) {
      // Expand: restore original nodes
      setCollapsedGroups((prev) => prev.filter((g) => g !== groupId));
      // TODO: Restore original positions
    } else {
      // Collapse: replace with single node
      setCollapsedGroups((prev) => [...prev, groupId]);
      // Hide child nodes, show group node
      setNodes((prev) =>
        prev.map((node) => {
          if (group.nodes.includes(node.id)) {
            return { ...node, hidden: true };
          }
          return node;
        })
      );
    }
  };

  // Update live data
  useEffect(() => {
    if (!stats) return;

    setNodes((prev) =>
      prev.map((node) => {
        if (node.id === 'approval-queue' && stats.pending_approvals !== undefined) {
          return {
            ...node,
            data: {
              ...node.data,
              description: `${stats.pending_approvals} pending approvals`,
              badge: stats.pending_approvals > 0 ? String(stats.pending_approvals) : undefined,
            },
          };
        }
        if (node.id === 'kill-switch') {
          return {
            ...node,
            data: {
              ...node.data,
              switches: [
                { name: 'email_send', active: stats.killswitches?.email_send || false },
                { name: 'stripe_charge', active: stats.killswitches?.stripe_charge || false },
                { name: 'db_write', active: stats.killswitches?.db_write || false },
              ],
            },
          };
        }
        return node;
      })
    );
  }, [stats, setNodes]);

  return (
    <div className="h-[600px] w-full border rounded-lg overflow-hidden bg-slate-950">
      <ReactFlow
        nodes={nodes}
        edges={edges}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        onConnect={onConnect}
        nodeTypes={nodeTypes}
        edgeTypes={edgeTypes}
        fitView
        attributionPosition="bottom-left"
      >
        <Background color="#334155" gap={16} size={1} />
        <Controls />
        <MiniMap
          nodeStrokeWidth={3}
          zoomable
          pannable
          className="bg-slate-900"
        />
        
        {/* Group controls */}
        <Panel position="top-left" className="bg-slate-900/90 p-2 rounded-lg border border-slate-700">
          <div className="flex items-center gap-2 mb-2">
            <Layers className="w-4 h-4 text-slate-400" />
            <span className="text-xs font-medium text-slate-300">Groups</span>
          </div>
          <div className="flex flex-col gap-1">
            {Object.entries(GROUPS).map(([id, group]) => (
              <Button
                key={id}
                variant="ghost"
                size="sm"
                onClick={() => toggleGroup(id)}
                className="justify-start text-xs"
                style={{
                  color: collapsedGroups.includes(id) ? '#94a3b8' : group.color,
                }}
              >
                {collapsedGroups.includes(id) ? (
                  <Plus className="w-3 h-3 mr-1" />
                ) : (
                  <Minus className="w-3 h-3 mr-1" />
                )}
                {group.label}
              </Button>
            ))}
          </div>
        </Panel>

        {/* Legend */}
        <Panel position="bottom-right" className="bg-slate-900/90 p-3 rounded-lg border border-slate-700">
          <div className="text-xs text-slate-400 space-y-1">
            <div className="flex items-center gap-2">
              <div className="w-2 h-2 rounded-full bg-green-500" />
              <span>Allowed</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-2 h-2 rounded-full bg-red-500" />
              <span>Blocked</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-2 h-2 rounded-full bg-yellow-500" />
              <span>Pending</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-2 h-2 rounded-full bg-blue-500" />
              <span>Processing</span>
            </div>
          </div>
        </Panel>
      </ReactFlow>
    </div>
  );
}
