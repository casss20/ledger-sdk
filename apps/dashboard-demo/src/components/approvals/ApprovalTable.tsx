import { useState } from "react";
import { StatusPill } from "../dashboard/StatusPill";
import { ApprovalDetailDrawer } from "./ApprovalDetailDrawer";
import { useApprovals } from "../../hooks/useApprovals";
import type { Approval } from "../../hooks/useApprovals";
import { Loader2 } from "lucide-react";

export function ApprovalTable() {
  const { data: approvals, isLoading, error } = useApprovals();
  const [selectedItem, setSelectedItem] = useState<Approval | null>(null);

  if (isLoading) {
    return (
      <div className="flex items-center justify-center p-12 text-slate-400">
        <Loader2 className="w-6 h-6 animate-spin mr-3" />
        Loading approvals...
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-8 text-center text-red-400 bg-red-400/10 rounded-lg border border-red-400/20">
        Error loading approvals. Please check your connection.
      </div>
    );
  }

  return (
    <>
      <div className="table-shell">
      <table className="data-table">
        <thead>
          <tr>
            <th>Status</th>
            <th>Priority</th>
            <th>ID</th>
            <th>Reason</th>
            <th>Requested By</th>
            <th>Action ID</th>
          </tr>
        </thead>
        <tbody>
          {(approvals || []).map((row) => (
            <tr 
              key={row.approval_id} 
              className="clickable-row"
              onClick={() => setSelectedItem(row)}
            >
              <td><StatusPill status={row.status} /></td>
              <td className="font-bold">{row.priority}</td>
              <td className="font-mono text-xs text-slate-500">{row.approval_id.slice(0, 8)}...</td>
              <td>{row.reason}</td>
              <td>{row.requested_by}</td>
              <td className="font-mono text-xs text-slate-500">{row.action_id.slice(0, 8)}...</td>
            </tr>
          ))}
        </tbody>
      </table>
      {(approvals || []).length === 0 && (
        <div className="p-12 text-center text-slate-500 italic">
          No pending approvals found.
        </div>
      )}
      </div>
      <ApprovalDetailDrawer 
        item={selectedItem as any} 
        onClose={() => setSelectedItem(null)} 
      />
    </>
  );
}
