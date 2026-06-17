"""Classify each inflow into one of four revenue-quality buckets, with a
confidence level.

Categories:
  - commercial_likely                       genuine third-party customer revenue
  - intercompany_or_related_party_likely    money from the borrower's own group
  - personal_to_business_likely             owner topping up the company
  - unclassified                            no rule matched

The rules run in two tiers (see core/constants.py):

  STRONG (high confidence) — explicit markers, learned brand/owner tokens, and a
  known-external-corporate allow-list. These classify directly.

  WEAK (medium/low confidence) — honorific + person-name shape, corporate-form
  names, generic revenue words. These only fire when no STRONG rule matched, so
  they raise recall on unseen statements without letting an ambiguous word
  override a confident classification.

Precedence is deliberate: personal and related-party are checked before
commercial so a suspicious inflow is never laundered into the commercial bucket.
A counterparty carrying a group/holding suffix but with no shared brand token is
classified commercial at LOW confidence with a "verify" reason rather than
mislabelled — this is what stops false positives like "Peak Advisory Group".
"""
from __future__ import annotations

from typing import NamedTuple

from ..core.constants import (
    COMMERCIAL_STRONG,
    COMMERCIAL_WEAK,
    INTERCOMPANY_STRONG,
    PERSONAL_STRONG,
    PERSONAL_WEAK_TITLES,
    RELATED_PARTY_WEAK,
)
from ..core.normalize import (
    BorrowerProfile,
    contains_any,
    looks_like_company,
    looks_like_person_name,
    tokens,
)

COMMERCIAL = "commercial_likely"
INTERCOMPANY = "intercompany_or_related_party_likely"
PERSONAL = "personal_to_business_likely"
UNCLASSIFIED = "unclassified"

CATEGORIES = (COMMERCIAL, INTERCOMPANY, PERSONAL, UNCLASSIFIED)


class Classification(NamedTuple):
    label: str
    confidence: str  # "high" | "medium" | "low"
    reason: str


def classify_inflow(row: dict, profile: BorrowerProfile) -> Classification:
    """Return the bucket, confidence and reason for a single inflow row."""
    text = f"{row['description']} {row['counterparty_raw']}"
    cp = row["counterparty_raw"]
    cp_tokens = set(tokens(cp))

    # ---- STRONG tier (high confidence) -----------------------------------
    if contains_any(text, PERSONAL_STRONG):
        return Classification(PERSONAL, "high", "personal/own-account marker")
    if profile.owner_tokens & cp_tokens:
        return Classification(PERSONAL, "high", "owner name token")

    if contains_any(text, INTERCOMPANY_STRONG):
        return Classification(INTERCOMPANY, "high", "intercompany marker")
    if profile.related_tokens & cp_tokens:
        return Classification(INTERCOMPANY, "high", "shared brand token")

    if contains_any(text, COMMERCIAL_STRONG):
        return Classification(COMMERCIAL, "high", "commercial payment marker")

    # ---- WEAK tier (medium / low confidence) -----------------------------
    if contains_any(text, PERSONAL_WEAK_TITLES) or looks_like_person_name(cp):
        return Classification(PERSONAL, "medium", "person-name pattern")

    if looks_like_company(cp) or contains_any(text, COMMERCIAL_WEAK):
        # A corporate-form name with a group/holding suffix but no shared brand
        # token is most likely an external customer — but could be related party,
        # so keep it commercial and flag it rather than guess.
        if contains_any(cp, RELATED_PARTY_WEAK):
            return Classification(
                COMMERCIAL, "low",
                "corporate-form name with group/holding suffix — verify not related-party",
            )
        return Classification(COMMERCIAL, "medium", "corporate-form name")

    return Classification(UNCLASSIFIED, "low", "no rule matched")


def classify_inflows(
    inflows: list[dict], profile: BorrowerProfile
) -> tuple[list[Classification], dict]:
    """Classify every inflow and aggregate into the breakdown structure.

    Returns ``(classifications, breakdown)`` where ``classifications[i]`` is the
    :class:`Classification` of ``inflows[i]`` and ``breakdown`` has
    ``total_inflow`` plus a per-category ``{total, count, percentage}`` map.
    Percentages are of inflow *value*.
    """
    classifications = [classify_inflow(r, profile) for r in inflows]
    total_value = sum(r["amount"] for r in inflows) or 0.0

    categories: dict[str, dict] = {
        c: {"total": 0.0, "count": 0, "percentage": 0.0} for c in CATEGORIES
    }
    for row, cls in zip(inflows, classifications):
        categories[cls.label]["total"] += row["amount"]
        categories[cls.label]["count"] += 1

    for c in CATEGORIES:
        categories[c]["total"] = round(categories[c]["total"], 2)
        categories[c]["percentage"] = (
            round(100 * categories[c]["total"] / total_value, 2) if total_value else 0.0
        )

    breakdown = {
        "total_inflow": round(total_value, 2),
        "categories": categories,
    }
    return classifications, breakdown


def confidence_summary(inflows: list[dict], classifications: list[Classification]) -> dict:
    """Share of inflow *value* classified at each confidence level — a precision
    signal for reviewers (how much of the breakdown rests on strong evidence)."""
    total = sum(r["amount"] for r in inflows) or 0.0
    by_conf = {"high": 0.0, "medium": 0.0, "low": 0.0}
    for row, cls in zip(inflows, classifications):
        by_conf[cls.confidence] = by_conf.get(cls.confidence, 0.0) + row["amount"]
    return {
        level: {
            "value": round(val, 2),
            "percentage": round(100 * val / total, 2) if total else 0.0,
        }
        for level, val in by_conf.items()
    }
