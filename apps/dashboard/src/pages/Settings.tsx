import { Card } from "../components/ui/Card";
import { PageShell } from "../layout/PageShell";

export function SettingsPage() {
  return (
    <PageShell title="Settings" description="Access, integrations, notifications, and retention.">
      <Card title="Workspace settings">Settings surface goes here.</Card>
    </PageShell>
  );
}
