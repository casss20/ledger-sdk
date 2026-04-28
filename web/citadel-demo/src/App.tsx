import { useState, useEffect, useRef } from 'react'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Separator } from '@/components/ui/separator'
import './App.css'

// ── Design tokens ────────────────────────────────────────────────────────────
const C = {
  accent:    '#5E6AD2',
  accentDim: 'rgba(94,106,210,0.12)',
  success:   '#2D8A4E',
  successBg: 'rgba(45,138,78,0.08)',
  warning:   '#B87A0A',
  warningBg: 'rgba(184,122,10,0.08)',
  error:     '#C43030',
  errorBg:   'rgba(196,48,48,0.08)',
  info:      '#1E6FAF',
  infoBg:    'rgba(30,111,175,0.08)',
  border:    '#E5E7EB',
  dark:      '#0F1117',
}

// ── Types ─────────────────────────────────────────────────────────────────────
type KernelStatus =
  | 'executed' | 'allowed' | 'dry_run' | 'pending_approval'
  | 'rejected_approval' | 'expired_approval'
  | 'blocked_policy' | 'blocked_emergency' | 'blocked_capability'
  | 'blocked_schema' | 'rate_limited' | 'failed_execution' | 'failed_audit'

type TrustBand = 'REVOKED' | 'PROBATION' | 'STANDARD' | 'TRUSTED' | 'HIGHLY_TRUSTED'
type StageStatus = 'idle' | 'running' | 'pass' | 'fail' | 'warn'

interface Decision {
  status: KernelStatus
  winning_rule: string
  reason: string
  trust_score: number
  trust_band: TrustBand
  action_id: string
  audit_hash: string
  latency_ms: number
}

interface StageDef {
  id: string
  label: string
  detail: string
  finalStatus: StageStatus
  ms: number
}

interface Stage {
  id: string
  label: string
  detail: string
  status: StageStatus
  ms?: number
}

// ── Scenarios ─────────────────────────────────────────────────────────────────
const SCENARIOS = [
  {
    label: 'Price update — standard',
    actor_id: 'pricing-engine-v2',
    actor_type: 'agent',
    action_name: 'price.update',
    resource: 'product/SKU-8821',
    payload: '{"new_price": 149.99}',
    outcome: 'executed' as KernelStatus,
    rule: 'policy_allow_standard',
    reason: 'Within policy thresholds. Actor trust score acceptable.',
    trust_score: 0.74,
    trust_band: 'TRUSTED' as TrustBand,
  },
  {
    label: 'Access EU citizen PII',
    actor_id: 'data-pipeline-v3',
    actor_type: 'agent',
    action_name: 'db.query',
    resource: 'users/eu-segment',
    payload: '{"filter": "gdpr_region=EU", "fields": ["email","dob"]}',
    outcome: 'pending_approval' as KernelStatus,
    rule: 'gdpr_article22_human_oversight',
    reason: 'EU AI Act Art. 14 — access to EU citizen PII requires human review before execution.',
    trust_score: 0.61,
    trust_band: 'TRUSTED' as TrustBand,
  },
  {
    label: 'Deploy policy to production',
    actor_id: 'compliance-sentinel',
    actor_type: 'agent',
    action_name: 'policy.deploy',
    resource: 'policy/pii-handler-v3',
    payload: '{"env": "production", "rollout": "immediate"}',
    outcome: 'pending_approval' as KernelStatus,
    rule: 'policy_deploy_prod_requires_approval',
    reason: 'Production deployments require senior engineer approval when policy affects PII scope.',
    trust_score: 0.82,
    trust_band: 'HIGHLY_TRUSTED' as TrustBand,
  },
  {
    label: 'Kill switch active — halted',
    actor_id: 'workflow-orchestrator',
    actor_type: 'agent',
    action_name: 'file.write',
    resource: 'fs/contracts/Q2-2026.pdf',
    payload: '{"content": "..."}',
    outcome: 'blocked_emergency' as KernelStatus,
    rule: 'ks_tenant_freeze_active',
    reason: 'Tenant-level kill switch is armed. All new submissions are blocked immediately.',
    trust_score: 0.55,
    trust_band: 'STANDARD' as TrustBand,
  },
  {
    label: 'Schema violation',
    actor_id: 'audit-agent-01',
    actor_type: 'agent',
    action_name: 'model.invoke',
    resource: 'llm/gpt-4o',
    payload: '{"prompt": 1234}',
    outcome: 'blocked_schema' as KernelStatus,
    rule: 'schema_validation_fail',
    reason: 'Payload field "prompt" must be string, received number (1234). Action rejected before policy evaluation.',
    trust_score: 0.68,
    trust_band: 'TRUSTED' as TrustBand,
  },
  {
    label: 'Rate limit exceeded',
    actor_id: 'content-mod-03',
    actor_type: 'agent',
    action_name: 'api.external_write',
    resource: 'stripe/charges',
    payload: '{"amount": 9900, "currency": "usd"}',
    outcome: 'rate_limited' as KernelStatus,
    rule: 'rate_limit_external_api_1000ph',
    reason: 'Agent exceeded 1000 external API writes per hour threshold. Cooldown window: 4 minutes.',
    trust_score: 0.42,
    trust_band: 'STANDARD' as TrustBand,
  },
]

