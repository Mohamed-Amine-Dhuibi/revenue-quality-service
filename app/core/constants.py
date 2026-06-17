"""All detection thresholds and weights in one place.

Every magic number a reviewer might probe lives here, named and commented, so the
heuristics can be audited and tuned without hunting through logic. The README's
"Defending the heuristics" section references these by name.
"""

# ---------------------------------------------------------------------------
# Text normalisation
# ---------------------------------------------------------------------------
# Tokens that carry no entity-identity signal. Stripped before we learn a
# borrower's "brand" / "owner" tokens, so that e.g. "HAWK HLD GRP" reduces to
# the identifying token {HAWK} rather than the generic {HLD, GRP}.
STOPWORDS: frozenset[str] = frozenset(
    {
        "THE", "AND", "FOR", "FROM", "PMT", "PAYMENT", "TRF", "TRANSFER",
        "INWARD", "OUTWARD", "OWN", "ACCT", "ACCOUNT", "PERSONAL",
        "INTERCOMPANY", "INTER", "COMPANY", "CO", "LLC", "LTD", "EST",
        "ESTABLISHMENT", "TRADING", "TECH", "TECHNOLOGY", "TECHNOLOGIES",
        "SERVICE", "SERVICES", "SOLUTION", "SOLUTIONS", "GROUP", "GRP",
        "HOLDING", "HOLDINGS", "HLD", "BRANCH", "FZ", "FZE", "FZCO", "DEPT",
        "DEPARTMENT", "IT", "GENERAL", "ENTERPRISE", "ENTERPRISES", "PARTNERS",
        "CONSULTANCY", "ADVISORY", "NET", "SUPPLIER", "VENDOR", "BANK",
    }
)

# Explicit, unambiguous markers found in the transaction text itself.
INTERCOMPANY_MARKERS: tuple[str, ...] = (
    "INTERCOMPANY", "INTER COMPANY", "INTERCO", "INTRAGROUP", "INTRA GROUP",
)
RELATED_PARTY_KEYWORDS: tuple[str, ...] = (
    "HOLDING", "HOLDINGS", "HLD", "GROUP", " GRP", "SUBSIDIARY", "AFFILIATE",
    "PARENT", "BRANCH", " FZ", "FZE", "FZCO", "SISTER",
)
PERSONAL_MARKERS: tuple[str, ...] = (
    "OWN ACCT", "OWN ACCOUNT", "PERSONAL", "SELF", "PROPRIETOR", "OWNER",
)
# A genuine third-party commercial inflow usually looks like an inbound wire.
COMMERCIAL_MARKERS: tuple[str, ...] = (
    "INWARD TT", "INWARD TELEGRAPHIC", "INCOMING WIRE", "POS ", "INVOICE",
    "INV ", "CUSTOMER", "SALES", "INWARD CHEQUE", "INWARD CHQ",
)

# ---------------------------------------------------------------------------
# Anomaly detection thresholds
# ---------------------------------------------------------------------------
# Round-number bias: an inflow whose amount is an exact multiple of this is
# "round". Real invoices (tax, fees, fractional rates) almost never are.
ROUND_NUMBER_DIVISOR: int = 1000
ROUND_NUMBER_MIN_AMOUNT: float = 1000.0  # ignore trivially small round values

# Identical-amount repeats: an exact amount seen at least this many times among
# inflows is a "repeat cluster" (scripted / recycled cash, not organic sales).
IDENTICAL_REPEAT_MIN_COUNT: int = 3

# End-of-month spike: how many trailing calendar days count as "month end".
MONTH_END_WINDOW_DAYS: int = 3

# ---------------------------------------------------------------------------
# Scoring — penalty weights (max points each component can subtract from 100)
# ---------------------------------------------------------------------------
# Rationale and citations are in README "Defending the heuristics".
W_RELATED_PARTY: float = 35.0   # share of inflow value that is intercompany/owner
W_ROUND: float = 18.0           # round-number bias
W_REPEAT: float = 12.0          # identical-amount repeat clusters
W_MONTH_END: float = 20.0       # period-end stuffing
W_UNCLASSIFIED: float = 10.0    # inflows we could not explain at all
# Total possible penalty = 95, so even a worst-case statement floors at 5, not 0;
# a literal 0 is reserved for input that is *entirely* non-commercial.

# Each component maps a "share" onto a 0..1 severity via a baseline (below which
# the behaviour is normal / expected by chance) and a saturation point (at or
# above which it is treated as maximally suspicious).
ROUND_BASELINE_SHARE: float = 0.05
ROUND_SATURATION_SHARE: float = 0.35
REPEAT_BASELINE_SHARE: float = 0.05
REPEAT_SATURATION_SHARE: float = 0.35
# 3 trailing days out of ~30 is ~10% of value by chance; below 15% is normal.
MONTH_END_BASELINE_SHARE: float = 0.15
MONTH_END_SATURATION_SHARE: float = 0.40

# ---------------------------------------------------------------------------
# Recommendation bands
# ---------------------------------------------------------------------------
TRUST_THRESHOLD: int = 70    # score >= 70  -> trust_reported_revenue
DECLINE_THRESHOLD: int = 40  # score <  40  -> decline
# 40..69 -> verify_with_vat_returns
