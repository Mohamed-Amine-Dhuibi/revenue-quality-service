import type { AnalyseResponse } from "../types";
import { compactMoney, pct } from "../format";

export default function StatCards({ data }: { data: AnalyseResponse }) {
  const { meta, inflow_breakdown } = data;
  const ccy = meta.currency;
  const commercial =
    inflow_breakdown.categories["commercial_likely"]?.percentage ?? 0;

  const cards = [
    {
      label: "Total inflow",
      value: compactMoney(meta.total_inflow, ccy),
      hint: `${meta.inflow_transactions} inflows over ${meta.period.months} mo`,
    },
    {
      label: "Annualised inflow",
      value: compactMoney(meta.annualised_inflow_estimate, ccy),
      hint: "naive extrapolation of observed cash",
    },
    {
      label: "Commercial share",
      value: pct(commercial),
      hint: "of inflow value is genuine revenue",
    },
    {
      label: "Period",
      value: `${meta.period.start} → ${meta.period.end}`,
      hint: `${meta.rows_parsed} rows parsed${meta.rows_skipped ? `, ${meta.rows_skipped} skipped` : ""}`,
    },
  ];

  return (
    <div className="grid cols-4">
      {cards.map((c) => (
        <div className="card" key={c.label}>
          <div className="stat">
            <span className="label">{c.label}</span>
            <span className="value">{c.value}</span>
            <span className="hint">{c.hint}</span>
          </div>
        </div>
      ))}
    </div>
  );
}
