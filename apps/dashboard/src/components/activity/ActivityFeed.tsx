import { activityEvents } from "../../data/mock-activity";
import { Card } from "../ui/Card";

export function ActivityFeed() {
  return (
    <div className="stack-lg">
      {activityEvents.map((event) => (
        <Card key={event.id} title={event.title}>
          <div className="event-row">
            <p>{event.description}</p>
            <span className="data-time">{event.time}</span>
          </div>
        </Card>
      ))}
    </div>
  );
}
