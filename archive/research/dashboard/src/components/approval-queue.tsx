import { useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { usePendingApprovals, useApproveRequest, useDenyRequest } from "@/lib/hooks";
import { CheckCircle, XCircle, Loader2 } from "lucide-react";

export function ApprovalQueue() {
  const { data: requests = [], isLoading } = usePendingApprovals();
  const approveMutation = useApproveRequest();
  const denyMutation = useDenyRequest();
  const [processing, setProcessing] = useState<string | null>(null);

  const handleApprove = async (id: string) => {
    setProcessing(id);
    await approveMutation.mutateAsync(id);
    setProcessing(null);
  };

  const handleDeny = async (id: string) => {
    setProcessing(id);
    await denyMutation.mutateAsync(id);
    setProcessing(null);
  };

  return (
    <Card className="h-[500px] flex flex-col">
      <CardHeader>
        <div className="flex items-center justify-between">
          <CardTitle className="flex items-center gap-2">
            ⏳ Pending Approvals
            {requests.length > 0 && (
              <Badge variant="secondary" className="bg-accent-warning text-black">
                {requests.length}
              </Badge>
            )}
          </CardTitle>
          <div className="h-2 w-2 rounded-full bg-accent-success animate-pulse" />
        </div>
      </CardHeader>
      <CardContent className="flex-1 overflow-auto">
        {isLoading ? (
          <div className="flex items-center justify-center h-full">
            <Loader2 className="h-8 w-8 animate-spin text-primary" />
          </div>
        ) : requests.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full text-muted-foreground">
            <CheckCircle className="h-12 w-12 mb-2 text-accent-success" />
            <p>No pending approvals</p>
          </div>
        ) : (
          <div className="space-y-3">
            {requests.map((req) => (
              <div
                key={req.id}
                className="p-4 rounded-lg border bg-card hover:bg-secondary/50 transition-colors"
              >
                <div className="flex items-start justify-between mb-2">
                  <div>
                    <div className="font-semibold">{req.action}</div>
                    <div className="text-sm text-muted-foreground">{req.resource}</div>
                  </div>
                  <Badge
                    variant="outline"
                    className={
                      req.risk === "high"
                        ? "border-accent-danger text-accent-danger"
                        : req.risk === "medium"
                        ? "border-accent-warning text-accent-warning"
                        : "border-accent-success text-accent-success"
                    }
                  >
                    {req.risk}
                  </Badge>
                </div>
                <pre className="text-xs bg-background p-2 rounded mb-3 overflow-x-auto">
                  {JSON.stringify(req.args, null, 2)}
                </pre>
                <div className="flex gap-2">
                  <Button
                    size="sm"
                    onClick={() => handleApprove(req.id)}
                    disabled={processing === req.id}
                    className="flex-1"
                  >
                    {processing === req.id ? (
                      <Loader2 className="h-4 w-4 animate-spin" />
                    ) : (
                      <CheckCircle className="h-4 w-4 mr-1" />
                    )}
                    Approve
                  </Button>
                  <Button
                    size="sm"
                    variant="destructive"
                    onClick={() => handleDeny(req.id)}
                    disabled={processing === req.id}
                    className="flex-1"
                  >
                    <XCircle className="h-4 w-4 mr-1" />
                    Deny
                  </Button>
                </div>
              </div>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