// ── Helpers ───────────────────────────────────────────────────────────────────
function statusConfig(s: KernelStatus) {
  const map: Record<KernelStatus, { color: string; bg: string; label: string }> = {
    executed:           { color: C.success, bg: C.successBg, label: 'EXECUTED' },
    allowed:            { color: C.success, bg: C.successBg, label: 'ALLOWED' },
    dry_run:            { color: C.info,    bg: C.infoBg,    label: 'DRY RUN' },
    pending_approval:   { color: C.warning, bg: C.warningBg, label: 'PENDING APPROVAL' },
    rejected_approval:  { color: C.error,   bg: C.errorBg,   label: 'REJECTED' },
    expired_approval:   { color: C.warning, bg: C.warningBg, label: 'EXPIRED' },
    blocked_policy:     { color: C.error,   bg: C.errorBg,   label: 'BLOCKED — POLICY' },
    blocked_emergency:  { color: C.error,   bg: C.errorBg,   label: 'BLOCKED — KILL SWITCH' },
    blocked_capability: { color: C.error,   bg: C.errorBg,   label: 'BLOCKED — CAPABILITY' },
    blocked_schema:     { color: C.error,   bg: C.errorBg,   label: 'BLOCKED — SCHEMA' },
    rate_limited:       { color: C.warning, bg: C.warningBg, label: 'RATE LIMITED' },
    failed_execution:   { color: C.error,   bg: C.errorBg,   label: 'FAILED EXECUTION' },
    failed_audit:       { color: C.error,   bg: C.errorBg,   label: 'FAILED AUDIT' },
  }
  return map[s]
}

function trustConfig(b: TrustBand) {
  const map: Record<TrustBand, { color: string }> = {
    REVOKED:        { color: C.error },
    PROBATION:      { color: C.warning },
    STANDARD:       { color: C.info },
    TRUSTED:        { color: C.success },
    HIGHLY_TRUSTED: { color: C.accent },
  }
  return map[b]
}

