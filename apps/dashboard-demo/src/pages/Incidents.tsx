import { Card } from "../components/ui/Card";
import { PageShell } from "../layout/PageShell";

export function IncidentsPage() {
  return (
    <PageShell title="Incidents" description="Escalations, anomalies, and response status.">
      <Card title="Incident timeline">Incident response surface goes here.</Card>
    </PageShell>
  );
}
