import { useState, useCallback, useMemo } from 'react';
import {
  ReactFlow,
  Background,
  Controls,
  MiniMap,
  Panel,
} from 'reactflow';
import type { Node, Edge } from 'reactflow';
import 'reactflow/dist/style.css';
import { GroupNode } from './GroupNode';
import { ActionNode } from './ActionNode';
import { Button } from '../ui/Button';
import { Maximize2, Minimize2 } from 'lucide-react';

const nodeTypes = {
  group: GroupNode,
  action: ActionNode,
};

const mockGroups = {
  id: 'group_root',
  name: 'Governance',
  display_name: 'Citadel Governance',
  icon: 'Shield',
  color: '#8b5cf6',
  type: 'group',
  collapsed: false,
  child_count: 8,
  subgroups: [
    {
      id: 'group_communication',
      name: 'Communication',
      display_name: 'Communication',
      icon: 'MessageCircle',
      color: '#8b5cf6',
      type: 'group',
      collapsed: true,
      child_count: 4,
      subgroups: [
        {
          id: 'group_email',
          name: 'Email',
          display_name: 'Email',
          icon: 'Mail',
          color: '#ef4444',
          type: 'group',
          collapsed: true,
          child_count: 2,
          actions: [
            { id: 'send_email', display_name: 'Send Email', icon: 'Mail', color: '#ef4444', risk: 'HIGH' },
            { id: 'send_bulk_email', display_name: 'Bulk Email', icon: 'Mails', color: '#dc2626', risk: 'HIGH' },
          ],
        },
        {
          id: 'group_chat',
          name: 'Chat',
          display_name: 'Chat',
          icon: 'MessageSquare',
          color: '#3b82f6',
          type: 'group',
          collapsed: true,
          child_count: 2,
          actions: [
            { id: 'send_slack', display_name: 'Slack', icon: 'Slack', color: '#3b82f6', risk: 'MEDIUM' },
            { id: 'send_discord', display_name: 'Discord', icon: 'MessageCircle', color: '#5865f2', risk: 'MEDIUM' },
          ],
        },
      ],
    },
    {
      id: 'group_payment',
      name: 'Payment',
      display_name: 'Payment',
      icon: 'CreditCard',
      color: '#22c55e',
      type: 'group',
      collapsed: true,
      child_count: 2,
      actions: [
        { id: 'stripe_charge', display_name: 'Stripe Charge', icon: 'CreditCard', color: '#22c55e', risk: 'HIGH' },
        { id: 'stripe_refund', display_name: 'Stripe Refund', icon: 'RotateCcw', color: '#16a34a', risk: 'HIGH' },
      ],
    },
    {
      id: 'group_database',
      name: 'Database',
      display_name: 'Database',
      icon: 'Database',
      color: '#3b82f6',
      type: 'group',
      collapsed: true,
      child_count: 2,
      actions: [
        { id: 'write_database', display_name: 'Write', icon: 'Database', color: '#3b82f6', risk: 'MEDIUM' },
        { id: 'delete_rows', display_name: 'Delete', icon: 'Trash2', color: '#ef4444', risk: 'HIGH' },
      ],
    },
    {
      id: 'group_infrastructure',
      name: 'Infrastructure',
      display_name: 'Infrastructure',
      icon: 'Server',
      color: '#f59e0b',
      type: 'group',
      collapsed: true,
      child_count: 2,
      actions: [
        { id: 'github_action', display_name: 'GitHub Action', icon: 'Github', color: '#f59e0b', risk: 'HIGH' },
        { id: 'deploy', display_name: 'Deploy', icon: 'Rocket', color: '#ea580c', risk: 'HIGH' },
      ],
    },
  ],
};

