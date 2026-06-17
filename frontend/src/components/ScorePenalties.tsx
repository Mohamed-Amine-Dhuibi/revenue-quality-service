import type { ScoreBreakdown } from "../types";
import { titleize } from "../format";

// Each bar shows how many points a red flag subtracted, against its max.
export default function ScorePenalties({ breakdown }: { breakdown: ScoreBreakdown }) {
  const maxOfMax = Math.max(...breakdown.components.map((c) => c.max_penalty));
  return (
    <div className="card">
      <h2>Why this score</h2>
      <div className="sub">
        Started at 100, lost {breakdown.total_penalty.toFixed(1)} points across these
        factors
      </div>
      {breakdown.components.map((c) => {
        const pctOfMax = c.max_penalty ? (c.penalty / c.max_penalty) * 100 : 0;
        // Track width scales by the factor's max weight, so heavier factors read wider.
        const trackPct = (c.max_penalty / maxOfMax) * 100;
        const color =
          pctOfMax > 66 ? "var(--red)" : pctOfMax > 33 ? "var(--amber)" : "var(--teal)";
        return (
          <div className="bar-row" key={c.name} title={c.explanation}>
            <span className="name">{titleize(c.name)}</span>
            <div className="bar-track" style={{ width: `${Math.max(trackPct, 18)}%` }}>
              <div
                className="bar-fill"
                style={{ width: `${pctOfMax}%`, background: color }}
              />
            </div>
            <span className="num">
              −{c.penalty.toFixed(1)}
              <span className="muted" style={{ fontWeight: 400 }}>
                /{c.max_penalty}
              </span>
            </span>
          </div>
        );
      })}
    </div>
  );
}
