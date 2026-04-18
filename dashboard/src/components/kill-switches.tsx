import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { useKillSwitches, useKillSwitch, useReviveSwitch } from "@/lib/hooks";
import { Power, PowerOff, Loader2 } from "lucide-react";
import { useState } from "react";

export function KillSwitches() {
  const { data: switches = [], isLoading } = useKillSwitches();
  const killMutation = useKillSwitch();
  const reviveMutation = useReviveSwitch();
  const [processing, setProcessing] = useState<string | null>(null);

  const handleToggle = async (sw: { name: string; enabled: boolean }) => {
    setProcessing(sw.name);
    if (sw.enabled) {
      await killMutation.mutateAsync(sw.name);
    } else {
      await reviveMutation.mutateAsync(sw.name);
    }
    setProcessing(null);
  };

  return (
    <Card className="h-[500px] flex flex-col">
      <CardHeader>
        <div className="flex items-center justify-between">
          <CardTitle className="flex items-center gap-2">
            🛑 Kill Switches
            <div className="h-2 w-2 rounded-full bg-accent-success animate-pulse" />
          </CardTitle>
        </div>
      </CardHeader>
      <CardContent className="flex-1 overflow-auto">
        {isLoading ? (
          <div className="flex items-center justify-center h-full">
            <Loader2 className="h-8 w-8 animate-spin text-primary" />
          </div>
        ) : (
          <div className="space-y-3">
            {switches.map((sw) => (
              <div
                key={sw.name}
                className="flex items-center justify-between p-4 rounded-lg border bg-card"
              >
                <div className="flex-1 min-w-0">
                  <div className="font-semibold flex items-center gap-2">
                    {sw.name}
                    <Badge
                      variant="outline"
                      className={
                        sw.enabled
                          ? "border-accent-success text-accent-success"
                          : "border-accent-danger text-accent-danger"
                      }
                    >
                      {sw.enabled ? "ACTIVE" : "KILLED"}
                    </Badge>
                  </div>
                  {sw.reason && (
                    <div className="text-sm text-muted-foreground truncate">
                      {sw.reason}
                    </div>
                  )}
                </div>
                <Button
                  size="sm"
                  variant={sw.enabled ? "destructive" : "default"}
                  onClick={() => handleToggle(sw)}
                  disabled={processing === sw.name}
                >
                  {processing === sw.name ? (
                    <Loader2 className="h-4 w-4 animate-spin" />
                  ) : sw.enabled ? (
                    <>
                      <PowerOff className="h-4 w-4 mr-1" />
                      Kill
                    </>
                  ) : (
                    <>
                      <Power className="h-4 w-4 mr-1" />
                      Revive
                    </>
                  )}
                </Button>
              </div>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