export function RecursiveGroupGraph() {
  const [expandedGroups, setExpandedGroups] = useState<Set<string>>(new Set(['group_root']));
  
  const buildNodes = useCallback((group: any, parentId?: string, level: number = 0): Node[] => {
    const nodes: Node[] = [];
    const isExpanded = expandedGroups.has(group.id);
    
    nodes.push({
      id: group.id,
      type: 'group',
      position: { x: 0, y: 0 },
      data: {
        ...group,
        isExpanded,
        level,
        onToggle: () => {
          setExpandedGroups(prev => {
            const next = new Set(prev);
            if (next.has(group.id)) next.delete(group.id);
            else next.add(group.id);
            return next;
          });
        },
      },
      parentId,
    });
    
    if (isExpanded) {
      group.subgroups?.forEach((subgroup: any) => {
        nodes.push(...buildNodes(subgroup, group.id, level + 1));
      });
      group.actions?.forEach((action: any) => {
        nodes.push({
          id: action.id,
          type: 'action',
          position: { x: 0, y: 0 },
          data: { ...action, level: level + 1, parentGroup: group.id },
          parentId: group.id,
        });
      });
    }
    return nodes;
  }, [expandedGroups]);
  
  const buildEdges = useCallback((nodes: Node[]): Edge[] => {
    const edges: Edge[] = [];
    nodes.forEach(node => {
      if (node.type === 'group' && node.data.isExpanded) {
        const children = nodes.filter(n => n.parentId === node.id);
        children.forEach(child => {
          edges.push({
            id: `e-${node.id}-${child.id}`,
            source: node.id,
            target: child.id,
            type: 'smoothstep',
            style: { stroke: '#475569', strokeWidth: 1 },
          });
        });
      }
    });
    return edges;
  }, []);
  
  const layoutNodes = useCallback((nodes: Node[]): Node[] => {
    const levelWidth = 250;
    const levelNodes: Map<number, Node[]> = new Map();
    nodes.forEach(node => {
      const level = node.data.level || 0;
      if (!levelNodes.has(level)) levelNodes.set(level, []);
      levelNodes.get(level)!.push(node);
    });
    
    let positioned = [...nodes];
    levelNodes.forEach((levelNodesList, level) => {
      const ySpacing = 100;
      const startY = -(levelNodesList.length * ySpacing) / 2;
      levelNodesList.forEach((node, idx) => {
        const x = level * levelWidth;
        const y = startY + idx * ySpacing;
        positioned = positioned.map(n => n.id === node.id ? { ...n, position: { x, y } } : n);
      });
    });
    return positioned;
  }, []);
  
  const nodes = useMemo(() => layoutNodes(buildNodes(mockGroups)), [buildNodes, layoutNodes]);
  const edges = useMemo(() => buildEdges(nodes), [nodes, buildEdges]);
  
  const expandAll = () => {
    const allIds = new Set<string>();
    const collectIds = (g: any) => {
      allIds.add(g.id);
      g.subgroups?.forEach(collectIds);
    };
    collectIds(mockGroups);
    setExpandedGroups(allIds);
  };
  
  const collapseAll = () => setExpandedGroups(new Set(['group_root']));
  
  return (
    <div className="h-[600px] w-full border rounded-lg overflow-hidden bg-slate-950">
      <ReactFlow nodes={nodes} edges={edges} nodeTypes={nodeTypes} fitView>
        <Background color="#334155" gap={16} size={1} />
        <Controls />
        <MiniMap nodeStrokeWidth={3} zoomable pannable className="bg-slate-900" />
        <Panel position="top-left" className="bg-slate-900/90 p-2 rounded-lg border border-slate-700">
          <div className="flex gap-1">
            <Button variant="secondary" onClick={expandAll} className="text-xs h-8"><Maximize2 className="w-3 h-3 mr-1" />Expand</Button>
            <Button variant="secondary" onClick={collapseAll} className="text-xs h-8"><Minimize2 className="w-3 h-3 mr-1" />Collapse</Button>
          </div>
        </Panel>
      </ReactFlow>
    </div>
  );
}
