import { memo } from 'react';
import { Handle, Position, NodeProps } from 'reactflow';
import { Bot, Shield, Users, Gauge, Mail, CreditCard, Database, FileText, AlertCircle } from 'lucide-react';

const ICONS: Record<string, React.ComponentType<{ className?: string }>> = {
  Bot,
  Shield,
  Users,
  Gauge,
  Mail,
  CreditCard,
  Database,
  FileText,
};

interface CustomNodeData {
  label: string;
  icon: string;
  color: string;
  description: string;
  status: 'active' | 'processing' | 'pending' | 'blocked' | 'ok';
  badge?: string;
  group?: string;
}

function CustomNodeComponent({ data, selected }: NodeProps<CustomNodeData>) {
  const Icon = ICONS[data.icon] || AlertCircle;
  
  const statusColors = {
    active: 'border-green-500/50 shadow-green-500/20',
    processing: 'border-blue-500/50 shadow-blue-500/20 animate-pulse',
    pending: 'border-yellow-500/50 shadow-yellow-500/20',
    blocked: 'border-red-500/50 shadow-red-500/20',
    ok: 'border-slate-500/50',
  };

  return (
    <div
      className={`
        relative min-w-[140px] max-w-[180px]
        bg-slate-900 border-2 rounded-lg p-3
        shadow-lg transition-all duration-200
        ${selected ? 'ring-2 ring-white/20 scale-105' : ''}
        ${statusColors[data.status]}
      `}
      style={{ borderColor: data.color + '40' }}
    >
      {/* Badge */}
      {data.badge && (
        <div className="absolute -top-2 -right-2 w-5 h-5 bg-red-500 rounded-full flex items-center justify-center text-xs font-bold text-white">
          {data.badge}
        </div>
      )}

      {/* Header */}
      <div className="flex items-center gap-2 mb-2">
        <div
          className="w-8 h-8 rounded-lg flex items-center justify-center"
          style={{ backgroundColor: data.color + '20' }}
        >
          <Icon className="w-4 h-4" style={{ color: data.color }} />
        </div>
        <span className="text-sm font-semibold text-slate-200 truncate">
          {data.label}
        </span>
      </div>

      {/* Description */}
      <div className="text-xs text-slate-400 leading-tight">
        {data.description}
      </div>

      {/* Status indicator */}
      <div className="mt-2 flex items-center gap-1.5">
        <div
          className="w-2 h-2 rounded-full"
          style={{
            backgroundColor:
              data.status === 'active' || data.status === 'ok'
                ? '#22c55e'
                : data.status === 'processing'
                ? '#3b82f6'
                : data.status === 'pending'
                ? '#f59e0b'
                : '#ef4444',
          }}
        />
        <span className="text-xs capitalize text-slate-500">{data.status}</span>
      </div>

      {/* Group tag */}
      {data.group && (
        <div className="mt-2 text-[10px] uppercase tracking-wider text-slate-600">
          {data.group}
        </div>
      )}

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

export const CustomNode = memo(CustomNodeComponent);
