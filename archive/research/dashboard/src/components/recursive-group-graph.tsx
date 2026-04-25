import { useState, useCallback, useMemo } from 'react';
import {
  ReactFlow,
  Background,
  Controls,
  MiniMap,
  Node,
  Edge,
  useNodesState,
  useEdgesState,
  Panel,
} from 'reactflow';
import 'reactflow/dist/style.css';
import { GroupNode } from './group-node';
import { ActionNode } from './action-node';
import { Button } from '@/components/ui/button';
import { Folder, Maximize2, Minimize2, Layers } from 'lucide-react';

const nodeTypes = {
  group: GroupNode,
  action: ActionNode,
};

// Mock data representing the recursive group structure
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

interface RecursiveGroupGraphProps {
  onGroupToggle?: (groupId: string, collapsed: boolean) => void;
}

export function RecursiveGroupGraph({ onGroupToggle }: RecursiveGroupGraphProps) {
  const [expandedGroups, setExpandedGroups] = useState<Set<string>>(new Set(['group_root']));
  
  // Build nodes from recursive group structure
  const buildNodes = useCallback((group: any, parentId?: string, level: number = 0): Node[] => {
    const nodes: Node[] = [];
    const isExpanded = expandedGroups.has(group.id);
    
    // Add the group node
    nodes.push({
      id: group.id,
      type: 'group',
      position: { x: 0, y: 0 }, // Will be laid out by ELK or manually
      data: {
        ...group,
        isExpanded,
        level,
        onToggle: () => {
          setExpandedGroups(prev => {
            const next = new Set(prev);
            if (next.has(group.id)) {
              next.delete(group.id);
            } else {
              next.add(group.id);
            }
            onGroupToggle?.(group.id, !next.has(group.id));
            return next;
          });
        },
      },
      parentId,
    });
    
    // Add children if expanded
    if (isExpanded) {
      // Add subgroups
      group.subgroups?.forEach((subgroup: any) => {
        nodes.push(...buildNodes(subgroup, group.id, level + 1));
      });
      
      // Add direct actions
      group.actions?.forEach((action: any, idx: number) => {
        nodes.push({
          id: action.id,
          type: 'action',
          position: { x: 0, y: 0 },
          data: {
            ...action,
            level: level + 1,
            parentGroup: group.id,
          },
          parentId: group.id,
        });
      });
    }
    
    return nodes;
  }, [expandedGroups, onGroupToggle]);
  
  // Build edges between nodes
  const buildEdges = useCallback((nodes: Node[]): Edge[] => {
    const edges: Edge[] = [];
    const nodeMap = new Map(nodes.map(n => [n.id, n]));
    
    nodes.forEach(node => {
      if (node.type === 'group' && node.data.isExpanded) {
        // Connect group to its visible children
        const children = nodes.filter(n => n.parentId === node.id);
        children.forEach((child, idx) => {
          edges.push({
            id: `e-${node.id}-${child.id}`,
            source: node.id,
            target: child.id,
            type: 'smoothstep',
            animated: false,
            style: { stroke: '#475569', strokeWidth: 1 },
          });
        });
      }
    });
    
    return edges;
  }, []);
  
  // Simple tree layout
  const layoutNodes = useCallback((nodes: Node[]): Node[] => {
    const levelWidth = 250;
    const nodeHeight = 80;
    const levelNodes: Map<number, Node[]> = new Map();
    
    // Group by level
    nodes.forEach(node => {
      const level = node.data.level || 0;
      if (!levelNodes.has(level)) {
        levelNodes.set(level, []);
      }
      levelNodes.get(level)!.push(node);
    });
    
    // Position nodes
    let positioned = [...nodes];
    levelNodes.forEach((levelNodesList, level) => {
      const ySpacing = 100;
      const totalHeight = levelNodesList.length * ySpacing;
      const startY = -totalHeight / 2;
      
      levelNodesList.forEach((node, idx) => {
        const x = level * levelWidth;
        const y = startY + idx * ySpacing;
        positioned = positioned.map(n => 
          n.id === node.id ? { ...n, position: { x, y } } : n
        );
      });
    });
    
    return positioned;
  }, []);
  
  const rawNodes = useMemo(() => buildNodes(mockGroups), [buildNodes]);
  const nodes = useMemo(() => layoutNodes(rawNodes), [rawNodes, layoutNodes]);
  const edges = useMemo(() => buildEdges(nodes), [nodes, buildEdges]);
  
  const [flowNodes, , onNodesChange] = useNodesState(nodes);
  const [flowEdges, , onEdgesChange] = useEdgesState(edges);
  
  // Update nodes when expanded groups change
  useMemo(() => {
    const newRawNodes = buildNodes(mockGroups);
    const newNodes = layoutNodes(newRawNodes);
    const newEdges = buildEdges(newNodes);
    // React Flow will pick these up
  }, [expandedGroups]);
  
  const expandAll = () => {
    const allIds = new Set<string>();
    const collectIds = (g: any) => {
      allIds.add(g.id);
      g.subgroups?.forEach(collectIds);
    };
    collectIds(mockGroups);
    setExpandedGroups(allIds);
  };
  
  const collapseAll = () => {
    setExpandedGroups(new Set(['group_root']));
  };
  
  return (
    <div className="h-[600px] w-full border rounded-lg overflow-hidden bg-slate-950">
      <ReactFlow
        nodes={nodes}
        edges={edges}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        nodeTypes={nodeTypes}
        fitView
        attributionPosition="bottom-left"
      >
        <Background color="#334155" gap={16} size={1} />
        <Controls />
        <MiniMap nodeStrokeWidth={3} zoomable pannable className="bg-slate-900" />
        
        {/* Controls */}
        <Panel position="top-left" className="bg-slate-900/90 p-2 rounded-lg border border-slate-700">
          <div className="flex items-center gap-2 mb-2">
            <Layers className="w-4 h-4 text-slate-400" />
            <span className="text-xs font-medium text-slate-300">Groups</span>
          </div>
          <div className="flex gap-1">
            <Button
              variant="ghost"
              size="sm"
              onClick={expandAll}
              className="text-xs text-slate-400"
            >
              <Maximize2 className="w-3 h-3 mr-1" />
              Expand All
            </Button>
            <Button
              variant="ghost"
              size="sm"
              onClick={collapseAll}
              className="text-xs text-slate-400"
            >
              <Minimize2 className="w-3 h-3 mr-1" />
              Collapse All
            </Button>
          </div>
        </Panel>
        
        {/* Stats */}
        <Panel position="top-right" className="bg-slate-900/90 p-3 rounded-lg border border-slate-700">
          <div className="text-xs text-slate-400 space-y-1">
            <div className="flex items-center gap-2">
              <Folder className="w-3 h-3" />
              <span>{expandedGroups.size} groups expanded</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-2 h-2 rounded-full bg-green-500" />
              <span>Recursive structure</span>
            </div>
          </div>
        </Panel>
      </ReactFlow>
    </div>
  );
}
