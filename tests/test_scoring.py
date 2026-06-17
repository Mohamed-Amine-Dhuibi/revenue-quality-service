"""Scoring + recommendation: severity curve, bounds, monotonicity, bands."""
import pytest

from app.core.normalize import learn_borrower_profile
from app.detection.anomalies import detect_all
from app.detection.classifier import classify_inflows
from app.detection.parser import parse_csv
from app.detection.pipeline import run_analysis
from app.detection.scoring import compute_score, recommend, severity

from .conftest import make_inflow


def _score_for(inflows):
    total = sum(r["amount"] for r in inflows)
    profile = learn_borrower_profile(inflows)
    labels, breakdown = classify_inflows(inflows, profile)
    anomalies = detect_all(inflows, labels, total)
    result = compute_score(breakdown, anomalies)
    return result, breakdown


# --- severity curve --------------------------------------------------------
def test_severity_bounds_and_linearity():
    assert severity(0.05, 0.05, 0.35) == 0.0      # at baseline
    assert severity(0.0, 0.05, 0.35) == 0.0       # below baseline
    assert severity(0.35, 0.05, 0.35) == 1.0      # at saturation
    assert severity(0.5, 0.05, 0.35) == 1.0       # above saturation
    assert severity(0.20, 0.05, 0.35) == pytest.approx(0.5)  # midpoint


# --- score behaviour -------------------------------------------------------
def test_clean_commercial_data_scores_high():
    inflows = [
        make_inflow(9518.51 + i * 137.4, f"CUSTOMER {i} LLC",
                    f"INWARD TT - CUSTOMER {i} LLC", day=(i % 25) + 1,
                    month=(i % 6) + 1)
        for i in range(20)
    ]
    result, _ = _score_for(inflows)
    assert result["score"] >= 70


def test_fabricated_data_scores_low():
    # All intercompany, all round, all repeated, all at month-end.
    inflows = [
        make_inflow(100000, "HAWK HOLDINGS", "INTERCOMPANY TRF FROM HAWK HOLDINGS",
                    day=30, month=(i % 6) + 1)
        for i in range(12)
    ]
    result, _ = _score_for(inflows)
    assert result["score"] < 40


def test_score_is_clamped_0_100():
    inflows = [
        make_inflow(100000, "HAWK HOLDINGS", "INTERCOMPANY TRF FROM HAWK HOLDINGS",
                    day=30)
        for _ in range(30)
    ]
    result, _ = _score_for(inflows)
    assert 0 <= result["score"] <= 100


def test_more_related_party_lowers_score():
    commercial = [make_inflow(9518.51 + i, f"CUST {i}", f"INWARD TT - CUST {i} LLC",
                              day=(i % 25) + 1) for i in range(10)]
    high, _ = _score_for(commercial)

    mixed = commercial + [
        make_inflow(50000, "HAWK HOLDINGS", "INTERCOMPANY TRF FROM HAWK HOLDINGS")
        for _ in range(10)
    ]
    low, _ = _score_for(mixed)
    assert low["score"] < high["score"]


# --- recommendation bands --------------------------------------------------
def test_recommendation_bands():
    dummy_breakdown = {
        "categories": {
            "commercial_likely": {"percentage": 90},
            "intercompany_or_related_party_likely": {"percentage": 5},
            "personal_to_business_likely": {"percentage": 5},
            "unclassified": {"percentage": 0},
        }
    }
    assert recommend(85, dummy_breakdown)["decision"] == "trust_reported_revenue"
    assert recommend(55, dummy_breakdown)["decision"] == "verify_with_vat_returns"
    assert recommend(20, dummy_breakdown)["decision"] == "decline"


# --- the real Hawk Tech case ----------------------------------------------
def test_hawk_sample_lands_in_verify_band(sample_bytes):
    rows, report = parse_csv(sample_bytes)
    result = run_analysis(rows, report)
    score = result["revenue_quality_score"]
    # Annualised cash roughly matches the reported SAR 9M, but the manipulation
    # signals are strong -> neither a clean trust nor an outright decline.
    assert 40 <= score < 70
    assert result["recommendation"]["decision"] == "verify_with_vat_returns"
