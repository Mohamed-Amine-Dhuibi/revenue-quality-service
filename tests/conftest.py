"""Shared fixtures: the real sample dataset and small synthetic builders."""
from __future__ import annotations

import calendar
from datetime import date
from pathlib import Path

import pytest

from app.detection.parser import parse_csv

SAMPLE_CSV = Path(__file__).resolve().parent.parent / "data" / "sample_hawk_tech.csv"


@pytest.fixture(scope="session")
def sample_bytes() -> bytes:
    return SAMPLE_CSV.read_bytes()


@pytest.fixture()
def sample_rows(sample_bytes):
    rows, _report = parse_csv(sample_bytes)
    return rows


@pytest.fixture()
def sample_parsed(sample_bytes):
    return parse_csv(sample_bytes)


def make_inflow(amount: float, counterparty: str = "ACME LLC",
                description: str = "INWARD TT - ACME LLC", day: int = 15,
                month: int = 1, year: int = 2025) -> dict:
    """Build a single normalised inflow row for unit tests."""
    day = min(day, calendar.monthrange(year, month)[1])  # clamp to valid day
    return {
        "date": date(year, month, day),
        "description": description,
        "amount": amount,
        "balance_after": None,
        "counterparty_raw": counterparty,
        "type": "credit",
        "is_inflow": True,
    }
