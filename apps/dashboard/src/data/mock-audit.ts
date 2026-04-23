export const auditEvents = [
  {
    id: "aud_1",
    time: "2026-04-23 01:58:04",
    actor: "Payments-Agent-01",
    action: "request.refund",
    target: "stripe.customer.2841",
    outcome: "Escalated",
    traceId: "trc_9ad4f2",
  },
  {
    id: "aud_2",
    time: "2026-04-23 01:42:33",
    actor: "Outreach-Agent-02",
    action: "send.email",
    target: "crm.batch.18",
    outcome: "Blocked",
    traceId: "trc_8bc113",
  },
  {
    id: "aud_3",
    time: "2026-04-23 01:31:18",
    actor: "Repo-Agent-07",
    action: "github.merge",
    target: "governance-docs.main",
    outcome: "Allowed",
    traceId: "trc_73ca21",
  },
];
