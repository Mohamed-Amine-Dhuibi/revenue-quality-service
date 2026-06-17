"""Classify each inflow into one of four revenue-quality buckets.

Categories:
  - commercial_likely                       genuine third-party customer revenue
  - intercompany_or_related_party_likely    money from the borrower's own group
  - personal_to_business_likely             owner topping up the company
  - unclassified                            no rule matched

Precedence is deliberate: *personal* and *related-party* are checked before
*commercial*, because a suspicious inflow that merely also looks like a wire
(e.g. "OWN ACCT TRF") must not be laundered into the commercial bucket.

Design choice on false positives: related-party is flagged only on an explicit
``INTERCOMPANY`` marker or a counterparty that shares a *learned brand token*
with the borrower's own intra-group transfers — NOT on generic words like
"Group"/"Holding" alone, which legitimate customers often carry.
"""
from __future__ import annotations

from ..core.constants import COMMERCIAL_MARKERS, INTERCOMPANY_MARKERS, PERSONAL_MARKERS
from ..core.normalize import BorrowerProfile, contains_any, tokens

COMMERCIAL = "commercial_likely"
INTERCOMPANY = "intercompany_or_related_party_likely"
PERSONAL = "personal_to_business_likely"
UNCLASSIFIED = "unclassified"

CATEGORIES = (COMMERCIAL, INTERCOMPANY, PERSONAL, UNCLASSIFIED)


def classify_inflow(row: dict, profile: BorrowerProfile) -> str:
    """Return the bucket for a single inflow row."""
    text = f"{row['description']} {row['counterparty_raw']}"
    cp_tokens = set(tokens(row["counterparty_raw"]))

    # 1) Owner / personal money — explicit marker or owner's name tokens.
    if contains_any(text, PERSONAL_MARKERS) or (profile.owner_tokens & cp_tokens):
        return PERSONAL

    # 2) Intercompany / related party — explicit marker or shared brand token.
    if contains_any(text, INTERCOMPANY_MARKERS) or (profile.related_tokens & cp_tokens):
        return INTERCOMPANY

    # 3) Looks like a genuine inbound commercial payment.
    if contains_any(text, COMMERCIAL_MARKERS):
        return COMMERCIAL

    # 4) Couldn't explain it.
    return UNCLASSIFIED


def classify_inflows(
    inflows: list[dict], profile: BorrowerProfile
) -> tuple[list[str], dict]:
    """Label every inflow and aggregate into the breakdown structure.

    Returns ``(labels, breakdown)`` where ``labels[i]`` is the category of
    ``inflows[i]`` and ``breakdown`` has ``total_inflow`` plus a per-category
    ``{total, count, percentage}`` map. Percentages are of inflow *value*.
    """
    labels = [classify_inflow(r, profile) for r in inflows]
    total_value = sum(r["amount"] for r in inflows) or 0.0

    categories: dict[str, dict] = {
        c: {"total": 0.0, "count": 0, "percentage": 0.0} for c in CATEGORIES
    }
    for row, label in zip(inflows, labels):
        categories[label]["total"] += row["amount"]
        categories[label]["count"] += 1

    for c in CATEGORIES:
        categories[c]["total"] = round(categories[c]["total"], 2)
        categories[c]["percentage"] = (
            round(100 * categories[c]["total"] / total_value, 2) if total_value else 0.0
        )

    breakdown = {
        "total_inflow": round(total_value, 2),
        "categories": categories,
    }
    return labels, breakdown
