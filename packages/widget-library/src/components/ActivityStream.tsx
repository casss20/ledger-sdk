import React from 'react';
import { AlertCircle, CheckCircle2, ShieldAlert, Clock, Info, ExternalLink } from 'lucide-react';
import { cn } from '../lib/utils';

export interface ActivityEvent {
  id: string;
  timestamp: string;
  severity: 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW' | 'INFO';
  type: string;
  agentId?: string;
  summary: string;
  actionable: boolean;
}

export interface ActivityStreamProps {
  events: ActivityEvent[];
  className?: string;
  onEventClick?: (event: ActivityEvent) => void;
}

const severityConfig = {
  CRITICAL: {
    icon: ShieldAlert,
    color: 'text-red-500 bg-red-500/10 border-red-500/20',
    dot: 'bg-red-500',
  },
  HIGH: {
    icon: AlertCircle,
    color: 'text-orange-500 bg-orange-500/10 border-orange-500/20',
    dot: 'bg-orange-500',
  },
  MEDIUM: {
    icon: Clock,
    color: 'text-yellow-500 bg-yellow-500/10 border-yellow-500/20',
    dot: 'bg-yellow-500',
  },
  LOW: {
    icon: CheckCircle2,
    color: 'text-emerald-500 bg-emerald-500/10 border-emerald-500/20',
    dot: 'bg-emerald-500',
  },
  INFO: {
    icon: Info,
    color: 'text-blue-500 bg-blue-500/10 border-blue-500/20',
    dot: 'bg-blue-500',
  },
};

export const ActivityStream: React.FC<ActivityStreamProps> = ({ events, className, onEventClick }) => {
  return (
    <div className={cn('flex flex-col gap-4', className)}>
      <div className="flex items-center justify-between px-2 mb-2">
        <h3 className="text-lg font-semibold text-slate-100">Governance Activity</h3>
        <span className="text-xs font-medium text-slate-400 bg-slate-800/50 px-2 py-1 rounded-full border border-slate-700/50">
          Live Feed
        </span>
      </div>
      
      <div className="relative space-y-3">
        {/* Timeline track */}
        <div className="absolute left-6 top-2 bottom-2 w-px bg-slate-800" />
        
        {events.map((event) => {
          const config = severityConfig[event.severity];
          const Icon = config.icon;
          
          return (
            <div
              key={event.id}
              onClick={() => onEventClick?.(event)}
              className={cn(
                "group relative flex gap-4 p-3 rounded-xl border transition-all duration-200 cursor-pointer",
                "bg-slate-900/40 border-slate-800 hover:border-slate-700 hover:bg-slate-900/60",
                "backdrop-blur-sm shadow-sm hover:shadow-md"
              )}
            >
              <div className="relative z-10 flex-shrink-0">
                <div className={cn("flex items-center justify-center w-8 h-8 rounded-lg border", config.color)}>
                  <Icon size={16} />
                </div>
                <div className={cn("absolute -bottom-1 -right-1 w-3 h-3 rounded-full border-2 border-slate-900", config.dot)} />
              </div>
              
              <div className="flex-1 min-w-0">
                <div className="flex items-start justify-between gap-2">
                  <span className="text-sm font-medium text-slate-200 truncate">
                    {event.summary}
                  </span>
                  <span className="text-[10px] font-medium text-slate-500 tabular-nums whitespace-nowrap mt-1">
                    {new Date(event.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                  </span>
                </div>
                
                <div className="mt-1 flex items-center gap-3">
                  <span className="text-xs text-slate-400 font-mono">
                    {event.agentId || 'system'}
                  </span>
                  <span className="w-1 h-1 rounded-full bg-slate-700" />
                  <span className="text-xs text-slate-500 capitalize">
                    {event.type.replace('.', ' ')}
                  </span>
                </div>
              </div>
              
              <div className="opacity-0 group-hover:opacity-100 transition-opacity">
                <ExternalLink size={14} className="text-slate-500" />
              </div>
            </div>
          );
        })}
        
        {events.length === 0 && (
          <div className="flex flex-col items-center justify-center py-12 px-4 rounded-2xl border border-dashed border-slate-800 text-slate-500">
            <Info size={32} className="mb-3 opacity-20" />
            <p className="text-sm font-medium">No governance events in this window</p>
          </div>
        )}
      </div>
    </div>
  );
};
