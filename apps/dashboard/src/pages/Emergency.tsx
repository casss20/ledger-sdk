import { KillSwitchPanel } from "../components/emergency/KillSwitchPanel";
import { PageShell } from "../layout/PageShell";

export function EmergencyPage() {
  return (
    <PageShell
      title="Emergency"
      description="Restrict or suspend risky execution paths."
    >
      <KillSwitchPanel />
    </PageShell>
  );
}
