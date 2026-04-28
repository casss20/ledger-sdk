import { Drawer } from "../ui/Drawer";
import { Button } from "../ui/Button";
import { useDecisionTrustBreakdown } from "../../hooks/useAudit";
import type { AuditEvent as DashboardAuditEvent } from "../../hooks/useAudit";

type Props = {
  event: DashboardAuditEvent | null;
  onClose: () => void;
};

function formatContribution(value: number) {
  const sign = value > 0 ? "+" : "";
  return `${sign}${value.toFixed(3)}`;
}

export function AuditEventPanel({ event, onClose }: Props) {
  const trust = useDecisionTrustBreakdown(event?.decision_id);

  if (!event) return null;
  const trustData = trust.data;
  const outcome = event.status || "pending";
  const traceId = event.trace_id || event.action_id;

  return (
    <Drawer
      isOpen={!!event}
      onClose={onClose}
      title="Audit Event Details"
      actions={
        <div className="drawer-actions">
          <Button variant="secondary" onClick={onClose}>
            Close
          </Button>
          <Button variant="primary">View Full Trace</Button>
        </div>
      }
    >
      <div className="stack-lg">
        <section className="detail-section">
          <div className="detail-header">
            <h4>Overview</h4>
            <span className={`status-badge status-${outcome.toLowerCase()}`}>
              {outcome}
            </span>
          </div>
          <div className="detail-grid">
            <div className="field">
              <span>Trace ID</span>
              <p className="data-num">{traceId}</p>
            </div>
            <div className="field">
              <span>Timestamp</span>
              <p className="data-time">{event.created_at}</p>
            </div>
            <div className="field">
              <span>Actor</span>
              <p>{event.user_id}</p>
            </div>
            <div className="field">
              <span>Decision</span>
              <p className="data-num">{event.decision_id || "not linked"}</p>
            </div>
          </div>
        </section>

        <section className="detail-section">
          <div className="detail-header">
            <h4>Trust Factor Breakdown</h4>
            {trustData?.available && (
              <span className={`status-badge status-${String(trustData.band || "").toLowerCase()}`}>
                {trustData.band} · {trustData.score?.toFixed(2)}
              </span>
            )}
          </div>
          {!event.decision_id ? (
            <p className="text-sm text-slate-400">This audit event is not linked to a decision.</p>
          ) : trust.isLoading ? (
            <p className="text-sm text-slate-400">Loading trust snapshot...</p>
          ) : trust.isError ? (
            <p className="text-sm text-red-400">Trust breakdown could not be loaded.</p>
          ) : !trustData?.available ? (
            <p className="text-sm text-slate-400">{trustData?.reason || "No trust snapshot available."}</p>
          ) : (
            <div className="stack-md">
              <div className="detail-grid">
                <div className="field">
                  <span>Snapshot ID</span>
                  <p className="data-num">{trustData.trust_snapshot_id}</p>
                </div>
                <div className="field">
                  <span>Computed</span>
                  <p className="data-time">{trustData.computed_at}</p>
                </div>
                <div className="field">
                  <span>Method</span>
                  <p>{trustData.computation_method}</p>
                </div>
              </div>
              <div className="space-y-3">
                {(trustData.factor_breakdown || []).map((factor) => {
                  const magnitude = Math.min(100, Math.round(Math.abs(factor.contribution) * 400));
                  const barColor = factor.direction === "negative" ? "bg-red-500" : factor.direction === "positive" ? "bg-emerald-500" : "bg-slate-600";
                  return (
                    <div key={factor.key}>
                      <div className="flex items-center justify-between gap-3 text-xs mb-1">
                        <span className="text-slate-300">{factor.label}</span>
                        <span className={factor.direction === "negative" ? "text-red-400" : "text-emerald-400"}>
                          {formatContribution(factor.contribution)}
                        </span>
                      </div>
                      <div className="h-2 rounded-full bg-slate-800 overflow-hidden">
                        <div className={`h-full ${barColor}`} style={{ width: `${magnitude}%` }} />
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          )}
        </section>

        <section className="detail-section">
          <h4>Execution Payload</h4>
          <div className="code-block">
            <pre>
              {`{
  "event_id": "${event.event_id}",
  "timestamp": "${event.created_at}",
  "trace_id": "${traceId}",
  "decision_id": "${event.decision_id || ""}",
  "trust_snapshot_id": "${event.trust_snapshot_id || ""}",
  "source": {
    "agent_id": "${event.user_id}",
    "ip": "10.1.42.18"
  },
  "action": {
    "type": "${event.action_type}",
    "target": "${event.action_id}",
    "parameters": {
      "force": false,
      "dry_run": false
    }
  },
  "result": {
    "status": "${outcome.toUpperCase()}",
    "policy_version": "v1.4.2"
  }
}`}
            </pre>
          </div>
        </section>
      </div>
    </Drawer>
  );
}
