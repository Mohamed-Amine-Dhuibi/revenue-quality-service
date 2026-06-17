"""The four pattern-anomaly detectors.

Each detector is a pure function over the inflow rows and returns a dict with:
  - ``detected``      bool, did the pattern fire
  - ``value_share``   fraction of inflow *value* implicated (0..1) — what scoring uses
  - metrics + ``evidence`` so a human can see exactly which rows triggered it

The detectors describe *what* is anomalous; ``scoring.py`` decides *how much* it
costs. Keeping them separate makes both independently testable.
"""
from __future__ import annotations

import calendar

from ..core.constants import (
    IDENTICAL_REPEAT_MIN_COUNT,
    MONTH_END_WINDOW_DAYS,
    ROUND_NUMBER_DIVISOR,
    ROUND_NUMBER_MIN_AMOUNT,
)
from .classifier import INTERCOMPANY, PERSONAL


def _share(part: float, whole: float) -> float:
    return round(part / whole, 4) if whole else 0.0


def _txn_view(row: dict) -> dict:
    """A compact, JSON-friendly snapshot of a transaction for evidence lists."""
    return {
        "date": row["date"].isoformat(),
        "amount": round(row["amount"], 2),
        "counterparty": row["counterparty_raw"],
        "description": row["description"],
    }


def round_number_bias(inflows: list[dict], total_value: float) -> dict:
    """Inflows that are exact multiples of 1000 (configurable).

    Genuine invoices carry tax, fractional rates and fees, so they are almost
    never perfectly round; a high round share points to manufactured figures.
    Probability a real 2-decimal amount is an exact multiple of 1000 is ~0.1%.
    """
    flagged = [
        r
        for r in inflows
        if r["amount"] >= ROUND_NUMBER_MIN_AMOUNT
        and round(r["amount"], 2) % ROUND_NUMBER_DIVISOR == 0
    ]
    flagged_value = sum(r["amount"] for r in flagged)
    return {
        "detected": len(flagged) > 0,
        "value_share": _share(flagged_value, total_value),
        "count": len(flagged),
        "count_share": _share(len(flagged), len(inflows)),
        "flagged_value": round(flagged_value, 2),
        "divisor": ROUND_NUMBER_DIVISOR,
        "expected_by_chance": 1 / ROUND_NUMBER_DIVISOR,
        "evidence": [
            _txn_view(r) for r in sorted(flagged, key=lambda r: -r["amount"])[:10]
        ],
    }


def identical_amount_repeats(inflows: list[dict], total_value: float) -> dict:
    """Exact amounts that recur >= IDENTICAL_REPEAT_MIN_COUNT times.

    Independent customers paying real invoices rarely land on the identical
    figure repeatedly; tight clusters of an identical amount suggest scripted or
    recycled cash.
    """
    by_amount: dict[float, list[dict]] = {}
    for r in inflows:
        by_amount.setdefault(round(r["amount"], 2), []).append(r)

    clusters = [
        (amt, rows)
        for amt, rows in by_amount.items()
        if len(rows) >= IDENTICAL_REPEAT_MIN_COUNT
    ]
    clusters.sort(key=lambda c: (-len(c[1]), -c[0]))

    repeated_value = sum(amt * len(rows) for amt, rows in clusters)
    evidence = [
        {
            "amount": amt,
            "count": len(rows),
            "total": round(amt * len(rows), 2),
            "counterparties": sorted({r["counterparty_raw"] for r in rows})[:8],
        }
        for amt, rows in clusters[:10]
    ]
    return {
        "detected": len(clusters) > 0,
        "value_share": _share(repeated_value, total_value),
        "repeated_clusters": len(clusters),
        "repeated_value": round(repeated_value, 2),
        "min_count": IDENTICAL_REPEAT_MIN_COUNT,
        "evidence": evidence,
    }


def end_of_month_spike(inflows: list[dict], total_value: float) -> dict:
    """Concentration of inflow value in the last N calendar days of each month.

    Parking cash on the last few days to hit a monthly target is a classic
    window-dressing tell. Three trailing days is ~10% of a month by chance, so a
    much larger value share is suspicious.
    """
    months: dict[tuple[int, int], dict] = {}
    eom_value = 0.0
    eom_count = 0
    for r in inflows:
        d = r["date"]
        key = (d.year, d.month)
        m = months.setdefault(key, {"total": 0.0, "eom_total": 0.0, "eom_count": 0})
        m["total"] += r["amount"]
        last_day = calendar.monthrange(d.year, d.month)[1]
        if d.day >= last_day - (MONTH_END_WINDOW_DAYS - 1):
            m["eom_total"] += r["amount"]
            m["eom_count"] += 1
            eom_value += r["amount"]
            eom_count += 1

    per_month = [
        {
            "month": f"{y:04d}-{mo:02d}",
            "inflow_total": round(v["total"], 2),
            "last_days_total": round(v["eom_total"], 2),
            "last_days_count": v["eom_count"],
            "last_days_share": _share(v["eom_total"], v["total"]),
        }
        for (y, mo), v in sorted(months.items())
    ]
    # Naive expectation: window days as a fraction of an ~30.4-day month.
    expected = round(MONTH_END_WINDOW_DAYS / 30.4, 4)
    return {
        "detected": _share(eom_value, total_value) > expected,
        "value_share": _share(eom_value, total_value),
        "window_days": MONTH_END_WINDOW_DAYS,
        "expected_share": expected,
        "last_days_value": round(eom_value, 2),
        "last_days_count": eom_count,
        "by_month": per_month,
    }


def suspected_related_party_flows(
    inflows: list[dict], labels: list[str], total_value: float
) -> dict:
    """Inflows the classifier tagged as intercompany or personal/owner money.

    These are not genuine external revenue and lenders discount them; surfaced
    here as an explicit anomaly with the per-counterparty breakdown.
    """
    flagged = [
        (r, lbl) for r, lbl in zip(inflows, labels) if lbl in (INTERCOMPANY, PERSONAL)
    ]
    flagged_value = sum(r["amount"] for r, _ in flagged)

    by_cp: dict[str, dict] = {}
    for r, lbl in flagged:
        cp = by_cp.setdefault(
            r["counterparty_raw"], {"label": lbl, "total": 0.0, "count": 0}
        )
        cp["total"] += r["amount"]
        cp["count"] += 1
    counterparties = sorted(
        (
            {"counterparty": k, "label": v["label"],
             "total": round(v["total"], 2), "count": v["count"]}
            for k, v in by_cp.items()
        ),
        key=lambda x: -x["total"],
    )
    return {
        "detected": len(flagged) > 0,
        "value_share": _share(flagged_value, total_value),
        "count": len(flagged),
        "flagged_value": round(flagged_value, 2),
        "counterparties": counterparties[:15],
    }


def detect_all(inflows: list[dict], labels: list[str], total_value: float) -> dict:
    """Run every detector and return the ``pattern_anomalies`` block."""
    return {
        "round_number_bias": round_number_bias(inflows, total_value),
        "identical_amount_repeats": identical_amount_repeats(inflows, total_value),
        "end_of_month_spike": end_of_month_spike(inflows, total_value),
        "suspected_intercompany_or_related_party_flows": suspected_related_party_flows(
            inflows, labels, total_value
        ),
    }
