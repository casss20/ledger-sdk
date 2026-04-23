export const kpis = [
  { label: "Pending reviews", value: "18", delta: "+3 today", tone: "warning" },
  { label: "Blocked actions", value: "42", delta: "+8%", tone: "danger" },
  { label: "Approved actions", value: "1,284", delta: "+4.2%", tone: "success" },
  { label: "Active agents", value: "27", delta: "2 restricted", tone: "neutral" },
  { label: "Critical incidents", value: "3", delta: "Needs review", tone: "danger" },
] as const;
