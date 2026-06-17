"""Anomaly detectors: each pattern in isolation, plus the real sample."""
from app.core.normalize import learn_borrower_profile
from app.detection.anomalies import (
    end_of_month_spike,
    identical_amount_repeats,
    round_number_bias,
    suspected_related_party_flows,
)
from app.detection.classifier import classify_inflows

from .conftest import make_inflow


def test_round_number_bias_flags_round_amounts():
    inflows = [make_inflow(50000), make_inflow(100000), make_inflow(9518.51)]
    total = sum(r["amount"] for r in inflows)
    res = round_number_bias(inflows, total)
    assert res["detected"] is True
    assert res["count"] == 2
    assert 0 < res["value_share"] < 1


def test_round_number_ignores_messy_amounts():
    inflows = [make_inflow(9518.51), make_inflow(2837.09)]
    res = round_number_bias(inflows, sum(r["amount"] for r in inflows))
    assert res["detected"] is False
    assert res["count"] == 0


def test_identical_amount_repeats_needs_three():
    twice = [make_inflow(75000), make_inflow(75000)]
    assert identical_amount_repeats(twice, 150000)["detected"] is False

    thrice = twice + [make_inflow(75000)]
    res = identical_amount_repeats(thrice, 225000)
    assert res["detected"] is True
    assert res["repeated_clusters"] == 1
    assert res["evidence"][0]["count"] == 3


def test_end_of_month_spike_detects_concentration():
    # Three big inflows on the 30th, one small mid-month.
    inflows = [
        make_inflow(100000, day=30, month=1),
        make_inflow(100000, day=31, month=1),
        make_inflow(100000, day=29, month=1),
        make_inflow(1000, day=10, month=1),
    ]
    res = end_of_month_spike(inflows, sum(r["amount"] for r in inflows))
    assert res["detected"] is True
    assert res["value_share"] > 0.9
    assert res["by_month"][0]["month"] == "2025-01"


def test_no_month_end_spike_for_even_spread():
    inflows = [make_inflow(1000, day=d, month=1) for d in (3, 10, 17, 24)]
    res = end_of_month_spike(inflows, sum(r["amount"] for r in inflows))
    assert res["detected"] is False


def test_related_party_flow_aggregation():
    inflows = [
        make_inflow(50000, "HAWK HOLDINGS", "INTERCOMPANY TRF FROM HAWK HOLDINGS"),
        make_inflow(20000, "A AL HARBI", "OWN ACCT TRF FROM A AL HARBI"),
        make_inflow(9518.51, "ALMARAI", "INWARD TT - ALMARAI"),
    ]
    labels, _ = classify_inflows(inflows, learn_borrower_profile(inflows))
    res = suspected_related_party_flows(inflows, labels, sum(r["amount"] for r in inflows))
    assert res["detected"] is True
    assert res["count"] == 2
    assert res["flagged_value"] == 70000.0


def test_all_four_patterns_fire_on_sample(sample_rows):
    inflows = [r for r in sample_rows if r["is_inflow"]]
    total = sum(r["amount"] for r in inflows)
    labels, _ = classify_inflows(inflows, learn_borrower_profile(inflows))

    assert round_number_bias(inflows, total)["detected"]
    assert identical_amount_repeats(inflows, total)["detected"]
    assert end_of_month_spike(inflows, total)["detected"]
    assert suspected_related_party_flows(inflows, labels, total)["detected"]
