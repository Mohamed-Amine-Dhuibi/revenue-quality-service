import { Cell, Pie, PieChart, ResponsiveContainer, Tooltip } from "recharts";
import type { InflowBreakdown } from "../types";
import { CATEGORY_COLORS, CATEGORY_LABELS } from "../theme";
import { compactMoney, money, pct } from "../format";

const ORDER = [
  "commercial_likely",
  "intercompany_or_related_party_likely",
  "personal_to_business_likely",
  "unclassified",
];

export default function InflowDonut({
  breakdown,
  currency,
}: {
  breakdown: InflowBreakdown;
  currency: string;
}) {
  const rows = ORDER.filter((k) => breakdown.categories[k]).map((k) => ({
    key: k,
    label: CATEGORY_LABELS[k],
    color: CATEGORY_COLORS[k],
    ...breakdown.categories[k],
  }));
  const data = rows.filter((r) => r.total > 0);

  return (
    <div className="card">
      <h2>Inflow breakdown</h2>
      <div className="sub">Where the money actually comes from (by value)</div>
      <div className="grid cols-2" style={{ alignItems: "center", gap: 8 }}>
        <div style={{ position: "relative", height: 200 }}>
          <ResponsiveContainer width="100%" height="100%">
            <PieChart>
              <Pie
                data={data}
                dataKey="total"
                nameKey="label"
                innerRadius={62}
                outerRadius={92}
                paddingAngle={2}
                stroke="none"
              >
                {data.map((r) => (
                  <Cell key={r.key} fill={r.color} />
                ))}
              </Pie>
              <Tooltip
                formatter={(v: number, _n, p) =>
                  [`${money(v, currency)} (${pct((p.payload as { percentage: number }).percentage)})`, (p.payload as { label: string }).label]
                }
              />
            </PieChart>
          </ResponsiveContainer>
          <div
            style={{
              position: "absolute",
              inset: 0,
              display: "grid",
              placeItems: "center",
              pointerEvents: "none",
            }}
          >
            <div style={{ textAlign: "center" }}>
              <div style={{ fontSize: 18, fontWeight: 700 }}>
                {compactMoney(breakdown.total_inflow, currency)}
              </div>
              <div style={{ fontSize: 11, color: "var(--muted)" }}>total inflow</div>
            </div>
          </div>
        </div>

        <div className="legend">
          {rows.map((r) => (
            <div className="item" key={r.key}>
              <span className="swatch" style={{ background: r.color }} />
              <span>
                {r.label} <span className="muted">· {r.count}</span>
              </span>
              <span className="pctval">{pct(r.percentage)}</span>
              <span className="totval">{compactMoney(r.total, currency)}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
