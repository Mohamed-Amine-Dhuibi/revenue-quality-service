import type { ReactNode } from "react";
import type { PatternAnomalies } from "../types";
import { compactMoney, money, sharePct } from "../format";

function StatusPill({ detected }: { detected: boolean }) {
  return (
    <span className={`pill ${detected ? "detected" : "clear"}`}>
      <span
        className="dot"
        style={{ background: detected ? "var(--red)" : "var(--green)" }}
      />
      {detected ? "Flagged" : "Clear"}
    </span>
  );
}

// Horizontal share bar with an optional dashed baseline marker.
function ShareBar({
  share,
  baseline,
  color = "var(--amber)",
}: {
  share: number;
  baseline?: number;
  color?: string;
}) {
  const w = Math.min(1, Math.max(0, share)) * 100;
  return (
    <div className="bar-track" style={{ height: 12, margin: "8px 0 4px" }}>
      <div className="bar-fill" style={{ width: `${w}%`, background: color }} />
      {baseline !== undefined && (
        <div
          title={`expected ≈ ${sharePct(baseline)}`}
          style={{
            position: "absolute",
            left: `${Math.min(100, baseline * 100)}%`,
            top: -2,
            bottom: -2,
            width: 2,
            background: "#e8edf7",
            opacity: 0.7,
          }}
        />
      )}
    </div>
  );
}

function Card({
  title,
  detected,
  headline,
  children,
}: {
  title: string;
  detected: boolean;
  headline: string;
  children?: ReactNode;
}) {
  return (
    <div className="card">
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <h3>{title}</h3>
        <StatusPill detected={detected} />
      </div>
      <div style={{ fontSize: 18, fontWeight: 700, margin: "10px 0 2px" }}>{headline}</div>
      {children}
    </div>
  );
}

export default function AnomaliesGrid({
  anomalies,
  currency,
}: {
  anomalies: PatternAnomalies;
  currency: string;
}) {
  const round = anomalies.round_number_bias;
  const repeats = anomalies.identical_amount_repeats;
  const eom = anomalies.end_of_month_spike;
  const rp = anomalies.suspected_intercompany_or_related_party_flows;

  return (
    <div className="grid cols-2">
      {/* Round-number bias */}
      <Card
        title="Round-number bias"
        detected={round.detected}
        headline={`${sharePct(round.value_share)} of value is round`}
      >
        <ShareBar share={round.value_share} baseline={round.expected_by_chance} />
        <div className="muted" style={{ fontSize: 12 }}>
          {round.count} inflows are exact multiples of {round.divisor.toLocaleString()} (expected
          by chance ≈ {sharePct(round.expected_by_chance, 2)})
        </div>
        {round.evidence.length > 0 && (
          <table className="tbl" style={{ marginTop: 10 }}>
            <tbody>
              {round.evidence.slice(0, 4).map((t, i) => (
                <tr key={i}>
                  <td>{t.date}</td>
                  <td>{t.counterparty}</td>
                  <td className="num">{money(t.amount, currency)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </Card>

      {/* Identical-amount repeats */}
      <Card
        title="Identical-amount repeats"
        detected={repeats.detected}
        headline={`${repeats.repeated_clusters} repeated amount${repeats.repeated_clusters === 1 ? "" : "s"}`}
      >
        <ShareBar share={repeats.value_share} color="var(--violet)" />
        <div className="muted" style={{ fontSize: 12 }}>
          {sharePct(repeats.value_share)} of inflow value sits on amounts seen ≥{" "}
          {repeats.min_count} times
        </div>
        {repeats.evidence.length > 0 && (
          <table className="tbl" style={{ marginTop: 10 }}>
            <thead>
              <tr>
                <th>Amount</th>
                <th className="num">×</th>
                <th className="num">Total</th>
              </tr>
            </thead>
            <tbody>
              {repeats.evidence.slice(0, 4).map((c, i) => (
                <tr key={i}>
                  <td>{money(c.amount, currency)}</td>
                  <td className="num">{c.count}</td>
                  <td className="num">{compactMoney(c.total, currency)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </Card>

      {/* End-of-month spike */}
      <Card
        title="End-of-month spike"
        detected={eom.detected}
        headline={`${sharePct(eom.value_share)} in last ${eom.window_days} days`}
      >
        <ShareBar share={eom.value_share} baseline={eom.expected_share} color="var(--amber)" />
        <div className="muted" style={{ fontSize: 12 }}>
          {compactMoney(eom.last_days_value, currency)} across {eom.last_days_count} inflows landed
          at month-end (expected ≈ {sharePct(eom.expected_share)})
        </div>
      </Card>

      {/* Related-party flows */}
      <Card
        title="Suspected related-party flows"
        detected={rp.detected}
        headline={`${sharePct(rp.value_share)} from related parties`}
      >
        <ShareBar share={rp.value_share} color="var(--amber)" />
        <div className="muted" style={{ fontSize: 12 }}>
          {rp.count} inflows ({compactMoney(rp.flagged_value, currency)}) from intercompany / owner
          sources
        </div>
        {rp.counterparties.length > 0 && (
          <table className="tbl" style={{ marginTop: 10 }}>
            <tbody>
              {rp.counterparties.slice(0, 4).map((c, i) => (
                <tr key={i}>
                  <td>{c.counterparty}</td>
                  <td className="num">{compactMoney(c.total, currency)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </Card>
    </div>
  );
}
