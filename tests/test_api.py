"""End-to-end API tests against the real sample file."""
from fastapi.testclient import TestClient

from app.main import app

# The default key when RQS_API_KEY is unset (see config.Settings).
VALID_KEY = "dev-local-key-change-me"
HEADERS = {"X-API-Key": VALID_KEY}

client = TestClient(app)


def _upload(sample_bytes, headers=HEADERS, **data):
    return client.post(
        "/analyse",
        files={"file": ("statement.csv", sample_bytes, "text/csv")},
        headers=headers,
        data=data,
    )


def test_health_is_public():
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


def test_analyse_requires_api_key(sample_bytes):
    r = _upload(sample_bytes, headers={})
    assert r.status_code == 401


def test_analyse_rejects_wrong_key(sample_bytes):
    r = _upload(sample_bytes, headers={"X-API-Key": "nope"})
    assert r.status_code == 401


def test_analyse_happy_path(sample_bytes):
    r = _upload(sample_bytes, borrower_name="Hawk Tech Services LLC")
    assert r.status_code == 200
    body = r.json()

    # All four mandated blocks present.
    assert set(body["inflow_breakdown"]["categories"]) == {
        "commercial_likely",
        "intercompany_or_related_party_likely",
        "personal_to_business_likely",
        "unclassified",
    }
    assert set(body["pattern_anomalies"]) == {
        "round_number_bias",
        "identical_amount_repeats",
        "end_of_month_spike",
        "suspected_intercompany_or_related_party_flows",
    }
    assert 0 <= body["revenue_quality_score"] <= 100
    assert body["recommendation"]["decision"] in {
        "trust_reported_revenue",
        "verify_with_vat_returns",
        "decline",
    }
    # Hawk Tech: strong manipulation signals -> verify band.
    assert body["recommendation"]["decision"] == "verify_with_vat_returns"
    # Report extras are populated.
    assert body["meta"]["inflow_transactions"] > 0
    assert body["report"]["monthly_inflow_series"]


def test_analyse_rejects_missing_columns():
    bad = b"date,amount\n2025-08-01,100\n"
    r = client.post(
        "/analyse",
        files={"file": ("bad.csv", bad, "text/csv")},
        headers=HEADERS,
    )
    assert r.status_code == 400
    assert "missing required column" in r.json()["detail"].lower()


def test_analyse_rejects_empty_file():
    r = client.post(
        "/analyse",
        files={"file": ("empty.csv", b"", "text/csv")},
        headers=HEADERS,
    )
    assert r.status_code == 400
