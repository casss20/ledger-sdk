import React, { useEffect, useMemo, useState } from 'react';
import { CheckCircle, Shield, SlidersHorizontal } from 'lucide-react';

import { api, type ApprovalThresholdPayload, type NoCodePolicy } from '../lib/api';
import { Button } from '../components/ui/Button';
import { Input } from '../components/ui/Input';

type Priority = ApprovalThresholdPayload['approval_priority'];

const priorities: Priority[] = ['medium', 'high', 'critical', 'low'];

export const Policies: React.FC = () => {
  const [threshold, setThreshold] = useState(70);
  const [priority, setPriority] = useState<Priority>('high');
  const [expiryHours, setExpiryHours] = useState(24);
  const [reason, setReason] = useState('High-risk agent action requires review');
  const [activePolicy, setActivePolicy] = useState<NoCodePolicy | null>(null);
  const [preview, setPreview] = useState<NoCodePolicy | null>(null);
  const [status, setStatus] = useState<string>('');
  const [isSaving, setIsSaving] = useState(false);

  const payload = useMemo<ApprovalThresholdPayload>(
    () => ({
      risk_score_threshold: threshold,
      approval_priority: priority,
      approval_expiry_hours: expiryHours,
      reason: reason.trim() || undefined,
    }),
    [expiryHours, priority, reason, threshold],
  );

  useEffect(() => {
    api
      .getApprovalThresholdPolicy()
      .then((policy) => {
        setActivePolicy(policy);
        const control = policy?.rules_json.control;
        if (control) {
          setThreshold(Number(control.risk_score_threshold ?? 70));
          setPriority((control.approval_priority as Priority) ?? 'high');
          setExpiryHours(Number(control.approval_expiry_hours ?? 24));
        }
      })
      .catch(() => setStatus('Policy service unavailable'));
  }, []);

  const handlePreview = async () => {
    setStatus('');
    const policy = await api.previewApprovalThresholdPolicy(payload);
    setPreview(policy);
  };

  const handleApply = async () => {
    setIsSaving(true);
    setStatus('');
    try {
      const policy = await api.applyApprovalThresholdPolicy(payload);
      setActivePolicy(policy);
      setPreview(policy);
      setStatus('Active policy updated');
    } finally {
      setIsSaving(false);
    }
  };

  const rule = (preview ?? activePolicy)?.rules_json.rules[0];

  return (
    <div className="space-y-6 animate-in fade-in duration-500">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-black text-white">Governance Policies</h1>
          <p className="text-sm text-slate-500 mt-1">Versioned runtime controls</p>
        </div>
        <SlidersHorizontal size={20} className="text-slate-500" />
      </div>

      <section className="grid grid-cols-1 xl:grid-cols-[minmax(0,1fr)_420px] gap-5">
        <div className="rounded-lg bg-slate-900/40 border border-slate-800/50 p-5">
          <div className="flex items-start justify-between gap-4">
            <div className="flex items-start gap-4">
              <div className="w-10 h-10 rounded-lg bg-orange-500/10 flex items-center justify-center flex-shrink-0">
                <Shield size={20} className="text-orange-500" />
              </div>
              <div>
                <h2 className="text-sm font-bold text-slate-200">Approval Threshold</h2>
                <p className="text-xs text-slate-500 mt-1">
                  Require review for actions above a selected risk score.
                </p>
              </div>
            </div>
            {activePolicy && (
              <span className="px-2 py-0.5 rounded text-[10px] font-bold uppercase bg-emerald-500/10 text-emerald-500">
                active
              </span>
            )}
          </div>

          <div className="mt-6 grid grid-cols-1 md:grid-cols-3 gap-4">
            <label className="space-y-2">
              <span className="text-[11px] font-bold uppercase text-slate-500">Risk score</span>
              <Input
                min={0}
                max={100}
                type="number"
                value={threshold}
                onChange={(event) => setThreshold(Number(event.target.value))}
              />
            </label>

            <label className="space-y-2">
              <span className="text-[11px] font-bold uppercase text-slate-500">Priority</span>
              <select
                className="text-input"
                value={priority}
                onChange={(event) => setPriority(event.target.value as Priority)}
              >
                {priorities.map((item) => (
                  <option key={item} value={item}>
                    {item}
                  </option>
                ))}
              </select>
            </label>

            <label className="space-y-2">
              <span className="text-[11px] font-bold uppercase text-slate-500">Expires hours</span>
              <Input
                min={1}
                max={168}
                type="number"
                value={expiryHours}
                onChange={(event) => setExpiryHours(Number(event.target.value))}
              />
            </label>
          </div>

          <label className="mt-4 block space-y-2">
            <span className="text-[11px] font-bold uppercase text-slate-500">Approval reason</span>
            <Input value={reason} onChange={(event) => setReason(event.target.value)} />
          </label>

          <div className="mt-5 flex flex-wrap items-center gap-3">
            <Button type="button" variant="secondary" onClick={handlePreview}>
              Preview rule
            </Button>
            <Button type="button" onClick={handleApply} disabled={isSaving}>
              {isSaving ? 'Saving' : 'Activate version'}
            </Button>
            {status && <span className="text-xs text-slate-400">{status}</span>}
          </div>
        </div>

        <aside className="rounded-lg bg-slate-950/50 border border-slate-800/50 p-5">
          <div className="flex items-center gap-2">
            <CheckCircle size={16} className="text-emerald-500" />
            <h2 className="text-sm font-bold text-slate-200">Generated Rule</h2>
          </div>

          {rule ? (
            <dl className="mt-5 space-y-4">
              <div>
                <dt className="text-[10px] font-bold uppercase text-slate-500">Condition</dt>
                <dd className="mt-1 text-sm text-slate-200 font-mono">{rule.condition}</dd>
              </div>
              <div>
                <dt className="text-[10px] font-bold uppercase text-slate-500">Effect</dt>
                <dd className="mt-1 text-sm text-slate-200">{rule.effect}</dd>
              </div>
              <div>
                <dt className="text-[10px] font-bold uppercase text-slate-500">Version</dt>
                <dd className="mt-1 text-sm text-slate-200">{(preview ?? activePolicy)?.version}</dd>
              </div>
              <div>
                <dt className="text-[10px] font-bold uppercase text-slate-500">Reason</dt>
                <dd className="mt-1 text-sm text-slate-300">{rule.reason}</dd>
              </div>
            </dl>
          ) : (
            <p className="mt-5 text-sm text-slate-500">No active threshold policy.</p>
          )}
        </aside>
      </section>
    </div>
  );
};
