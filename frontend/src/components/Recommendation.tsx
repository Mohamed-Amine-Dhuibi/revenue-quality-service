import type { Recommendation } from "../types";
import { DECISION_STYLE } from "../theme";

const ICON: Record<string, string> = {
  trust_reported_revenue: "✓",
  verify_with_vat_returns: "!",
  decline: "✕",
};

export default function RecommendationBanner({ rec }: { rec: Recommendation }) {
  const style = DECISION_STYLE[rec.decision];
  return (
    <div className="rec" style={{ ["--rec-color" as string]: style.color }}>
      <div className="rec-icon">{ICON[rec.decision]}</div>
      <div>
        <div className="rec-label">{style.label}</div>
        <div className="rec-just">{rec.justification}</div>
      </div>
    </div>
  );
}
