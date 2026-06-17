import {
  Bar,
  BarChart,
  Cell,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { TopCounterparty } from "../types";
import { CATEGORY_COLORS, CATEGORY_LABELS } from "../theme";
import { compactMoney, money } from "../format";

function shorten(name: string, n = 22): string {
  return name.length > n ? name.slice(0, n - 1) + "…" : name;
}

export default function CounterpartiesChart({
  rows,
  currency,
}: {
  rows: TopCounterparty[];
  currency: string;
}) {
  const data = rows.slice(0, 8).map((r) => ({
    name: shorten(r.counterparty),
    full: r.counterparty,
    total: r.total,
    category: r.category,
    color: CATEGORY_COLORS[r.category] ?? "#64748b",
  }));

  return (
    <div className="card">
      <h2>Top inflow counterparties</h2>
      <div className="sub">Coloured by classification</div>
      <ResponsiveContainer width="100%" height={Math.max(220, data.length * 34)}>
        <BarChart
          data={data}
          layout="vertical"
          margin={{ top: 0, right: 16, left: 8, bottom: 0 }}
        >
          <XAxis
            type="number"
            tickFormatter={(v: number) => compactMoney(v, currency).replace(`${currency} `, "")}
            tick={{ fill: "#8b96ad", fontSize: 11 }}
            stroke="#232c44"
          />
          <YAxis
            type="category"
            dataKey="name"
            width={150}
            tick={{ fill: "#c3ccde", fontSize: 11.5 }}
            stroke="#232c44"
          />
          <Tooltip
            cursor={{ fill: "rgba(255,255,255,0.04)" }}
            formatter={(v: number, _n, p) => [
              money(v, currency),
              CATEGORY_LABELS[(p.payload as { category: string }).category] ?? "—",
            ]}
            labelFormatter={(_l, p) => (p?.[0]?.payload as { full: string })?.full ?? ""}
          />
          <Bar dataKey="total" radius={[0, 5, 5, 0]}>
            {data.map((d) => (
              <Cell key={d.full} fill={d.color} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
