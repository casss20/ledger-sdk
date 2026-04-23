import { useState } from "react";
import { approvals } from "../../data/mock-approvals";
import { StatusPill } from "../dashboard/StatusPill";
import { ApprovalDetailDrawer } from "./ApprovalDetailDrawer";
import type { ApprovalItem } from "../../features/approvals/types";

export function ApprovalTable() {
  const [selectedItem, setSelectedItem] = useState<ApprovalItem | null>(null);

  return (
    <>
      <div className="table-shell">
      <table className="data-table">
        <thead>
          <tr>
            <th>Status</th>
            <th>Risk</th>
            <th>Agent</th>
            <th>Requested action</th>
            <th>Target</th>
            <th>Policy source</th>
            <th>Requested at</th>
            <th>Waiting</th>
            <th>Decision</th>
          </tr>
        </thead>
        <tbody>
          {approvals.map((row) => (
            <tr 
              key={row.id} 
              className="clickable-row"
              onClick={() => setSelectedItem(row)}
            >
              <td><StatusPill status={row.status} /></td>
              <td>{row.risk}</td>
              <td>{row.agent}</td>
              <td>{row.action}</td>
              <td>{row.target}</td>
              <td>{row.policy}</td>
              <td className="data-time">{row.requestedAt}</td>
              <td className="data-num">{row.waiting}</td>
              <td>{row.decision}</td>
            </tr>
          ))}
        </tbody>
      </table>
      </div>
      <ApprovalDetailDrawer 
        item={selectedItem} 
        onClose={() => setSelectedItem(null)} 
      />
    </>
  );
}
