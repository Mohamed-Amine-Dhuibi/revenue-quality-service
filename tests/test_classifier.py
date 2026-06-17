"""Classifier: bucket assignment, token learning, and breakdown integrity."""
from app.core.normalize import learn_borrower_profile
from app.detection.classifier import (
    COMMERCIAL,
    INTERCOMPANY,
    PERSONAL,
    UNCLASSIFIED,
    classify_inflow,
    classify_inflows,
)

from .conftest import make_inflow


def _profile(rows):
    return learn_borrower_profile(rows)


def test_explicit_intercompany_marker():
    rows = [make_inflow(50000, "HAWK HOLDINGS",
                        "INTERCOMPANY TRF FROM HAWK HOLDINGS")]
    assert classify_inflow(rows[0], _profile(rows)) == INTERCOMPANY


def test_explicit_personal_marker():
    rows = [make_inflow(20000, "A AL HARBI PERSONAL",
                        "OWN ACCT TRF FROM A AL HARBI PERSONAL")]
    assert classify_inflow(rows[0], _profile(rows)) == PERSONAL


def test_commercial_inward_tt():
    rows = [make_inflow(9518.51, "ALMARAI IT SERVICES",
                        "INWARD TT - ALMARAI IT SERVICES")]
    assert classify_inflow(rows[0], _profile(rows)) == COMMERCIAL


def test_learned_brand_token_catches_unmarked_row():
    # One labelled intercompany row teaches the brand token "HAWK"; a later bare
    # "HAWK ..." inflow with no marker must still be caught as related-party.
    rows = [
        make_inflow(50000, "HAWK HLD GRP", "INTERCOMPANY TRF FROM HAWK HLD GRP"),
        make_inflow(40000, "HAWK TRADING", "INWARD TT - HAWK TRADING"),
    ]
    profile = learn_borrower_profile(rows)
    assert "HAWK" in profile.related_tokens
    assert classify_inflow(rows[1], profile) == INTERCOMPANY


def test_legit_customer_with_group_is_not_flagged():
    # "Group" alone must NOT trigger related-party (no shared brand token).
    rows = [make_inflow(12345.67, "BLUE HORIZON GROUP",
                        "INWARD TT - BLUE HORIZON GROUP")]
    assert classify_inflow(rows[0], _profile(rows)) == COMMERCIAL


def test_unclassified_when_no_rule_matches():
    rows = [make_inflow(500, "???", "MISC CREDIT")]
    assert classify_inflow(rows[0], _profile(rows)) == UNCLASSIFIED


def test_breakdown_totals_and_percentages_are_consistent(sample_rows):
    inflows = [r for r in sample_rows if r["is_inflow"]]
    _labels, breakdown = classify_inflows(inflows, learn_borrower_profile(inflows))

    cats = breakdown["categories"]
    summed = sum(cats[c]["total"] for c in cats)
    assert summed == breakdown["total_inflow"]
    assert sum(cats[c]["count"] for c in cats) == len(inflows)
    assert abs(sum(cats[c]["percentage"] for c in cats) - 100.0) < 0.5
    # On the real Hawk data, commercial is the plurality but well under 100%.
    assert cats[COMMERCIAL]["percentage"] > 60
    assert cats[INTERCOMPANY]["percentage"] > 10
