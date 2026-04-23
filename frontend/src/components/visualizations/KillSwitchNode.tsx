import { memo } from 'react';
import { Handle, Position } from 'reactflow';
import type { NodeProps } from 'reactflow';
import { Power, PowerOff, AlertTriangle } from 'lucide-react';

interface KillSwitchData {
  label: string;
  switches: Array<{
    name: string;
    active: boolean;
  }>;
}

function KillSwitchNodeComponent({ data }: NodeProps<KillSwitchData>) {
  const activeCount = data.switches.filter((s) => s.active).length;
  const totalCount = data.switches.length;

  return (
    <div className="min-w-[160px] bg-slate-900 border-2 border-red-500/30 rounded-lg p-3 shadow-lg shadow-red-500/10">
      <div className="flex items-center gap-2 mb-3">
        <div className="w-8 h-8 rounded-lg bg-red-500/20 flex items-center justify-center">
          {activeCount > 0 ? (
            <PowerOff className="w-4 h-4 text-red-500" />
          ) : (
            <Power className="w-4 h-4 text-green-500" />
          )}
        </div>
        <span className="text-sm font-semibold text-slate-200">{data.label}</span>
      </div>

      <div className="space-y-1.5">
        {data.switches.map((sw) => (
          <div
            key={sw.name}
            className={`flex items-center justify-between text-xs px-2 py-1 rounded ${
              sw.active ? 'bg-red-500/10' : 'bg-slate-800'
            }`}
          >
            <span className={sw.active ? 'text-red-400' : 'text-slate-400'}>
              {sw.name}
            </span>
            {sw.active ? (
              <AlertTriangle className="w-3 h-3 text-red-500" />
            ) : (
              <div className="w-2 h-2 rounded-full bg-green-500" />
            )}
          </div>
        ))}
      </div>

      <div className="mt-3 pt-2 border-t border-slate-700 text-xs text-slate-500">
        {activeCount}/{totalCount} active
      </div>

      <Handle type="target" position={Position.Left} className="w-3 h-3 !bg-red-500 !border-2 !border-slate-800" />
      <Handle type="source" position={Position.Right} className="w-3 h-3 !bg-red-500 !border-2 !border-slate-800" />
    </div>
  );
}

export const KillSwitchNode = memo(KillSwitchNodeComponent);
