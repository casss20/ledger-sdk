import type { ApprovalItem } from "../../features/approvals/types";
import { Drawer } from "../ui/Drawer";
import { Button } from "../ui/Button";
import { StatusPill } from "../dashboard/StatusPill";

type Props = {
  item: ApprovalItem | null;
  onClose: () => void;
};

export function ApprovalDetailDrawer({ item, onClose }: Props) {
  if (!item) return null;

  return (
    <Drawer
      isOpen={!!item}
      onClose={onClose}
      title="Request Details"
      actions={
        <div className="drawer-actions">
          <Button variant="secondary" onClick={onClose}>
            Close
          </Button>
          <Button variant="danger">Deny</Button>
          <Button variant="primary">Approve Action</Button>
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
              <span>Risk Level</span>
              <p>{item.risk}</p>
            </div>
            <div className="field">
              <span>Agent</span>
              <p>{item.agent}</p>
            </div>
            <div className="field">
              <span>Target Resource</span>
              <p>{item.target}</p>
            </div>
            <div className="field">
              <span>Requested At</span>
              <p className="data-time">{item.requestedAt}</p>
            </div>
          </div>
        </section>

        <section className="detail-section">
          <h4>Requested Action</h4>
          <div className="code-block">
            <pre>
              {`{
  "action": "${item.action}",
  "reason": "Agent requires execution outside of normal threshold bounds.",
  "target_id": "${item.target.split(' / ')[1] || item.target}"
}`}
            </pre>
          </div>
        </section>

        <section className="detail-section">
          <h4>Policy Trigger</h4>
          <p>
            This action was intercepted by the <strong>{item.policy}</strong>{" "}
            policy rule.
          </p>
          <div className="policy-box">
            <code>
              IF action.type == "{item.action.split(' ')[0].toLowerCase()}" AND action.risk &gt;= "{item.risk}" THEN require(human_review)
            </code>
          </div>
        </section>
      </div>
    </Drawer>
  );
}
