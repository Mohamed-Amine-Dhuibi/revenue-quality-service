import {
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { AnalyseResponse } from "../types";
import { compactMoney, monthLabel, money } from "../format";

export default function MonthlyInflowChart({ data }: { data: AnalyseResponse }) {
  const ccy = data.meta.currency;
  const eomByMonth = new Map(
    data.pattern_anomalies.end_of_month_spike.by_month.map((m) => [
      m.month,
      m.last_days_total,
    ]),
  );

  const chart = data.report.monthly_inflow_series.map((m) => {
    const eom = eomByMonth.get(m.month) ?? 0;
    return {
      month: monthLabel(m.month),
      rest: Math.max(m.total - eom, 0),
      monthEnd: eom,
    };
  });

  return (
    <div className="card">
      <h2>Monthly inflow & month-end concentration</h2>
      <div className="sub">
        Amber = value landing in the last {data.pattern_anomalies.end_of_month_spike.window_days}{" "}
        days of each month
      </div>
      <ResponsiveContainer width="100%" height={250}>
        <BarChart data={chart} margin={{ top: 6, right: 8, left: 8, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#232c44" vertical={false} />
          <XAxis dataKey="month" tick={{ fill: "#8b96ad", fontSize: 12 }} stroke="#232c44" />
          <YAxis
            tickFormatter={(v: number) => compactMoney(v, ccy).replace(`${ccy} `, "")}
            tick={{ fill: "#8b96ad", fontSize: 11 }}
            stroke="#232c44"
            width={48}
          />
          <Tooltip
            cursor={{ fill: "rgba(255,255,255,0.04)" }}
            formatter={(v: number, n) => [money(v, ccy), n === "monthEnd" ? "Last 3 days" : "Rest of month"]}
          />
          <Legend
            formatter={(v) => (v === "monthEnd" ? "Last 3 days" : "Rest of month")}
            wrapperStyle={{ fontSize: 12 }}
          />
          <Bar dataKey="rest" stackId="a" fill="#3b4a6b" radius={[0, 0, 0, 0]} />
          <Bar dataKey="monthEnd" stackId="a" fill="#f59e0b" radius={[4, 4, 0, 0]} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
