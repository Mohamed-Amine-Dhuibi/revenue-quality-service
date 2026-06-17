// Shared colour semantics used across charts and badges.
import type { Decision } from "./types";

export const CATEGORY_COLORS: Record<string, string> = {
  commercial_likely: "#14b8a6", // teal — good revenue
  intercompany_or_related_party_likely: "#f59e0b", // amber — suspect
  personal_to_business_likely: "#a855f7", // violet — owner funding
  unclassified: "#64748b", // slate — unknown
};

export const CATEGORY_LABELS: Record<string, string> = {
  commercial_likely: "Commercial",
  intercompany_or_related_party_likely: "Intercompany / related",
  personal_to_business_likely: "Personal → business",
  unclassified: "Unclassified",
};

export interface DecisionStyle {
  label: string;
  color: string;
  tagline: string;
}

export const DECISION_STYLE: Record<Decision, DecisionStyle> = {
  trust_reported_revenue: {
    label: "Trust reported revenue",
    color: "#22c55e",
    tagline: "Inflows look like genuine commercial revenue.",
  },
  verify_with_vat_returns: {
    label: "Verify with VAT returns",
    color: "#f59e0b",
    tagline: "Mixed signals — cross-check against filed VAT returns.",
  },
  decline: {
    label: "Decline",
    color: "#ef4444",
    tagline: "Revenue appears fabricated or recycled.",
  },
};

// Score band colour (matches recommendation thresholds 70 / 40).
export function scoreColor(score: number): string {
  if (score >= 70) return "#22c55e";
  if (score >= 40) return "#f59e0b";
  return "#ef4444";
}
