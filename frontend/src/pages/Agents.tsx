import { Card } from "../components/ui/Card";
import { PageShell } from "../layout/PageShell";

export function AgentsPage() {
  return (
    <PageShell title="Agents" description="Registry, scopes, and recent behavior.">
      <Card title="Agent registry">Agent inventory surface goes here.</Card>
    </PageShell>
  );
}
