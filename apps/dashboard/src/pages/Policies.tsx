import { Card } from "../components/ui/Card";
import { PageShell } from "../layout/PageShell";

export function PoliciesPage() {
  return (
    <PageShell title="Policies" description="Policy packs, thresholds, and change history.">
      <Card title="Policy registry">Policy management surface goes here.</Card>
    </PageShell>
  );
}
