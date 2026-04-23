import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { useAuditLog } from "@/lib/hooks";
import { Loader2, CheckCircle, XCircle } from "lucide-react";

export function AuditLog() {
  const { data: entries = [], isLoading } = useAuditLog();

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <CardTitle className="flex items-center gap-2">
            📋 Recent Audit Log
            <div className="h-2 w-2 rounded-full bg-accent-success animate-pulse" />
          </CardTitle>
        </div>
      </CardHeader>
      <CardContent>
        {isLoading ? (
          <div className="flex items-center justify-center py-12">
            <Loader2 className="h-8 w-8 animate-spin text-primary" />
          </div>
        ) : entries.length === 0 ? (
          <div className="text-center py-12 text-muted-foreground">
            No audit entries yet
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="border-b">
                  <th className="text-left py-3 px-4 text-xs font-medium text-muted-foreground uppercase">
                    Time
                  </th>
                  <th className="text-left py-3 px-4 text-xs font-medium text-muted-foreground uppercase">
                    Actor
                  </th>
                  <th className="text-left py-3 px-4 text-xs font-medium text-muted-foreground uppercase">
                    Action
                  </th>
                  <th className="text-left py-3 px-4 text-xs font-medium text-muted-foreground uppercase">
                    Resource
                  </th>
                  <th className="text-left py-3 px-4 text-xs font-medium text-muted-foreground uppercase">
                    Risk
                  </th>
                  <th className="text-left py-3 px-4 text-xs font-medium text-muted-foreground uppercase">
                    Status
                  </th>
                </tr>
              </thead>
              <tbody>
                {entries.map((entry) => (
                  <tr key={entry.id} className="border-b last:border-0 hover:bg-secondary/50">
                    <td className="py-3 px-4 text-sm">
                      {new Date(entry.ts).toLocaleTimeString()}
                    </td>
                    <td className="py-3 px-4 text-sm font-medium">{entry.actor}</td>
                    <td className="py-3 px-4 text-sm">{entry.action}</td>
                    <td className="py-3 px-4 text-sm text-muted-foreground">
                      {entry.resource}
                    </td>
                    <td className="py-3 px-4">
                      <Badge
                        variant="outline"
                        className={
                          entry.risk === "high"
                            ? "border-accent-danger text-accent-danger"
                            : entry.risk === "medium"
                            ? "border-accent-warning text-accent-warning"
                            : "border-accent-success text-accent-success"
                        }
                      >
                        {entry.risk}
                      </Badge>
                    </td>
                    <td className="py-3 px-4">
                      {entry.approved ? (
                        <Badge className="bg-accent-success text-white">
                          <CheckCircle className="h-3 w-3 mr-1" />
                          Approved
                        </Badge>
                      ) : (
                        <Badge className="bg-accent-danger text-white">
                          <XCircle className="h-3 w-3 mr-1" />
                          Denied
                        </Badge>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
