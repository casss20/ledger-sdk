import { useState } from "react";
import { useAudit } from "../../hooks/useAudit";
import type { AuditEvent } from "../../hooks/useAudit";
import { AuditEventPanel } from "./AuditEventPanel";
import { Loader2 } from "lucide-react";

export function AuditTable() {
  const { data: events, isLoading, error } = useAudit();
  const [selectedEvent, setSelectedEvent] = useState<AuditEvent | null>(null);

  if (isLoading) {
    return (
      <div className="flex items-center justify-center p-12 text-slate-400">
        <Loader2 className="w-6 h-6 animate-spin mr-3" />
        Loading audit logs...
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-8 text-center text-red-400 bg-red-400/10 rounded-lg border border-red-400/20">
        Error loading audit logs.
      </div>
    );
  }

  return (
    <>
      <div className="table-shell">
      <table className="data-table">
        <thead>
          <tr>
            <th>Time</th>
            <th>Actor</th>
            <th>Action</th>
            <th>Outcome</th>
            <th>Risk Score</th>
            <th>Trust Snapshot</th>
          </tr>
        </thead>
        <tbody>
          {(events || []).map((row) => (
            <tr 
              key={row.event_id}
              className="clickable-row"
              onClick={() => setSelectedEvent(row)}
            >
              <td className="data-time">{new Date(row.created_at).toLocaleTimeString()}</td>
              <td>{row.user_id}</td>
              <td>{row.action_type}</td>
              <td>{row.status}</td>
              <td className="data-num">{row.risk_score}</td>
              <td className="data-num font-mono text-xs">
                {row.trust_snapshot_id ? row.trust_snapshot_id.slice(0, 8) : "none"}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      </div>
      <AuditEventPanel 
        event={selectedEvent as any} 
        onClose={() => setSelectedEvent(null)} 
      />
    </>
  );
}
