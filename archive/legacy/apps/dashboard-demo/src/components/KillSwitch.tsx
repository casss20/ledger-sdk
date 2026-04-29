import React, { useState } from 'react';
import { Lock, Unlock, Shield } from 'lucide-react';

interface Props {
  isActive: boolean;
  onToggle: (state: boolean) => Promise<void>;
}

export const KillSwitch: React.FC<Props> = ({ isActive, onToggle }) => {
  const [loading, setLoading] = useState(false);

  const handleToggle = async () => {
    setLoading(true);
    await onToggle(!isActive);
    setLoading(false);
  };

  return (
    <div className={`p-6 rounded-3xl border backdrop-blur-sm transition-all ${
      isActive 
        ? 'bg-red-950/30 border-red-500/30' 
        : 'bg-slate-900/40 border-slate-800/50'
    }`}>
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-2">
          <Shield size={18} className={isActive ? 'text-red-400' : 'text-emerald-400'} />
          <h3 className="text-sm font-bold text-slate-200 uppercase tracking-tight">Emergency Kill Switch</h3>
        </div>
        <div className={`w-2 h-2 rounded-full ${isActive ? 'bg-red-500 animate-pulse' : 'bg-emerald-500'}`} />
      </div>

      <div className="text-center py-4">
        {isActive ? (
          <Lock size={48} className="text-red-500 mx-auto mb-3" />
        ) : (
          <Unlock size={48} className="text-emerald-500 mx-auto mb-3" />
        )}
        <p className={`text-lg font-bold mb-1 ${isActive ? 'text-red-400' : 'text-emerald-400'}`}>
          {isActive ? 'SYSTEM LOCKED' : 'SYSTEM ACTIVE'}
        </p>
        <p className="text-xs text-slate-500">
          {isActive 
            ? 'All agent actions are currently blocked' 
            : 'Governance system operating normally'}
        </p>
      </div>

      <button
        onClick={handleToggle}
        disabled={loading}
        className={`w-full mt-4 py-3 rounded-xl font-bold text-sm transition-all ${
          isActive
            ? 'bg-emerald-600 hover:bg-emerald-500 text-white'
            : 'bg-red-600 hover:bg-red-500 text-white'
        } disabled:opacity-50`}
      >
        {loading ? 'Processing...' : isActive ? 'Unlock System' : 'Engage Lock'}
      </button>
    </div>
  );
};
