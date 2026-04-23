import { memo } from 'react';
import { Handle, Position, NodeProps } from 'reactflow';
import { 
  Mail, Mails, CreditCard, RotateCcw, Database, Trash2, 
  Github, Rocket, Slack, MessageCircle, AlertCircle 
} from 'lucide-react';

interface ActionNodeData {
  id: string;
  display_name: string;
  icon: string;
  color: string;
  risk: 'LOW' | 'MEDIUM' | 'HIGH';
  level: number;
  parentGroup: string;
}

const ICONS: Record<string, React.ComponentType<{ className?: string }>> = {
  Mail,
  Mails,
  CreditCard,
  RotateCcw,
  Database,
  Trash2,
  Github,
  Rocket,
  Slack,
  MessageCircle,
  AlertCircle,
};

const RISK_COLORS = {
  LOW: '#22c55e',
  MEDIUM: '#f59e0b',
  HIGH: '#ef4444',
};

function ActionNodeComponent({ data, selected }: NodeProps<ActionNodeData>) {
  const { display_name, icon, color, risk, level, parentGroup } = data;
  const Icon = ICONS[icon] || AlertCircle;
  const riskColor = RISK_COLORS[risk];
  
  const indent = level * 12;
  
  return (
    <div
      className={`
        relative min-w-[140px]
        bg-slate-900 border rounded-lg p-3
        shadow-lg transition-all duration-200
        ${selected ? 'ring-2 ring-white/20 scale-105' : ''}
      `}
      style={{ 
        borderColor: riskColor + '40',
        marginLeft: indent,
      }}
    >
      {/* Risk indicator */}
      <div 
        className="absolute -top-1 -right-1 w-3 h-3 rounded-full border-2 border-slate-900"
        style={{ backgroundColor: riskColor }}
      />
      
      {/* Header */}
      <div className="flex items-center gap-2">
        <div
          className="w-8 h-8 rounded-lg flex items-center justify-center"
          style={{ backgroundColor: color + '20' }}
        >
          <Icon className="w-4 h-4" style={{ color }} />
        </div>
        
        <span className="text-sm font-medium text-slate-200 truncate">
          {display_name}
        </span>
      </div>
      
      {/* Risk badge */}
      <div className="mt-2 flex items-center gap-1.5">
        <div
          className="px-2 py-0.5 rounded text-[10px] font-medium uppercase tracking-wider"
          style={{ 
            backgroundColor: riskColor + '20',
            color: riskColor,
          }}
        >
          {risk}
        </div>
        <span className="text-[10px] text-slate-500">
          in {parentGroup}
        </span>
      </div>
      
      {/* Handles */}
      <Handle
        type="target"
        position={Position.Left}
        className="w-2 h-2 !bg-slate-500 !border-2 !border-slate-800"
      />
      <Handle
        type="source"
        position={Position.Right}
        className="w-2 h-2 !bg-slate-500 !border-2 !border-slate-800"
      />
    </div>
  );
}

export const ActionNode = memo(ActionNodeComponent);
