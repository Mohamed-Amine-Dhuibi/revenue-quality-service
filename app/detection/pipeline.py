"""Orchestration: parsed rows -> the complete /analyse response.

This is the one place that wires the stages together (classify -> detect ->
score -> recommend) and assembles the rich, report-ready payload. Pure function
over already-parsed rows so it can be tested without HTTP or file I/O.
"""
from __future__ import annotations

from ..core.normalize import learn_borrower_profile
from .anomalies import _txn_view, detect_all
from .classifier import classify_inflows
from .scoring import compute_score, recommend


def _period(rows: list[dict]) -> dict:
    dates = sorted(r["date"] for r in rows)
    start, end = dates[0], dates[-1]
    months = (end.year - start.year) * 12 + (end.month - start.month) + 1
    return {"start": start.isoformat(), "end": end.isoformat(), "months": months}


def _monthly_inflow_series(inflows: list[dict]) -> list[dict]:
    buckets: dict[str, dict] = {}
    for r in inflows:
        key = f"{r['date'].year:04d}-{r['date'].month:02d}"
        b = buckets.setdefault(key, {"month": key, "total": 0.0, "count": 0})
        b["total"] += r["amount"]
        b["count"] += 1
    series = sorted(buckets.values(), key=lambda b: b["month"])
    for b in series:
        b["total"] = round(b["total"], 2)
    return series


def _top_counterparties(inflows: list[dict], labels: list[str], limit: int = 10) -> list[dict]:
    agg: dict[str, dict] = {}
    for r, lbl in zip(inflows, labels):
        a = agg.setdefault(
            r["counterparty_raw"], {"counterparty": r["counterparty_raw"],
                                    "category": lbl, "total": 0.0, "count": 0}
        )
        a["total"] += r["amount"]
        a["count"] += 1
    ranked = sorted(agg.values(), key=lambda a: -a["total"])[:limit]
    for a in ranked:
        a["total"] = round(a["total"], 2)
    return ranked


def run_analysis(
    rows: list[dict],
    parse_report: dict,
    *,
    borrower_name: str | None = None,
    currency: str = "SAR",
) -> dict:
    """Build the full analysis response from parsed transaction rows."""
    inflows = [r for r in rows if r["is_inflow"]]
    outflows = [r for r in rows if not r["is_inflow"]]
    total_inflow = sum(r["amount"] for r in inflows)
    total_outflow = sum(r["amount"] for r in outflows)

    period = _period(rows)
    months = max(period["months"], 1)

    # --- Detection stages --------------------------------------------------
    profile = learn_borrower_profile(inflows, borrower_name=borrower_name)
    labels, breakdown = classify_inflows(inflows, profile)
    anomalies = detect_all(inflows, labels, total_inflow)
    scoring = compute_score(breakdown, anomalies)
    recommendation = recommend(scoring["score"], breakdown)

    # --- Report-ready extras ----------------------------------------------
    flagged_round = anomalies["round_number_bias"]["evidence"][:5]
    report = {
        "monthly_inflow_series": _monthly_inflow_series(inflows),
        "top_inflow_counterparties": _top_counterparties(inflows, labels),
        "sample_flagged_transactions": {
            "round_number": flagged_round,
            "related_party": [
                _txn_view(r)
                for r, lbl in zip(inflows, labels)
                if lbl in ("intercompany_or_related_party_likely",
                           "personal_to_business_likely")
            ][:5],
        },
        "notes": [
            "Inflows are identified by a positive amount (credit). Outflows are ignored "
            "for revenue-quality purposes.",
            "Percentages in inflow_breakdown are of inflow value, not transaction count.",
            "Annualised estimate is a naive extrapolation of observed inflow over the "
            "covered period and is context, not a substitute for audited accounts.",
        ],
    }

    return {
        "meta": {
            "currency": currency,
            "rows_total": parse_report["rows_total"],
            "rows_parsed": parse_report["rows_parsed"],
            "rows_skipped": parse_report["rows_skipped"],
            "skipped_examples": parse_report["skipped_examples"],
            "period": period,
            "inflow_transactions": len(inflows),
            "outflow_transactions": len(outflows),
            "total_inflow": round(total_inflow, 2),
            "total_outflow": round(total_outflow, 2),
            "annualised_inflow_estimate": round(total_inflow / months * 12, 2),
            "borrower_profile": profile.as_dict(),
        },
        "inflow_breakdown": breakdown,
        "pattern_anomalies": anomalies,
        "revenue_quality_score": scoring["score"],
        "score_breakdown": scoring,
        "recommendation": recommendation,
        "report": report,
    }
