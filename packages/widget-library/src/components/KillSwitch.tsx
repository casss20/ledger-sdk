import React, { useState } from 'react';
import { Power, AlertTriangle, ShieldCheck, RefreshCw } from 'lucide-react';
import { cn } from '../lib/utils';

export interface KillSwitchProps {
  isActive: boolean;
  onToggle: (state: boolean) => Promise<void>;
  label?: string;
  className?: string;
}

export const KillSwitch: React.FC<KillSwitchProps> = ({ isActive, onToggle, label = "Global Governance Lock", className }) => {
  const [isPending, setIsPending] = useState(false);

  const handleToggle = async () => {
    setIsPending(true);
    try {
      await onToggle(!isActive);
    } finally {
      setIsPending(false);
    }
  };

  return (
    <div className={cn(
      "group relative p-6 rounded-3xl border transition-all duration-500 overflow-hidden",
      isActive 
        ? "bg-red-500/10 border-red-500/30 shadow-[0_0_40px_-15px_rgba(239,68,68,0.3)]" 
        : "bg-slate-900/60 border-slate-800",
      className
    )}>
      {/* Background Glow */}
      <div className={cn(
        "absolute -inset-24 opacity-20 blur-3xl transition-colors duration-1000",
        isActive ? "bg-red-500" : "bg-emerald-500"
      )} />

      <div className="relative flex flex-col items-center gap-6 text-center">
        <div className={cn(
          "flex items-center justify-center w-16 h-16 rounded-2xl border-2 transition-all duration-500",
          isActive 
            ? "bg-red-500 border-red-400 text-white shadow-lg shadow-red-500/40 animate-pulse" 
            : "bg-slate-800 border-slate-700 text-slate-400"
        )}>
          {isActive ? <Power size={32} /> : <ShieldCheck size={32} />}
        </div>

        <div>
          <h3 className={cn(
            "text-xl font-black uppercase tracking-tighter transition-colors duration-500",
            isActive ? "text-red-400" : "text-slate-200"
          )}>
            {isActive ? "Execution Locked" : label}
          </h3>
          <p className="text-xs text-slate-500 mt-2 max-w-[200px] leading-relaxed">
            {isActive 
              ? "All non-vital agent actions are currently suspended by global mandate." 
              : "Autonomous execution is enabled. One-click to suspend all activity."}
          </p>
        </div>

        <button
          disabled={isPending}
          onClick={handleToggle}
          className={cn(
            "relative w-full py-4 rounded-2xl font-black text-sm uppercase tracking-widest transition-all duration-300 active:scale-95 disabled:opacity-50",
            isActive
              ? "bg-slate-100 text-red-600 hover:bg-white"
              : "bg-red-600 text-white hover:bg-red-500 shadow-xl shadow-red-900/20"
          )}
        >
          {isPending ? (
            <RefreshCw className="animate-spin mx-auto" size={18} />
          ) : (
            isActive ? "Disengage Lock" : "Engage Kill Switch"
          )}
        </button>

        {isActive && (
          <div className="flex items-center gap-2 text-[10px] font-bold text-red-500/80 uppercase">
            <AlertTriangle size={12} />
            Immediate Intervention Active
          </div>
        )}
      </div>
    </div>
  );
};
