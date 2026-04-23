export type ApprovalItem = {
  id: string;
  status: "approved" | "pending" | "blocked";
  risk: "Low" | "Medium" | "High" | "Critical";
  agent: string;
  action: string;
  target: string;
  policy: string;
  requestedAt: string;
  waiting: string;
  decision: string;
  traceId?: string;
  owner?: string;
};
