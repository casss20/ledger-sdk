import React from 'react';
import { AlertTriangle, Shield, Info, Clock } from 'lucide-react';

export interface ActivityEvent {
  id: string;
  timestamp: string;
  severity: 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW';
  type: string;
  summary: string;
  agentId: string;
  actionable: boolean;
}

interface Props {
  events: ActivityEvent[];
}

export const ActivityStream: React.FC<Props> = ({ events }) => {
  const getIcon = (severity: string) => {
    switch (severity) {
      case 'CRITICAL': return <AlertTriangle size={14} className="text-red-500" />;
      case 'HIGH': return <AlertTriangle size={14} className="text-orange-500" />;
      case 'MEDIUM': return <Info size={14} className="text-amber-500" />;
      default: return <Shield size={14} className="text-emerald-500" />;
    }
  };

  const getBadgeColor = (severity: string) => {
    switch (severity) {
      case 'CRITICAL': return 'bg-red-500/10 text-red-400 border-red-500/20';
      case 'HIGH': return 'bg-orange-500/10 text-orange-400 border-orange-500/20';
      case 'MEDIUM': return 'bg-amber-500/10 text-amber-400 border-amber-500/20';
      default: return 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20';
    }
  };

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-sm font-bold text-slate-200 uppercase tracking-tight">Live Activity Stream</h3>
        <span className="text-[10px] text-slate-500">{events.length} events</span>
      </div>
      <div className="space-y-2 max-h-[400px] overflow-y-auto">
        {events.map((event) => (
          <div key={event.id} className="flex items-start gap-3 p-3 rounded-xl bg-slate-950/50 border border-slate-800/50 hover:border-slate-700/50 transition-all">
            <div className="mt-0.5">{getIcon(event.severity)}</div>
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2 mb-1">
                <span className={`px-1.5 py-0.5 rounded text-[10px] font-bold uppercase border ${getBadgeColor(event.severity)}`}>
                  {event.severity}
                </span>
                <span className="text-[10px] text-slate-500 font-mono">{event.type}</span>
              </div>
              <p className="text-xs text-slate-300 font-medium">{event.summary}</p>
              <div className="flex items-center gap-2 mt-1.5">
                <span className="text-[10px] text-slate-500">{event.agentId}</span>
                <span className="text-[10px] text-slate-600">•</span>
                <span className="text-[10px] text-slate-500 flex items-center gap-1">
                  <Clock size={10} />
                  {new Date(event.timestamp).toLocaleTimeString()}
                </span>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};
