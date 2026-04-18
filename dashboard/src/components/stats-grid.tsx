import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { useStats } from "@/lib/hooks";
import { Clock, CheckCircle, XCircle, AlertTriangle } from "lucide-react";

export function StatsGrid() {
  const { data: stats, isLoading } = useStats();

  const items = [
    {
      title: "Pending Approvals",
      value: stats?.pending ?? 0,
      icon: Clock,
      color: "text-accent-warning",
    },
    {
      title: "Approved Today",
      value: stats?.approved ?? 0,
      icon: CheckCircle,
      color: "text-accent-success",
    },
    {
      title: "Denied Today",
      value: stats?.denied ?? 0,
      icon: XCircle,
      color: "text-accent-danger",
    },
    {
      title: "Active Kill Switches",
      value: stats?.active_kills ?? 0,
      icon: AlertTriangle,
      color: "text-accent-danger",
    },
  ];

  if (isLoading) {
    return (
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
        {Array(4).fill(0).map((_, i) => (
          <Card key={i} className="h-28 animate-pulse" />
        ))}
      </div>
    );
  }

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
      {items.map((item) => (
        <Card key={item.title}>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              {item.title}
            </CardTitle>
            <item.icon className={`h-4 w-4 ${item.color}`} />
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-bold">{item.value}</div>
          </CardContent>
        </Card>
      ))}
    </div>
  );
}
