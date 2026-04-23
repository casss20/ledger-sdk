import { Drawer } from "../ui/Drawer";
import { Button } from "../ui/Button";
import { StatusPill } from "../dashboard/StatusPill";
import type { Approval } from "../../hooks/useApprovals";
import { useApprovals } from "../../hooks/useApprovals";
import { Loader2 } from "lucide-react";

type Props = {
  item: Approval | null;
  onClose: () => void;
};

export function ApprovalDetailDrawer({ item, onClose }: Props) {
  const { approve, reject, isProcessing } = useApprovals();
  const user = { email: "Operator" }; // Mock until JWT decoding is implemented
  if (!item) return null;

  return (
    <Drawer
      isOpen={!!item}
      onClose={onClose}
      title="Request Details"
      actions={
        <div className="drawer-actions">
          <Button variant="secondary" onClick={onClose} disabled={isProcessing}>
            Close
          </Button>
          <Button 
            variant="danger" 
            onClick={async () => {
              await reject({ id: item.approval_id, reviewer: user?.email || "Operator", reason: "Rejected by operator" });
              onClose();
            }}
            disabled={isProcessing || item.status !== 'pending'}
          >
            {isProcessing ? <Loader2 className="w-4 h-4 animate-spin" /> : "Deny"}
          </Button>
          <Button 
            variant="primary"
            onClick={async () => {
              await approve({ id: item.approval_id, reviewer: user?.email || "Operator", reason: "Approved by operator" });
              onClose();
            }}
            disabled={isProcessing || item.status !== 'pending'}
          >
            {isProcessing ? <Loader2 className="w-4 h-4 animate-spin" /> : "Approve Action"}
          </Button>
        </div>
      }
    >
      <div className="stack-lg">
        <section className="detail-section">
          <div className="detail-header">
            <h4>Summary</h4>
            <StatusPill status={item.status} />
          </div>
          <div className="detail-grid">
            <div className="field">
              <span>Priority</span>
              <p className="font-bold">{item.priority}</p>
            </div>
            <div className="field">
              <span>Requested By</span>
              <p>{item.requested_by}</p>
            </div>
            <div className="field">
              <span>Action ID</span>
              <p className="font-mono text-xs">{item.action_id}</p>
            </div>
            <div className="field">
              <span>Approval ID</span>
              <p className="font-mono text-xs">{item.approval_id}</p>
            </div>
          </div>
        </section>

        <section className="detail-section">
          <h4>Reasoning</h4>
          <p>{item.reason}</p>
        </section>

        {item.decided_at && (
          <section className="detail-section">
            <h4>Decision Info</h4>
            <div className="detail-grid">
              <div className="field">
                <span>Reviewed By</span>
                <p>{item.reviewed_by}</p>
              </div>
              <div className="field">
                <span>Decided At</span>
                <p className="data-time">{item.decided_at}</p>
              </div>
            </div>
            <div className="mt-2 text-sm text-slate-400">
              {item.decision_reason}
            </div>
          </section>
        )}
      </div>
    </Drawer>
  );
}
