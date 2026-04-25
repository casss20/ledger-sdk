import { memo } from 'react';
import { Handle, Position, NodeProps } from 'reactflow';
import { Folder, ChevronDown, ChevronRight, Layers } from 'lucide-react';

interface GroupNodeData {
  id: string;
  name: string;
  display_name: string;
  icon: string;
  color: string;
  type: 'group';
  collapsed: boolean;
  isExpanded: boolean;
  child_count: number;
  subgroup_count?: number;
  action_count?: number;
  level: number;
  onToggle: () => void;
}

// Icon mapping
const IconMap: Record<string, React.ComponentType<{ className?: string }>> = {
  Folder,
  Layers,
};

function GroupNodeComponent({ data, selected }: NodeProps<GroupNodeData>) {
  const { 
    display_name, 
    icon, 
    color, 
    isExpanded, 
    child_count, 
    subgroup_count = 0,
    action_count = 0,
    level,
    onToggle 
  } = data;
  
  const Icon = IconMap[icon] || Folder;
  const hasChildren = child_count > 0;
  
  // Indent based on level
  const indent = level * 12;
  
  return (
    <div
      className={`
        relative min-w-[160px]
        bg-slate-900 border-2 rounded-lg p-3
        shadow-lg transition-all duration-200
        ${selected ? 'ring-2 ring-white/20 scale-105' : ''}
        ${isExpanded ? 'border-slate-600' : 'border-dashed border-slate-700'}
      `}
      style={{ 
        borderColor: isExpanded ? color + '60' : color + '30',
        marginLeft: indent,
      }}
    >
      {/* Header with expand/collapse */}
      <div className="flex items-center gap-2">
        {hasChildren && (
          <button
            onClick={onToggle}
            className="w-5 h-5 flex items-center justify-center rounded hover:bg-slate-800 transition-colors"
          >
            {isExpanded ? (
              <ChevronDown className="w-4 h-4 text-slate-400" />
            ) : (
              <ChevronRight className="w-4 h-4 text-slate-400" />
            )}
          </button>
        )}
        
        <div
          className="w-8 h-8 rounded-lg flex items-center justify-center"
          style={{ backgroundColor: color + '20' }}
        >
          <Icon className="w-4 h-4" style={{ color }} />
        </div>
        
        <div className="flex-1 min-w-0">
          <div className="text-sm font-semibold text-slate-200 truncate">
            {display_name}
          </div>
          <div className="text-xs text-slate-500">
            {child_count} {child_count === 1 ? 'child' : 'children'}
          </div>
        </div>
      </div>
      
      {/* Breakdown */}
      {isExpanded && (
        <div className="mt-2 pt-2 border-t border-slate-700/50 flex gap-3 text-xs">
          {subgroup_count > 0 && (
            <span className="text-slate-400">
              <span className="text-slate-300 font-medium">{subgroup_count}</span> subgroups
            </span>
          )}
          {action_count > 0 && (
            <span className="text-slate-400">
              <span className="text-slate-300 font-medium">{action_count}</span> actions
            </span>
          )}
        </div>
      )}
      
      {/* Level indicator */}
      <div className="absolute -left-1 top-1/2 -translate-y-1/2 w-1 h-8 rounded-full" 
        style={{ backgroundColor: color }}
      />
      
      {/* Handles */}
      <Handle
        type="target"
        position={Position.Left}
        className="w-3 h-3 !bg-slate-600 !border-2 !border-slate-800"
      />
      <Handle
        type="source"
        position={Position.Right}
        className="w-3 h-3 !bg-slate-600 !border-2 !border-slate-800"
      />
    </div>
  );
}

export const GroupNode = memo(GroupNodeComponent);
