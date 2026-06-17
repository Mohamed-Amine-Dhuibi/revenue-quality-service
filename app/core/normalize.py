"""Text normalisation and borrower-token learning.

The classifier needs to know which counterparties are the *borrower's own*
entities. Rather than hard-coding "HAWK", we learn the borrower's identifying
tokens from rows that carry an explicit, unambiguous marker (``INTERCOMPANY`` /
``OWN ACCT``), then reuse those tokens to catch related rows that lack the
marker (e.g. a bare ``HAWK HOLDINGS``). Optionally the caller can seed the
borrower name to make this robust on datasets with no explicit markers at all.
"""
from __future__ import annotations

import re

from .constants import (
    CORPORATE_SUFFIXES,
    INTERCOMPANY_STRONG,
    PERSON_NAME_PARTICLES,
    PERSONAL_STRONG,
    STOPWORDS,
)

_TOKEN_RE = re.compile(r"[^A-Z0-9]+")


def upper(text: str | None) -> str:
    return (text or "").upper().strip()


def tokens(text: str | None) -> list[str]:
    """Identifying tokens of a name: alphanumerics >= 3 chars, minus stopwords."""
    return [t for t in _TOKEN_RE.split(upper(text)) if len(t) >= 3 and t not in STOPWORDS]


def raw_tokens(text: str | None) -> list[str]:
    """All tokens, no stopword removal — for name/company shape detection."""
    return [t for t in _TOKEN_RE.split(upper(text)) if t]


def contains_any(haystack: str, needles) -> bool:
    up = upper(haystack)
    return any(n.upper() in up for n in needles)


def looks_like_company(name: str | None) -> bool:
    """A counterparty carrying a corporate legal-form / organisation token."""
    return any(t in CORPORATE_SUFFIXES for t in raw_tokens(name))


def looks_like_person_name(name: str | None) -> bool:
    """Heuristic: 2–4 alphabetic tokens, no corporate suffix, and at least one
    personal-name particle (e.g. AL / BIN / ABDUL). Requiring a particle keeps
    this precise — it won't misread two-word company names like "Omega Net"."""
    toks = [t for t in raw_tokens(name) if t.isalpha()]
    if not 2 <= len(toks) <= 4:
        return False
    if any(t in CORPORATE_SUFFIXES for t in toks):
        return False
    return any(t in PERSON_NAME_PARTICLES for t in toks)


class BorrowerProfile:
    """Tokens that identify the borrower's own / related entities and owner.

    ``related_tokens`` — brand tokens of group/sister/holding entities.
    ``owner_tokens``   — tokens of the owner's personal name.
    """

    def __init__(self, related_tokens: set[str], owner_tokens: set[str]):
        self.related_tokens = related_tokens
        self.owner_tokens = owner_tokens

    def as_dict(self) -> dict[str, list[str]]:
        return {
            "related_tokens": sorted(self.related_tokens),
            "owner_tokens": sorted(self.owner_tokens),
        }


def learn_borrower_profile(
    inflows: list[dict],
    borrower_name: str | None = None,
) -> BorrowerProfile:
    """Derive borrower tokens from explicitly-marked rows (+ optional seed name).

    A counterparty on an ``INTERCOMPANY`` row contributes its identifying tokens
    to ``related_tokens``; a counterparty on an ``OWN ACCT``/``PERSONAL`` row
    contributes to ``owner_tokens``. ``borrower_name``, when supplied, seeds the
    related tokens so the heuristic also works on data with no explicit markers.
    """
    related: set[str] = set(tokens(borrower_name))
    owner: set[str] = set()

    for row in inflows:
        text = f"{row['description']} {row['counterparty_raw']}"
        cp_tokens = tokens(row["counterparty_raw"])
        if contains_any(text, INTERCOMPANY_STRONG):
            related.update(cp_tokens)
        if contains_any(text, PERSONAL_STRONG):
            owner.update(cp_tokens)

    # Owner tokens that are also brand tokens (shouldn't happen, but be safe)
    owner -= related
    return BorrowerProfile(related_tokens=related, owner_tokens=owner)
