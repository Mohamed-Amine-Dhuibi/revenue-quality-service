"""Classifier: tiered bucket assignment, confidence, token learning, breakdown."""
from app.core.normalize import learn_borrower_profile
from app.detection.classifier import (
    COMMERCIAL,
    INTERCOMPANY,
    PERSONAL,
    UNCLASSIFIED,
    classify_inflow,
    classify_inflows,
    confidence_summary,
)

from .conftest import make_inflow


def _profile(rows):
    return learn_borrower_profile(rows)


# --- STRONG tier -----------------------------------------------------------
def test_explicit_intercompany_marker():
    rows = [make_inflow(50000, "HAWK HOLDINGS", "INTERCOMPANY TRF FROM HAWK HOLDINGS")]
    c = classify_inflow(rows[0], _profile(rows))
    assert c.label == INTERCOMPANY and c.confidence == "high"


def test_explicit_personal_marker():
    rows = [make_inflow(20000, "A AL HARBI PERSONAL",
                        "OWN ACCT TRF FROM A AL HARBI PERSONAL")]
    c = classify_inflow(rows[0], _profile(rows))
    assert c.label == PERSONAL and c.confidence == "high"


def test_commercial_inward_tt():
    rows = [make_inflow(9518.51, "ALMARAI IT SERVICES",
                        "INWARD TT - ALMARAI IT SERVICES")]
    assert classify_inflow(rows[0], _profile(rows)).label == COMMERCIAL


def test_learned_brand_token_catches_unmarked_row():
    rows = [
        make_inflow(50000, "HAWK HLD GRP", "INTERCOMPANY TRF FROM HAWK HLD GRP"),
        make_inflow(40000, "HAWK TRADING", "INWARD TT - HAWK TRADING"),
    ]
    profile = learn_borrower_profile(rows)
    assert "HAWK" in profile.related_tokens
    assert classify_inflow(rows[1], profile).label == INTERCOMPANY


def test_legit_customer_with_group_is_not_flagged():
    rows = [make_inflow(12345.67, "BLUE HORIZON GROUP",
                        "INWARD TT - BLUE HORIZON GROUP")]
    assert classify_inflow(rows[0], _profile(rows)).label == COMMERCIAL


# --- A big-brand name alone is NOT auto-trusted (anti-bias / anti-overfit) --
def test_brand_name_alone_is_not_auto_classified():
    # No payment marker, just a famous name in free text -> we must NOT lock it to
    # commercial. Trusting names would reward fabricating inflows under real brands.
    rows = [make_inflow(9000, "ALMARAI", "EFT CREDIT")]
    c = classify_inflow(rows[0], _profile(rows))
    assert not (c.label == COMMERCIAL and c.confidence == "high")
    # With a genuine payment marker it does classify as commercial.
    rows2 = [make_inflow(9000, "ALMARAI", "INWARD TT - ALMARAI")]
    assert classify_inflow(rows2[0], _profile(rows2)).label == COMMERCIAL


# --- New: generalized payment rails (not IT-specific) ----------------------
def test_generalized_payment_rails_are_commercial():
    for cp, desc in [
        ("SADAD COLLECTION", "SADAD PAYMENT RECEIVED"),
        ("POS MERCHANT", "POS SETTLEMENT BATCH"),
        ("OVERSEAS BUYER", "INWARD REMITTANCE"),
    ]:
        rows = [make_inflow(5000, cp, desc)]
        assert classify_inflow(rows[0], _profile(rows)).label == COMMERCIAL


# --- New: WEAK tier (person name, corporate form, group-suffix flag) --------
def test_person_name_pattern_is_personal_medium():
    rows = [make_inflow(6000, "ABDULLAH AL HARBI", "EFT CREDIT")]
    c = classify_inflow(rows[0], _profile(rows))
    assert c.label == PERSONAL and c.confidence == "medium"


def test_two_word_company_is_not_read_as_a_person():
    rows = [make_inflow(6000, "OMEGA NET", "EFT CREDIT")]
    assert classify_inflow(rows[0], _profile(rows)).label != PERSONAL


def test_corporate_form_name_is_commercial_medium():
    rows = [make_inflow(8000, "BRIGHT FUTURE TRADING LLC", "EFT CREDIT")]
    c = classify_inflow(rows[0], _profile(rows))
    assert c.label == COMMERCIAL and c.confidence == "medium"


def test_group_suffix_without_brand_token_is_flagged_low():
    rows = [make_inflow(7000, "PEAK ADVISORY GROUP", "EFT CREDIT")]
    c = classify_inflow(rows[0], _profile(rows))
    assert c.label == COMMERCIAL and c.confidence == "low"
    assert "verify" in c.reason.lower()


def test_unclassified_when_no_rule_matches():
    rows = [make_inflow(500, "XQZ", "MISC CREDIT")]
    assert classify_inflow(rows[0], _profile(rows)).label == UNCLASSIFIED


# --- Breakdown + confidence on the real sample -----------------------------
def test_breakdown_totals_and_percentages_are_consistent(sample_rows):
    inflows = [r for r in sample_rows if r["is_inflow"]]
    _cls, breakdown = classify_inflows(inflows, learn_borrower_profile(inflows))

    cats = breakdown["categories"]
    assert sum(cats[c]["total"] for c in cats) == breakdown["total_inflow"]
    assert sum(cats[c]["count"] for c in cats) == len(inflows)
    assert abs(sum(cats[c]["percentage"] for c in cats) - 100.0) < 0.5
    assert cats[COMMERCIAL]["percentage"] > 60
    assert cats[INTERCOMPANY]["percentage"] > 10


def test_sample_is_classified_at_high_confidence(sample_rows):
    inflows = [r for r in sample_rows if r["is_inflow"]]
    classifications, _ = classify_inflows(inflows, learn_borrower_profile(inflows))
    summary = confidence_summary(inflows, classifications)
    # Every Hawk inflow carries an explicit marker, so the breakdown is well-evidenced.
    assert summary["high"]["percentage"] > 95