// ── Stage icon ─────────────────────────────────────────────────────────────────
function StageIcon({ status }: { status: StageStatus }) {
  if (status === 'running') {
    return (
      <svg className="animate-spin-custom" width={16} height={16} viewBox="0 0 16 16" fill="none" style={{ flexShrink: 0 }}>
        <circle cx="8" cy="8" r="6" stroke={C.accent} strokeWidth="2" strokeDasharray="28" strokeDashoffset="10" strokeLinecap="round"/>
      </svg>
    )
  }
  if (status === 'pass') return (
    <svg width={16} height={16} viewBox="0 0 16 16" fill="none" style={{ flexShrink: 0 }}>
      <circle cx="8" cy="8" r="7" fill={C.successBg} stroke={C.success} strokeWidth="1.2"/>
      <path d="M5 8l2 2 4-4" stroke={C.success} strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
    </svg>
  )
  if (status === 'fail') return (
    <svg width={16} height={16} viewBox="0 0 16 16" fill="none" style={{ flexShrink: 0 }}>
      <circle cx="8" cy="8" r="7" fill={C.errorBg} stroke={C.error} strokeWidth="1.2"/>
      <path d="M5.5 5.5l5 5M10.5 5.5l-5 5" stroke={C.error} strokeWidth="1.5" strokeLinecap="round"/>
    </svg>
  )
  if (status === 'warn') return (
    <svg width={16} height={16} viewBox="0 0 16 16" fill="none" style={{ flexShrink: 0 }}>
      <circle cx="8" cy="8" r="7" fill={C.warningBg} stroke={C.warning} strokeWidth="1.2"/>
      <path d="M8 5v4" stroke={C.warning} strokeWidth="1.5" strokeLinecap="round"/>
      <circle cx="8" cy="11" r="0.8" fill={C.warning}/>
    </svg>
  )
  return (
    <div style={{ width: 16, height: 16, flexShrink: 0, borderRadius: '50%', border: '1.5px solid #D1D5DB', background: '#F9FAFB' }}/>
  )
}

