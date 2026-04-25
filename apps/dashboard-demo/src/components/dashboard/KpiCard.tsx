type Props = {
  label: string;
  value: string;
  delta?: string;
  tone?: "neutral" | "success" | "warning" | "danger";
};

export function KpiCard({ label, value, delta, tone = "neutral" }: Props) {
  return (
    <section className={`card kpi-card tone-${tone}`}>
      <div className="kpi-card__label">{label}</div>
      <div className="kpi-card__value metric-value">{value}</div>
      {delta ? <div className="kpi-card__delta">{delta}</div> : null}
    </section>
  );
}
