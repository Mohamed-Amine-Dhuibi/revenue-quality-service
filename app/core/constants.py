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

# Signals are organised in two confidence tiers (see classifier.py):
#   STRONG = explicit and unambiguous -> classify directly (high confidence).
#   WEAK   = affiliation / contextual -> only act when corroborated (shared brand
#            token, person-name shape) or to resolve an otherwise-unclassified row.
# Adding to a STRONG tuple is pure recall with no precision cost; WEAK signals can
# never misfire on their own. The lexicons are sector-agnostic on purpose.

# ── STRONG: intercompany / intra-group transfers ───────────────────────────
INTERCOMPANY_STRONG: tuple[str, ...] = (
    "INTERCOMPANY", "INTER COMPANY", "INTER-CO", "INTERCO", "INTRAGROUP",
    "INTRA GROUP", "INTRA-GROUP", "IC TRF", "I/C TRF", "INTERBRANCH",
    "INTER BRANCH", "INTER-BRANCH", "HEAD OFFICE", "H/O TRF", "HO TRANSFER",
    "GROUP TRANSFER", "GRP TRF", "SHAREHOLDER LOAN", "DIRECTOR LOAN",
    "CAPITAL INJECTION", "EQUITY INJECTION", "RELATED PARTY", "RELATED-PARTY",
    "TRANSFER PRICING", "COST RECHARGE", "INTERCO SETTLEMENT", "DUE FROM GROUP",
)
# ── STRONG: owner / personal funding ───────────────────────────────────────
PERSONAL_STRONG: tuple[str, ...] = (
    "OWN ACCT", "OWN ACCOUNT", "OWN A/C", "SELF TRF", "SELF TRANSFER",
    "FROM SELF", "PERSONAL ACCOUNT", "PERSONAL SAVINGS", "PERSONAL TRANSFER",
    "CAPITAL CONTRIBUTION", "PARTNER CONTRIBUTION", "SHAREHOLDER CONTRIBUTION",
    "OWNER FUNDING", "PROPRIETOR",
)
# ── STRONG: genuine third-party commercial inflows (payment rails, sector-
#    agnostic: wires, cards/POS, e-commerce, cheques, collections, invoices) ──
COMMERCIAL_STRONG: tuple[str, ...] = (
    # bank wires / transfers
    "INWARD TT", "INWARD TELEGRAPHIC", "INCOMING WIRE", "INWARD REMIT",
    "INWARD REMITTANCE", "RTGS", "SARIE", "ACH CREDIT", "GIRO", "SWIFT CREDIT",
    # cards / POS / e-commerce settlement
    "POS SETTLEMENT", "POS DEP", "MERCHANT SETTLEMENT", "CARD SETTLEMENT",
    "ACQUIRER", "MADA", "SADAD", "E-COMMERCE", "ECOM ", "PAYMENT GATEWAY",
    "PAYTABS", "MOYASAR", "HYPERPAY", "TAP PAYMENTS", "STC PAY", "URPAY",
    "VISA SETTLEMENT", "MASTERCARD SETTLEMENT",
    # cheques / collections / invoices / contracts
    "INWARD CHEQUE", "INWARD CHQ", "CHEQUE DEPOSIT", "CHQ DEP", "INVOICE",
    "INV NO", "CUSTOMER PAYMENT", "CONTRACT PAYMENT", "PROGRESS PAYMENT",
    "MILESTONE PAYMENT", "PURCHASE ORDER", "RENTAL INCOME", "RENT RECEIVED",
)

# ── WEAK: affiliation suffixes (legal forms / group words). Never classify on
#    their own — used only to corroborate a shared brand token or to flag a
#    commercial row as "verify, could be related-party". ──
RELATED_PARTY_WEAK: tuple[str, ...] = (
    "HOLDING", "HOLDINGS", "HLD", "GROUP", " GRP", "SUBSIDIARY", "AFFILIATE",
    "PARENT", "SISTER", "FAMILY OFFICE", "INVESTMENT", "INVESTMENTS",
    "VENTURES", "BRANCH",
)
# ── WEAK: honorific titles preceding a person name (corroborate w/ name shape) ──
PERSONAL_WEAK_TITLES: tuple[str, ...] = (
    "MR ", "MRS ", "MS ", "MISS ", "DR ", "ENG ", "SHEIKH ", "SH ", "PROF ",
)
# ── WEAK: generic revenue words (only when nothing stronger matched) ──
COMMERCIAL_WEAK: tuple[str, ...] = (
    "COLLECTION", "SETTLEMENT", "PAYMENT RECEIVED", "RECEIPT", "SALES",
    "REMITTANCE", "SUBSCRIPTION", "RETAINER", "DEPOSIT FROM",
)

# Corporate legal-form / organisation tokens. Presence => the counterparty is an
# organisation, not a person (drives the person-name vs company detectors).
CORPORATE_SUFFIXES: frozenset[str] = frozenset(
    {
        "LLC", "LTD", "CO", "COMPANY", "INC", "CORP", "CORPORATION", "PLC",
        "WLL", "SPC", "PJSC", "PSC", "SAL", "SARL", "GMBH", "PTE", "SDN", "BHD",
        "EST", "ESTABLISHMENT", "TRADING", "ENTERPRISE", "ENTERPRISES",
        "INDUSTRIES", "INDUSTRIAL", "FACTORY", "GROUP", "HOLDING", "HOLDINGS",
        "HLD", "GRP", "FZE", "FZCO", "FZ", "DMCC", "JLT", "SERVICES",
        "SOLUTIONS", "TECHNOLOGIES", "CONTRACTING", "CONSULTING", "CONSULTANCY",
        "AGENCY", "STORES", "MARKET", "FOODS", "LOGISTICS", "PARTNERS",
    }
)
# Person-name particles (incl. common Arabic) that mark a string as a human name.
PERSON_NAME_PARTICLES: frozenset[str] = frozenset(
    {"AL", "BIN", "BINT", "ABU", "ABD", "ABDUL", "ABDULLAH", "BANI", "UMM", "IBN"}
)
# NOTE: we deliberately do NOT keep a "known big corporate" allow-list. A
# counterparty name in a bank narration is unverified free text, so auto-trusting
# big-brand names would (a) overfit to whatever names appear in a given sample and
# (b) reward the cheapest fabrication technique — naming fake inflows after real
# companies. Legitimacy must come from the transaction's own markers, not its name.

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
