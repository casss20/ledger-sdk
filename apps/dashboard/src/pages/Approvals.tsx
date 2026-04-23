import { ApprovalFilters } from "../components/approvals/ApprovalFilters";
import { ApprovalTable } from "../components/approvals/ApprovalTable";
import { PageShell } from "../layout/PageShell";

export function ApprovalsPage() {
  return (
    <PageShell
      title="Approval Queue"
      description="Review and decide high-risk agent actions."
      actions={<button className="btn btn-secondary">Export CSV</button>}
    >
      <div className="stack-lg">
        <ApprovalFilters />
        <ApprovalTable />
      </div>
    </PageShell>
  );
}
