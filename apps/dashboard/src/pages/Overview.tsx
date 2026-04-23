import { KpiCard } from "../components/dashboard/KpiCard";
import { Card } from "../components/ui/Card";
import { kpis } from "../data/kpis";
import { PageShell } from "../layout/PageShell";
import { GovernanceGraph } from "../components/visualizations/GovernanceGraph";
import { useState } from "react";
import { GitGraph, LayoutDashboard } from "lucide-react";
import { Button } from "../components/ui/Button";

export function OverviewPage() {
  const [view, setView] = useState<"dashboard" | "flow">("dashboard");

  return (
    <PageShell
      title="Overview"
      description="Current posture, workload, and recent risk."
      actions={
        <div className="flex gap-2">
          <Button 
            variant={view === "dashboard" ? "primary" : "secondary"} 
            onClick={() => setView("dashboard")}
            className="h-9 px-3"
          >
            <LayoutDashboard className="w-4 h-4 mr-2" />
            Dashboard
          </Button>
          <Button 
            variant={view === "flow" ? "primary" : "secondary"} 
            onClick={() => setView("flow")}
            className="h-9 px-3"
          >
            <GitGraph className="w-4 h-4 mr-2" />
            Flow View
          </Button>
        </div>
      }
    >
      {view === "dashboard" ? (
        <>
          <div className="kpi-grid">
            {kpis.map((item) => (
              <KpiCard key={item.label} {...item} />
            ))}
          </div>

          <div className="overview-grid">
            <Card title="Pending reviews">Queue summary and highest-risk pending items.</Card>
            <Card title="Recent critical activity">Chronological feed of urgent events.</Card>
            <Card title="Kill switch status">Current emergency state and scope.</Card>
          </div>
        </>
      ) : (
        <div className="stack-lg">
          <Card title="Governance Decision Path">
            <GovernanceGraph />
          </Card>
        </div>
      )}
    </PageShell>
  );
}
