import { AuditFilters } from "../components/audit/AuditFilters";
import { AuditTable } from "../components/audit/AuditTable";
import { PageShell } from "../layout/PageShell";

export function AuditExplorerPage() {
  return (
    <PageShell
      title="Audit Explorer"
      description="Search, filter, and export traceable governance events."
    >
      <div className="stack-lg">
        <AuditFilters />
        <AuditTable />
      </div>
    </PageShell>
  );
}
