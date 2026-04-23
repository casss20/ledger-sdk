import { KpiCard } from "../components/dashboard/KpiCard";
import { Card } from "../components/ui/Card";
import { kpis } from "../data/kpis";
import { PageShell } from "../layout/PageShell";

export function OverviewPage() {
  return (
    <PageShell
      title="Overview"
      description="Current posture, workload, and recent risk."
    >
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
    </PageShell>
  );
}
