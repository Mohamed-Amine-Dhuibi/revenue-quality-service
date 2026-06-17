import type { AnalyseResponse } from "../types";
import ScoreGauge from "./ScoreGauge";
import RecommendationBanner from "./Recommendation";
import StatCards from "./StatCards";
import InflowDonut from "./InflowDonut";
import ScorePenalties from "./ScorePenalties";
import AnomaliesGrid from "./AnomaliesGrid";
import MonthlyInflowChart from "./MonthlyInflowChart";
import CounterpartiesChart from "./CounterpartiesChart";

export default function Dashboard({
  data,
  onReset,
}: {
  data: AnalyseResponse;
  onReset: () => void;
}) {
  const ccy = data.meta.currency;
  return (
    <>
      <div className="topbar">
        <div className="brand">
          <div className="logo">RQ</div>
          <div>
            <h1>Revenue Quality Report</h1>
            <p>
              {data.meta.period.start} → {data.meta.period.end} ·{" "}
              {data.meta.inflow_transactions} inflows · {ccy}
            </p>
          </div>
        </div>
        <button className="btn ghost" onClick={onReset}>
          ↻ Analyse another
        </button>
      </div>

      {/* Hero: gauge + recommendation + why-this-score */}
      <div className="grid hero">
        <div className="card" style={{ display: "grid", placeItems: "center" }}>
          <ScoreGauge score={data.revenue_quality_score} />
        </div>
        <div className="grid" style={{ gridTemplateRows: "auto 1fr", gap: 18 }}>
          <RecommendationBanner rec={data.recommendation} />
          <ScorePenalties breakdown={data.score_breakdown} />
        </div>
      </div>

      <div style={{ height: 18 }} />
      <StatCards data={data} />

      <div className="section-title">Inflow composition</div>
      <div className="grid cols-2">
        <InflowDonut breakdown={data.inflow_breakdown} currency={ccy} />
        <CounterpartiesChart rows={data.report.top_inflow_counterparties} currency={ccy} />
      </div>

      <div className="section-title">Pattern anomalies</div>
      <AnomaliesGrid anomalies={data.pattern_anomalies} currency={ccy} />

      <div className="section-title">Cash-flow timing</div>
      <MonthlyInflowChart data={data} />

      <div style={{ height: 18 }} />
      <div className="card">
        <h2>Method notes</h2>
        <ul className="note-list" style={{ marginTop: 10 }}>
          {data.report.notes.map((n, i) => (
            <li key={i}>{n}</li>
          ))}
        </ul>
      </div>
    </>
  );
}
