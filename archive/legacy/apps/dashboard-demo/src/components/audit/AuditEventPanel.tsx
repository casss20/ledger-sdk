import { Drawer } from "../ui/Drawer";
import { Button } from "../ui/Button";

type AuditEvent = {
  id: string;
  time: string;
  actor: string;
  action: string;
  target: string;
  outcome: string;
  traceId: string;
};

type Props = {
  event: AuditEvent | null;
  onClose: () => void;
};

export function AuditEventPanel({ event, onClose }: Props) {
  if (!event) return null;

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
            <span className={`status-badge status-${event.outcome.toLowerCase()}`}>
              {event.outcome}
            </span>
          </div>
          <div className="detail-grid">
            <div className="field">
              <span>Trace ID</span>
              <p className="data-num">{event.traceId}</p>
            </div>
            <div className="field">
              <span>Timestamp</span>
              <p className="data-time">{event.time}</p>
            </div>
            <div className="field">
              <span>Actor</span>
              <p>{event.actor}</p>
            </div>
            <div className="field">
              <span>Target</span>
              <p>{event.target}</p>
            </div>
          </div>
        </section>

        <section className="detail-section">
          <h4>Execution Payload</h4>
          <div className="code-block">
            <pre>
              {`{
  "event_id": "${event.id}",
  "timestamp": "${event.time}",
  "trace_id": "${event.traceId}",
  "source": {
    "agent_id": "${event.actor}",
    "ip": "10.1.42.18"
  },
  "action": {
    "type": "${event.action}",
    "target": "${event.target}",
    "parameters": {
      "force": false,
      "dry_run": false
    }
  },
  "result": {
    "status": "${event.outcome.toUpperCase()}",
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
