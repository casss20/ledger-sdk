type Props = {
  status: "approved" | "pending" | "blocked" | "rejected";
};

export function StatusPill({ status }: Props) {
  const map = {
    approved: "status-badge status-approved",
    pending: "status-badge status-pending",
    blocked: "status-badge status-blocked",
    rejected: "status-badge status-blocked",
  };

  return <span className={map[status]}>{status}</span>;
}
