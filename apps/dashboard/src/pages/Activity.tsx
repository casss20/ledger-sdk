import { ActivityFeed } from "../components/activity/ActivityFeed";
import { PageShell } from "../layout/PageShell";

export function ActivityPage() {
  return (
    <PageShell
      title="Activity Stream"
      description="Live operational events across agents and policies."
    >
      <ActivityFeed />
    </PageShell>
  );
}
