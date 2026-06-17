"""Revenue quality score (0-100) and the lending recommendation.

The score is an additive penalty model: start at 100 (perfectly trustworthy) and
subtract a weighted penalty for each red flag. Every weight, baseline and
saturation point is a named constant in ``core/constants.py`` and is defended in
the README. The model is intentionally transparent — a lender can read off
exactly why a borrower lost points.

    score = 100
            - W_RELATED_PARTY * related_party_share
            - W_ROUND        * severity(round_share)
            - W_REPEAT       * severity(repeat_share)
            - W_MONTH_END    * severity(month_end_share)
            - W_UNCLASSIFIED * unclassified_share
"""
from __future__ import annotations

from ..core.constants import (
    DECLINE_THRESHOLD,
    MONTH_END_BASELINE_SHARE,
    MONTH_END_SATURATION_SHARE,
    REPEAT_BASELINE_SHARE,
    REPEAT_SATURATION_SHARE,
    ROUND_BASELINE_SHARE,
    ROUND_SATURATION_SHARE,
    TRUST_THRESHOLD,
    W_MONTH_END,
    W_RELATED_PARTY,
    W_REPEAT,
    W_ROUND,
    W_UNCLASSIFIED,
)
from .classifier import COMMERCIAL, INTERCOMPANY, PERSONAL, UNCLASSIFIED


def severity(share: float, baseline: float, saturation: float) -> float:
    """Map a raw share onto 0..1 severity.

    <= baseline   -> 0 (normal / explainable by chance)
    >= saturation -> 1 (maximally suspicious)
    linear in between.
    """
    if share <= baseline:
        return 0.0
    if share >= saturation:
        return 1.0
    return (share - baseline) / (saturation - baseline)


def _pct_share(breakdown: dict, category: str) -> float:
    return breakdown["categories"][category]["percentage"] / 100.0


def compute_score(breakdown: dict, anomalies: dict) -> dict:
    """Return ``{score, components}`` — the integer score plus the penalty audit."""
    related_party_share = _pct_share(breakdown, INTERCOMPANY) + _pct_share(
        breakdown, PERSONAL
    )
    unclassified_share = _pct_share(breakdown, UNCLASSIFIED)

    round_sev = severity(
        anomalies["round_number_bias"]["value_share"],
        ROUND_BASELINE_SHARE,
        ROUND_SATURATION_SHARE,
    )
    repeat_sev = severity(
        anomalies["identical_amount_repeats"]["value_share"],
        REPEAT_BASELINE_SHARE,
        REPEAT_SATURATION_SHARE,
    )
    month_sev = severity(
        anomalies["end_of_month_spike"]["value_share"],
        MONTH_END_BASELINE_SHARE,
        MONTH_END_SATURATION_SHARE,
    )

    components = [
        {
            "name": "related_party_inflows",
            "penalty": round(W_RELATED_PARTY * related_party_share, 2),
            "max_penalty": W_RELATED_PARTY,
            "driver_share": round(related_party_share, 4),
            "explanation": "Inflow value from intercompany/owner sources is not external revenue.",
        },
        {
            "name": "round_number_bias",
            "penalty": round(W_ROUND * round_sev, 2),
            "max_penalty": W_ROUND,
            "driver_share": anomalies["round_number_bias"]["value_share"],
            "explanation": "Suspiciously round inflow amounts suggest manufactured figures.",
        },
        {
            "name": "identical_amount_repeats",
            "penalty": round(W_REPEAT * repeat_sev, 2),
            "max_penalty": W_REPEAT,
            "driver_share": anomalies["identical_amount_repeats"]["value_share"],
            "explanation": "Exact amounts repeating point to scripted / recycled cash.",
        },
        {
            "name": "end_of_month_spike",
            "penalty": round(W_MONTH_END * month_sev, 2),
            "max_penalty": W_MONTH_END,
            "driver_share": anomalies["end_of_month_spike"]["value_share"],
            "explanation": "Value concentrated at month-end indicates target-hitting / window dressing.",
        },
        {
            "name": "unclassified_inflows",
            "penalty": round(W_UNCLASSIFIED * unclassified_share, 2),
            "max_penalty": W_UNCLASSIFIED,
            "driver_share": round(unclassified_share, 4),
            "explanation": "Inflows we could not attribute to any clear source.",
        },
    ]

    total_penalty = sum(c["penalty"] for c in components)
    score = int(round(max(0.0, min(100.0, 100.0 - total_penalty))))
    return {
        "score": score,
        "total_penalty": round(total_penalty, 2),
        "components": components,
    }


def recommend(score: int, breakdown: dict) -> dict:
    """Map score -> decision + a one-sentence, data-grounded justification."""
    commercial_pct = breakdown["categories"][COMMERCIAL]["percentage"]
    related_pct = round(
        breakdown["categories"][INTERCOMPANY]["percentage"]
        + breakdown["categories"][PERSONAL]["percentage"],
        2,
    )

    if score >= TRUST_THRESHOLD:
        decision = "trust_reported_revenue"
        justification = (
            f"Score {score}/100: inflows are predominantly genuine commercial revenue "
            f"({commercial_pct:.0f}% of value) with no material manipulation patterns."
        )
    elif score < DECLINE_THRESHOLD:
        decision = "decline"
        justification = (
            f"Score {score}/100: revenue quality is poor — {related_pct:.0f}% of inflow "
            f"value is related-party and manipulation patterns are strong, so the reported "
            f"figure cannot be relied upon."
        )
    else:
        decision = "verify_with_vat_returns"
        justification = (
            f"Score {score}/100: only {commercial_pct:.0f}% of inflow value is clearly "
            f"commercial and several manipulation signals are present, so confirm the "
            f"reported revenue against filed VAT returns before lending."
        )
    return {"decision": decision, "justification": justification}
