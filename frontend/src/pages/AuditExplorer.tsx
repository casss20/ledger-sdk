import { AuditFilters } from "../components/audit/AuditFilters";
import { AuditTable } from "../components/audit/AuditTable";
import { PageShell } from "../layout/PageShell";
import { RecursiveGroupGraph } from "../components/visualizations/RecursiveGroupGraph";
import { useState } from "react";
import { Table2, FolderTree } from "lucide-react";
import { Button } from "../components/ui/Button";
import { Card } from "../components/ui/Card";

export function AuditExplorerPage() {
  const [view, setView] = useState<"table" | "groups">("table");

  return (
    <PageShell
      title="Audit Explorer"
      description="Search, filter, and export traceable governance events."
      actions={
        <div className="flex gap-2">
          <Button 
            variant={view === "table" ? "primary" : "secondary"} 
            onClick={() => setView("table")}
            className="h-9 px-3"
          >
            <Table2 className="w-4 h-4 mr-2" />
            Table
          </Button>
          <Button 
            variant={view === "groups" ? "primary" : "secondary"} 
            onClick={() => setView("groups")}
            className="h-9 px-3"
          >
            <FolderTree className="w-4 h-4 mr-2" />
            Groups
          </Button>
        </div>
      }
    >
      {view === "table" ? (
        <div className="stack-lg">
          <AuditFilters />
          <AuditTable />
        </div>
      ) : (
        <div className="stack-lg">
          <Card title="Structural Action Grouping">
            <RecursiveGroupGraph />
          </Card>
        </div>
      )}
    </PageShell>
  );
}
