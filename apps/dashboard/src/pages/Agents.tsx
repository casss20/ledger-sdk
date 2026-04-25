import { useState, useEffect } from 'react';
import { Shield, Fingerprint, AlertTriangle, CheckCircle, XCircle, TrendingUp } from 'lucide-react';
import { agentIdentityApi } from '../api/client';

interface AgentIdentity {
  agent_id: string;
  tenant_id: string;
  public_key: string;
  trust_level: string;
  verification_status: string;
  created_at: string;
  last_verified_at?: string;
}

interface TrustScore {
  agent_id: string;
  score: number;
  level: string;
  factors: Record<string, number>;
}

export const Agents = () => {
  const [agents, setAgents] = useState<AgentIdentity[]>([]);
  const [trustScores, setTrustScores] = useState<Record<string, TrustScore>>({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const loadAgents = async () => {
      try {
        setLoading(true);
        const response = await agentIdentityApi.list();
        setAgents(response.identities);

        // Load trust scores for each agent
        const scores: Record<string, TrustScore> = {};
        for (const agent of response.identities) {
          try {
            const trust = await agentIdentityApi.trust(agent.agent_id);
            scores[agent.agent_id] = trust;
          } catch {
            // Skip if trust score not available
          }
        }
        setTrustScores(scores);
        setError(null);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load agents');
      } finally {
        setLoading(false);
      }
    };

    loadAgents();
  }, []);

  const handleRevoke = async (agentId: string) => {
    if (!confirm(`Revoke identity for ${agentId}? This cannot be undone.`)) return;
    try {
      await agentIdentityApi.revoke(agentId, 'Revoked via dashboard');
      setAgents(prev => prev.filter(a => a.agent_id !== agentId));
    } catch (err) {
      alert(`Failed to revoke: ${err instanceof Error ? err.message : 'Unknown error'}`);
    }
  };

  const getTrustColor = (level: string) => {
    switch (level) {
      case 'highly_trusted': return 'text-emerald-400 bg-emerald-400/10 border-emerald-400/20';
      case 'trusted': return 'text-blue-400 bg-blue-400/10 border-blue-400/20';
      case 'standard': return 'text-yellow-400 bg-yellow-400/10 border-yellow-400/20';
      case 'unverified': return 'text-orange-400 bg-orange-400/10 border-orange-400/20';
      case 'revoked': return 'text-red-400 bg-red-400/10 border-red-400/20';
      default: return 'text-slate-400 bg-slate-400/10 border-slate-400/20';
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'verified': return <CheckCircle size={16} className="text-emerald-400" />;
      case 'revoked': return <XCircle size={16} className="text-red-400" />;
      default: return <AlertTriangle size={16} className="text-orange-400" />;
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-indigo-400" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-6 rounded-3xl bg-red-900/20 border border-red-800/50">
        <div className="flex items-center gap-2 text-red-400">
          <AlertTriangle size={20} />
          <span className="font-medium">{error}</span>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-black text-white">Agent Identities</h1>
          <p className="text-sm text-slate-500 mt-1">
            {agents.length} registered • {agents.filter(a => a.verification_status === 'verified').length} verified
          </p>
        </div>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        {[
          { label: 'Total', value: agents.length, icon: Fingerprint, color: 'text-blue-400' },
          { label: 'Verified', value: agents.filter(a => a.verification_status === 'verified').length, icon: CheckCircle, color: 'text-emerald-400' },
          { label: 'Revoked', value: agents.filter(a => a.verification_status === 'revoked').length, icon: XCircle, color: 'text-red-400' },
          { label: 'Avg Trust', value: `${Math.round(Object.values(trustScores).reduce((a, b) => a + b.score, 0) / Math.max(Object.values(trustScores).length, 1) * 100)}%`, icon: TrendingUp, color: 'text-indigo-400' },
        ].map((stat, i) => (
          <div key={i} className="p-4 rounded-2xl bg-slate-900/40 border border-slate-800/50">
            <div className={`p-2 rounded-lg bg-slate-800/50 w-fit ${stat.color}`}>
              <stat.icon size={18} />
            </div>
            <p className="text-xl font-black text-white mt-3">{stat.value}</p>
            <p className="text-xs text-slate-500">{stat.label}</p>
          </div>
        ))}
      </div>

      {/* Agents Table */}
      <div className="rounded-3xl bg-slate-900/40 border border-slate-800/50 overflow-hidden">
        <table className="w-full">
          <thead>
            <tr className="border-b border-slate-800/50">
              <th className="px-6 py-4 text-left text-xs font-bold text-slate-500 uppercase tracking-wider">Agent</th>
              <th className="px-6 py-4 text-left text-xs font-bold text-slate-500 uppercase tracking-wider">Status</th>
              <th className="px-6 py-4 text-left text-xs font-bold text-slate-500 uppercase tracking-wider">Trust Level</th>
              <th className="px-6 py-4 text-left text-xs font-bold text-slate-500 uppercase tracking-wider">Trust Score</th>
              <th className="px-6 py-4 text-left text-xs font-bold text-slate-500 uppercase tracking-wider">Created</th>
              <th className="px-6 py-4 text-right text-xs font-bold text-slate-500 uppercase tracking-wider">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-800/50">
            {agents.map(agent => {
              const trust = trustScores[agent.agent_id];
              return (
                <tr key={agent.agent_id} className="hover:bg-slate-800/30 transition-colors">
                  <td className="px-6 py-4">
                    <div className="flex items-center gap-3">
                      <div className="p-2 rounded-lg bg-slate-800/50">
                        <Shield size={16} className="text-indigo-400" />
                      </div>
                      <div>
                        <p className="text-sm font-medium text-white">{agent.agent_id}</p>
                        <p className="text-xs text-slate-500">{agent.tenant_id}</p>
                      </div>
                    </div>
                  </td>
                  <td className="px-6 py-4">
                    <div className="flex items-center gap-2">
                      {getStatusIcon(agent.verification_status)}
                      <span className="text-xs font-medium text-slate-300 capitalize">{agent.verification_status}</span>
                    </div>
                  </td>
                  <td className="px-6 py-4">
                    <span className={`inline-flex items-center px-2.5 py-1 rounded-full text-xs font-medium border ${getTrustColor(agent.trust_level)}`}>
                      {agent.trust_level}
                    </span>
                  </td>
                  <td className="px-6 py-4">
                    {trust ? (
                      <div className="flex items-center gap-2">
                        <div className="w-16 h-2 rounded-full bg-slate-800 overflow-hidden">
                          <div
                            className="h-full rounded-full bg-indigo-400"
                            style={{ width: `${trust.score * 100}%` }}
                          />
                        </div>
                        <span className="text-xs text-slate-400">{Math.round(trust.score * 100)}%</span>
                      </div>
                    ) : (
                      <span className="text-xs text-slate-600">—</span>
                    )}
                  </td>
                  <td className="px-6 py-4">
                    <span className="text-xs text-slate-500">
                      {new Date(agent.created_at).toLocaleDateString()}
                    </span>
                  </td>
                  <td className="px-6 py-4 text-right">
                    <button
                      onClick={() => handleRevoke(agent.agent_id)}
                      disabled={agent.verification_status === 'revoked'}
                      className="px-3 py-1.5 rounded-lg text-xs font-medium bg-red-900/20 text-red-400 border border-red-800/50 hover:bg-red-900/40 disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
                    >
                      Revoke
                    </button>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
        {agents.length === 0 && (
          <div className="p-12 text-center">
            <Fingerprint size={32} className="text-slate-700 mx-auto mb-4" />
            <p className="text-sm text-slate-500">No agent identities registered yet</p>
          </div>
        )}
      </div>
    </div>
  );
};
