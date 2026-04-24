declare module '@citadel/widget-library' {
  export interface ActivityEvent {
    id: string;
    timestamp: string;
    severity: 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW';
    type: string;
    summary: string;
    agentId: string;
    actionable: boolean;
  }

  export interface ApprovalRequest {
    id: string;
    action: string;
    resource: string;
    actorId: string;
    timestamp: string;
    riskScore: number;
    reason: string;
  }

  export const ActivityStream: React.FC<{ events: ActivityEvent[] }>;
  export const ApprovalQueue: React.FC<{
    requests: ApprovalRequest[];
    onApprove: (id: string) => void;
    onReject: (id: string) => void;
  }>;
  export const KillSwitch: React.FC<{
    isActive: boolean;
    onToggle: (state: boolean) => Promise<void>;
  }>;
}
