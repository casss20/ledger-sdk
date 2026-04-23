import { useState } from "react";
import { auditEvents } from "../../data/mock-audit";
import { AuditEventPanel } from "./AuditEventPanel";

export function AuditTable() {
  const [selectedEvent, setSelectedEvent] = useState<typeof auditEvents[0] | null>(null);

  return (
    <>
      <div className="table-shell">
      <table className="data-table">
        <thead>
          <tr>
            <th>Time</th>
            <th>Actor</th>
            <th>Action</th>
            <th>Target</th>
            <th>Outcome</th>
            <th>Trace ID</th>
          </tr>
        </thead>
        <tbody>
          {auditEvents.map((row) => (
            <tr 
              key={row.id}
              className="clickable-row"
              onClick={() => setSelectedEvent(row)}
            >
              <td className="data-time">{row.time}</td>
              <td>{row.actor}</td>
              <td>{row.action}</td>
              <td>{row.target}</td>
              <td>{row.outcome}</td>
              <td className="data-num">{row.traceId}</td>
            </tr>
          ))}
        </tbody>
      </table>
      </div>
      <AuditEventPanel 
        event={selectedEvent} 
        onClose={() => setSelectedEvent(null)} 
      />
    </>
  );
}