// ── App ────────────────────────────────────────────────────────────────────────
export default function App() {
  const [scenario, setScenario] = useState(SCENARIOS[0])
  const [actorId, setActorId]       = useState(SCENARIOS[0].actor_id)
  const [actorType, setActorType]   = useState(SCENARIOS[0].actor_type)
  const [actionName, setActionName] = useState(SCENARIOS[0].action_name)
  const [resource, setResource]     = useState(SCENARIOS[0].resource)
  const [payload, setPayload]       = useState(SCENARIOS[0].payload)

  const [stages, setStages]   = useState<Stage[]>([])
  const [decision, setDecision] = useState<Decision | null>(null)
  const [running, setRunning] = useState(false)
  const [runCount, setRunCount] = useState(0)
  const timers = useRef<ReturnType<typeof setTimeout>[]>([])

  function clearTimers() { timers.current.forEach(clearTimeout); timers.current = [] }
  function schedule(fn: () => void, ms: number) { timers.current.push(setTimeout(fn, ms)) }

  function applyScenario(s: typeof SCENARIOS[0]) {
    setScenario(s)
    setActorId(s.actor_id)
    setActorType(s.actor_type)
    setActionName(s.action_name)
    setResource(s.resource)
    setPayload(s.payload)
    setDecision(null)
    setStages([])
  }

  function runEval() {
    if (running) return
    clearTimers()
    setDecision(null)
    setRunning(true)
    setRunCount(c => c + 1)

    const s = scenario
    const isSchema   = s.outcome === 'blocked_schema'
    const isRate     = s.outcome === 'rate_limited'
    const isKS       = s.outcome === 'blocked_emergency'
    const isApproval = s.outcome === 'pending_approval'
    const isPolicy   = s.outcome === 'blocked_policy'

    const defs: StageDef[] = [
      { id: 'schema',   label: 'Schema validation',  detail: 'Validating payload structure and field types', finalStatus: isSchema ? 'fail' : 'pass', ms: 95  },
      { id: 'rate',     label: 'Rate limit check',   detail: `Checking per-actor submission frequency`,      finalStatus: isRate   ? 'fail' : 'pass', ms: 130 },
      { id: 'ks',       label: 'Kill switch scan',   detail: 'Scanning active kill switch scopes',           finalStatus: isKS     ? 'fail' : 'pass', ms: 75  },
      { id: 'trust',    label: 'Actor trust lookup', detail: `Resolving trust band for ${s.actor_id}`,       finalStatus: 'pass',                     ms: 175 },
      { id: 'policy',   label: 'Policy evaluation',  detail: 'Matching action against active rule set',      finalStatus: isPolicy ? 'fail' : isApproval ? 'warn' : 'pass', ms: 255 },
      { id: 'decision', label: 'Decision issued',    detail: 'Signing and persisting audit event',           finalStatus: 'pass',                     ms: 55  },
    ]

    // Where does the pipeline halt?
    let haltAt = defs.length - 1
    for (let i = 0; i < defs.length; i++) {
      if (defs[i].finalStatus === 'fail') { haltAt = i; break }
    }

    setStages(defs.map(d => ({ id: d.id, label: d.label, detail: d.detail, status: 'idle' })))

    let cursor = 0
    let elapsed = 0

    function tick() {
      const i = cursor
      if (i > haltAt) { setRunning(false); return }

      setStages(prev => prev.map((st, j) => j === i ? { ...st, status: 'running' } : st))

      const dur = defs[i].ms
      elapsed += dur

      schedule(() => {
        const fs: StageStatus = (i === haltAt && defs[i].finalStatus === 'fail') ? 'fail'
          : (defs[i].finalStatus === 'warn') ? 'warn'
          : 'pass'

        setStages(prev => prev.map((st, j) => j === i ? { ...st, status: fs, ms: dur } : st))
        cursor++

        const done = fs === 'fail' || cursor > haltAt
        if (done) {
          schedule(() => {
            setDecision({
              status: s.outcome,
              winning_rule: s.rule,
              reason: s.reason,
              trust_score: s.trust_score,
              trust_band: s.trust_band,
              action_id: Math.random().toString(36).slice(2, 10),
              audit_hash: Array.from({ length: 16 }, () => Math.floor(Math.random() * 16).toString(16)).join(''),
              latency_ms: elapsed + 18,
            })
            setRunning(false)
          }, 180)
        } else {
          schedule(tick, 28)
        }
      }, dur)
    }

    tick()
  }

  useEffect(() => () => clearTimers(), [])

  return (
    <div style={{ minHeight: '100dvh', background: '#F3F4F7' }}>

      {/* ── Header ─────────────────────────────────────────────────────────── */}
      <header style={{
        background: '#fff', borderBottom: '1px solid #E5E7EB',
        height: 52, display: 'flex', alignItems: 'center',
        padding: '0 24px', gap: 10,
        position: 'sticky', top: 0, zIndex: 50,
        boxShadow: '0 1px 0 #E5E7EB',
      }}>
        <div style={{ width: 26, height: 26, background: C.accent, borderRadius: 6, display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0 }}>
          <svg width="13" height="13" viewBox="0 0 14 14" fill="none">
            <path d="M7 1l5.5 3.15v5.7L7 13 1.5 9.85V4.15L7 1z" fill="#fff"/>
          </svg>
        </div>
        <span style={{ fontWeight: 700, fontSize: 15, color: C.dark, letterSpacing: '-0.01em' }}>Citadel</span>
        <span style={{ fontSize: 11, color: '#9CA3AF', fontFamily: 'JetBrains Mono, monospace', padding: '2px 6px', border: '1px solid #E5E7EB', borderRadius: 4, lineHeight: 1 }}>v2.1.0</span>
        <div style={{ flex: 1 }}/>
        <div style={{ display: 'flex', alignItems: 'center', gap: 7 }}>
          <div style={{ width: 6, height: 6, borderRadius: '50%', background: C.success }} className="animate-pulse-dot"/>
          <span style={{ fontSize: 12, color: '#6B7280' }}>Governance Simulator</span>
        </div>
      </header>

      {/* ── Body ───────────────────────────────────────────────────────────── */}
      <div style={{
        maxWidth: 1060, margin: '0 auto', padding: '24px 20px',
        display: 'grid', gridTemplateColumns: '360px 1fr', gap: 18,
        alignItems: 'start',
      }}>

        {/* ── Request builder ─────────────────────────────────────────────── */}
        <div style={{ background: '#fff', border: '1px solid #E5E7EB', borderRadius: 10, overflow: 'hidden', position: 'sticky', top: 68 }}>
          <div style={{ padding: '14px 18px', borderBottom: '1px solid #F0F1F3' }}>
            <div style={{ fontSize: 10, fontWeight: 700, letterSpacing: '0.09em', color: '#9CA3AF', textTransform: 'uppercase', marginBottom: 3 }}>Action Request</div>
            <div style={{ fontSize: 13, color: '#6B7280' }}>Construct an agent action for evaluation</div>
          </div>

          {/* Scenario picker */}
          <div style={{ padding: '12px 18px', borderBottom: '1px solid #F0F1F3', background: '#FAFAFA' }}>
            <label style={{ display: 'block', fontSize: 10, fontWeight: 700, color: '#374151', letterSpacing: '0.07em', textTransform: 'uppercase', marginBottom: 6 }}>Quick scenario</label>
            <Select value={scenario.label} onValueChange={v => {
              const s = SCENARIOS.find(x => x.label === v)
              if (s) applyScenario(s)
            }}>
              <SelectTrigger style={{ fontSize: 13, height: 36, background: '#fff' }}>
                <SelectValue/>
              </SelectTrigger>
              <SelectContent>
                {SCENARIOS.map(s => (
                  <SelectItem key={s.label} value={s.label} style={{ fontSize: 13 }}>{s.label}</SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          <div style={{ padding: '16px 18px', display: 'flex', flexDirection: 'column', gap: 13 }}>

            <div>
              <label style={{ display: 'block', fontSize: 10, fontWeight: 700, color: '#374151', letterSpacing: '0.07em', textTransform: 'uppercase', marginBottom: 5 }}>Actor ID</label>
              <Input value={actorId} onChange={e => setActorId(e.target.value)}
                style={{ fontSize: 12.5, height: 36, fontFamily: 'JetBrains Mono, monospace' }}/>
            </div>

            <div>
              <label style={{ display: 'block', fontSize: 10, fontWeight: 700, color: '#374151', letterSpacing: '0.07em', textTransform: 'uppercase', marginBottom: 5 }}>Actor type</label>
              <Select value={actorType} onValueChange={setActorType}>
                <SelectTrigger style={{ fontSize: 13, height: 36 }}>
                  <SelectValue/>
                </SelectTrigger>
                <SelectContent>
                  {['agent', 'service', 'human', 'system'].map(t => (
                    <SelectItem key={t} value={t} style={{ fontSize: 13, fontFamily: 'JetBrains Mono, monospace' }}>{t}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10 }}>
              <div>
                <label style={{ display: 'block', fontSize: 10, fontWeight: 700, color: '#374151', letterSpacing: '0.07em', textTransform: 'uppercase', marginBottom: 5 }}>Action</label>
                <Input value={actionName} onChange={e => setActionName(e.target.value)}
                  style={{ fontSize: 12, height: 36, fontFamily: 'JetBrains Mono, monospace' }}/>
              </div>
              <div>
                <label style={{ display: 'block', fontSize: 10, fontWeight: 700, color: '#374151', letterSpacing: '0.07em', textTransform: 'uppercase', marginBottom: 5 }}>Resource</label>
                <Input value={resource} onChange={e => setResource(e.target.value)}
                  style={{ fontSize: 12, height: 36, fontFamily: 'JetBrains Mono, monospace' }}/>
              </div>
            </div>

            <div>
              <label style={{ display: 'block', fontSize: 10, fontWeight: 700, color: '#374151', letterSpacing: '0.07em', textTransform: 'uppercase', marginBottom: 5 }}>Payload (JSON)</label>
              <textarea
                value={payload} onChange={e => setPayload(e.target.value)} rows={3}
                style={{
                  width: '100%', padding: '8px 10px', borderRadius: 6,
                  border: '1px solid #E5E7EB', fontSize: 12, resize: 'vertical',
                  fontFamily: 'JetBrains Mono, monospace', outline: 'none',
                  background: '#FAFAFA', color: C.dark, lineHeight: 1.65,
                  boxSizing: 'border-box', transition: 'border-color 0.15s',
                }}
                onFocus={e => e.currentTarget.style.borderColor = C.accent}
                onBlur={e => e.currentTarget.style.borderColor = '#E5E7EB'}
              />
            </div>

            <button
              onClick={runEval} disabled={running}
              style={{
                width: '100%', height: 40,
                background: running ? '#A5AEDE' : C.accent,
                color: '#fff', border: 'none', borderRadius: 7,
                fontSize: 14, fontWeight: 600, cursor: running ? 'not-allowed' : 'pointer',
                transition: 'background 0.15s, transform 0.1s',
                fontFamily: "'DM Sans', system-ui, sans-serif",
                display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 8,
              }}
              onMouseEnter={e => { if (!running) e.currentTarget.style.background = '#4854BC' }}
              onMouseLeave={e => { if (!running) e.currentTarget.style.background = C.accent }}
              onMouseDown={e => { if (!running) e.currentTarget.style.transform = 'scale(0.98)' }}
              onMouseUp={e => e.currentTarget.style.transform = 'none'}
            >
              {running ? (
                <>
                  <svg className="animate-spin-custom" width="14" height="14" viewBox="0 0 16 16" fill="none">
                    <circle cx="8" cy="8" r="6" stroke="rgba(255,255,255,0.5)" strokeWidth="2" strokeDasharray="28" strokeDashoffset="10" strokeLinecap="round"/>
                  </svg>
                  Evaluating…
                </>
              ) : (
                <>
                  <svg width="14" height="14" viewBox="0 0 16 16" fill="none">
                    <path d="M4 2l9 6-9 6V2z" fill="#fff"/>
                  </svg>
                  Evaluate Action
                </>
              )}
            </button>
          </div>
        </div>

        {/* ── Trace panel ─────────────────────────────────────────────────── */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>

          {stages.length === 0 ? (
            <div style={{ background: '#fff', border: '1px solid #E5E7EB', borderRadius: 10, padding: '56px 32px', textAlign: 'center' }}>
              <div style={{ width: 46, height: 46, background: '#F3F4F7', borderRadius: 10, display: 'flex', alignItems: 'center', justifyContent: 'center', margin: '0 auto 14px' }}>
                <svg width="22" height="22" viewBox="0 0 20 20" fill="none">
                  <path d="M10 2l7 4v8l-7 4-7-4V6l7-4z" stroke="#9CA3AF" strokeWidth="1.4" strokeLinejoin="round"/>
                  <path d="M10 2v16M3 6l7 4 7-4" stroke="#9CA3AF" strokeWidth="1.4"/>
                </svg>
              </div>
              <div style={{ fontWeight: 600, fontSize: 15, color: C.dark, marginBottom: 6 }}>Ready to evaluate</div>
              <div style={{ fontSize: 13, color: '#9CA3AF', maxWidth: 300, margin: '0 auto', lineHeight: 1.6 }}>
                Pick a scenario or construct a custom action, then click <strong style={{ color: '#6B7280' }}>Evaluate Action</strong> to see the governance pipeline in real time.
              </div>
            </div>
          ) : (
            <>
              {/* Pipeline */}
              <div style={{ background: '#fff', border: '1px solid #E5E7EB', borderRadius: 10, overflow: 'hidden' }}>
                <div style={{ padding: '13px 18px', borderBottom: '1px solid #F0F1F3', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                  <div>
                    <div style={{ fontSize: 10, fontWeight: 700, letterSpacing: '0.09em', color: '#9CA3AF', textTransform: 'uppercase', marginBottom: 2 }}>Evaluation Pipeline</div>
                    <div style={{ fontSize: 11, color: '#9CA3AF', fontFamily: 'JetBrains Mono, monospace' }}>
                      run_{String(runCount).padStart(4, '0')} · {actorId}
                    </div>
                  </div>
                  {running && (
                    <span style={{ fontSize: 10, fontWeight: 700, color: C.accent, background: C.accentDim, padding: '3px 9px', borderRadius: 4, letterSpacing: '0.06em' }}>
                      LIVE
                    </span>
                  )}
                </div>

                <div style={{ padding: '6px 0' }}>
                  {stages.map((stage, i) => (
                    <div
                      key={stage.id}
                      style={{
                        display: 'flex', alignItems: 'center', gap: 12,
                        padding: '9px 18px',
                        opacity: stage.status === 'idle' ? 0.38 : 1,
                        transition: 'opacity 0.22s ease',
                        borderLeft: stage.status !== 'idle' && stage.status !== 'running'
                          ? `2.5px solid ${stage.status === 'fail' ? C.error : stage.status === 'warn' ? C.warning : C.success}`
                          : '2.5px solid transparent',
                      }}
                    >
                      <StageIcon status={stage.status}/>
                      <div style={{ flex: 1, minWidth: 0 }}>
                        <div style={{ fontSize: 13, fontWeight: 500, color: stage.status === 'idle' ? '#9CA3AF' : C.dark }}>
                          {stage.label}
                        </div>
                        {stage.status !== 'idle' && (
                          <div style={{ fontSize: 11, color: '#9CA3AF', marginTop: 1, fontFamily: 'JetBrains Mono, monospace' }}>{stage.detail}</div>
                        )}
                      </div>
                      <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexShrink: 0 }}>
                        {stage.ms && stage.status !== 'idle' && stage.status !== 'running' && (
                          <span style={{ fontSize: 11, fontFamily: 'JetBrains Mono, monospace', color: '#9CA3AF' }}>{stage.ms}ms</span>
                        )}
                        {stage.status === 'fail' && (
                          <span style={{ fontSize: 10, fontWeight: 700, color: C.error, background: C.errorBg, padding: '2px 7px', borderRadius: 4, letterSpacing: '0.06em' }}>HALT</span>
                        )}
                        {stage.status === 'warn' && (
                          <span style={{ fontSize: 10, fontWeight: 700, color: C.warning, background: C.warningBg, padding: '2px 7px', borderRadius: 4, letterSpacing: '0.06em' }}>REVIEW</span>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              {/* Decision card */}
              {decision && (() => {
                const sc = statusConfig(decision.status)
                const tc = trustConfig(decision.trust_band)
                return (
                  <div
                    className="animate-slide-up"
                    style={{ background: '#fff', border: `1.5px solid ${sc.color}`, borderRadius: 10, overflow: 'hidden' }}
                  >
                    {/* Status bar */}
                    <div style={{ background: sc.bg, padding: '13px 18px', borderBottom: `1px solid ${sc.color}28`, display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                      <span style={{ fontSize: 11, fontWeight: 700, letterSpacing: '0.09em', color: sc.color, fontFamily: 'JetBrains Mono, monospace' }}>
                        {sc.label}
                      </span>
                      <span style={{ fontSize: 11, color: '#9CA3AF', fontFamily: 'JetBrains Mono, monospace' }}>
                        {decision.latency_ms}ms total · act_{decision.action_id}
                      </span>
                    </div>

                    <div style={{ padding: '16px 18px', display: 'flex', flexDirection: 'column', gap: 14 }}>
                      <p style={{ margin: 0, fontSize: 13.5, color: C.dark, lineHeight: 1.65 }}>{decision.reason}</p>

                      <div style={{ height: 1, background: '#F0F1F3' }}/>

                      {/* Detail grid */}
                      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 14 }}>
                        <div>
                          <div style={{ fontSize: 10, fontWeight: 700, color: '#9CA3AF', textTransform: 'uppercase', letterSpacing: '0.07em', marginBottom: 4 }}>Winning rule</div>
                          <code style={{ fontSize: 12, fontFamily: 'JetBrains Mono, monospace', color: C.dark }}>{decision.winning_rule}</code>
                        </div>
                        <div>
                          <div style={{ fontSize: 10, fontWeight: 700, color: '#9CA3AF', textTransform: 'uppercase', letterSpacing: '0.07em', marginBottom: 4 }}>Actor</div>
                          <code style={{ fontSize: 12, fontFamily: 'JetBrains Mono, monospace', color: C.dark }}>{actorId}</code>
                        </div>
                        <div>
                          <div style={{ fontSize: 10, fontWeight: 700, color: '#9CA3AF', textTransform: 'uppercase', letterSpacing: '0.07em', marginBottom: 6 }}>Trust score</div>
                          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                            <span style={{ fontSize: 14, fontWeight: 700, fontFamily: 'JetBrains Mono, monospace', color: tc.color }}>
                              {decision.trust_score.toFixed(2)}
                            </span>
                            <span style={{ fontSize: 10, fontWeight: 700, color: tc.color, background: `${tc.color}18`, padding: '2px 7px', borderRadius: 4, letterSpacing: '0.06em' }}>
                              {decision.trust_band}
                            </span>
                          </div>
                          {/* Mini trust bar */}
                          <div style={{ marginTop: 6, height: 4, background: '#F0F1F3', borderRadius: 2, overflow: 'hidden' }}>
                            <div style={{
                              height: '100%', background: tc.color, borderRadius: 2,
                              width: `${decision.trust_score * 100}%`,
                              transition: 'width 0.7s cubic-bezier(0.22,1,0.36,1)',
                              animation: 'bar-fill 0.7s cubic-bezier(0.22,1,0.36,1) both',
                            }}/>
                          </div>
                        </div>
                        <div>
                          <div style={{ fontSize: 10, fontWeight: 700, color: '#9CA3AF', textTransform: 'uppercase', letterSpacing: '0.07em', marginBottom: 4 }}>Audit hash</div>
                          <code style={{ fontSize: 11, fontFamily: 'JetBrains Mono, monospace', color: '#6B7280' }}>sha256:{decision.audit_hash}…</code>
                        </div>
                      </div>

                      {/* JSON audit event */}
                      <div style={{ background: '#0D1117', borderRadius: 8, padding: '13px 16px', overflowX: 'auto' }}>
                        <div style={{ fontSize: 9, color: '#4B5563', fontFamily: 'JetBrains Mono, monospace', marginBottom: 8, letterSpacing: '0.08em', textTransform: 'uppercase' }}>
                          Audit Event · Tamper-evident · Immutable
                        </div>
                        <pre style={{ margin: 0, fontSize: 12, fontFamily: 'JetBrains Mono, monospace', color: '#E5E7EB', lineHeight: 1.75, whiteSpace: 'pre' }}>
{`{
  `}<span style={{ color: '#7DD3FC' }}>"action_id"</span>{`:    `}<span style={{ color: '#86EFAC' }}>{`"act_${decision.action_id}"`}</span>{`,
  `}<span style={{ color: '#7DD3FC' }}>"status"</span>{`:       `}<span style={{ color: sc.color }}>{`"${decision.status}"`}</span>{`,
  `}<span style={{ color: '#7DD3FC' }}>"winning_rule"</span>{`: `}<span style={{ color: '#C4B5FD' }}>{`"${decision.winning_rule}"`}</span>{`,
  `}<span style={{ color: '#7DD3FC' }}>"actor_id"</span>{`:     `}<span style={{ color: '#86EFAC' }}>{`"${actorId}"`}</span>{`,
  `}<span style={{ color: '#7DD3FC' }}>"action_name"</span>{`:  `}<span style={{ color: '#86EFAC' }}>{`"${actionName}"`}</span>{`,
  `}<span style={{ color: '#7DD3FC' }}>"trust_score"</span>{`:  `}<span style={{ color: '#FDE68A' }}>{decision.trust_score.toFixed(2)}</span>{`,
  `}<span style={{ color: '#7DD3FC' }}>"latency_ms"</span>{`:   `}<span style={{ color: '#FDE68A' }}>{decision.latency_ms}</span>{`,
  `}<span style={{ color: '#7DD3FC' }}>"audit_hash"</span>{`:   `}<span style={{ color: '#F9A8D4' }}>{`"sha256:${decision.audit_hash}..."`}</span>{`
}`}
                        </pre>
                      </div>
                    </div>
                  </div>
                )
              })()}
            </>
          )}
        </div>
      </div>

      {/* ── Footer ─────────────────────────────────────────────────────────── */}
      <footer style={{ textAlign: 'center', padding: '18px 24px', color: '#9CA3AF', fontSize: 12, borderTop: '1px solid #E5E7EB', background: '#fff', marginTop: 8 }}>
        Citadel Runtime Governance Kernel · v2.1.0 · Every decision is cryptographically audited and tamper-evident
      </footer>
    </div>
  )
}
