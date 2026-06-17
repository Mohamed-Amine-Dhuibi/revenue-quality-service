"""Parser: structural validation, tolerance, and inflow detection."""
import pytest

from app.detection.parser import CsvValidationError, parse_csv

HEADER = "date,description,amount,balance_after,counterparty_raw,type\n"


def test_parses_sample(sample_parsed):
    rows, report = sample_parsed
    assert report["rows_parsed"] == len(rows)
    assert report["rows_parsed"] > 1000
    # Every row carries the derived inflow flag.
    assert all("is_inflow" in r for r in rows)


def test_inflow_flag_follows_sign():
    csv = HEADER + (
        "2025-08-01,INWARD TT - ACME,9518.51,1000,ACME,credit\n"
        "2025-08-01,FUEL,-3791.30,900,ALDREES,debit\n"
    )
    rows, _ = parse_csv(csv.encode())
    assert rows[0]["is_inflow"] is True
    assert rows[1]["is_inflow"] is False


def test_missing_column_raises():
    bad = "date,description,amount\n2025-08-01,x,1\n"
    with pytest.raises(CsvValidationError):
        parse_csv(bad.encode())


def test_empty_raises():
    with pytest.raises(CsvValidationError):
        parse_csv(b"")


def test_skips_bad_rows_without_failing():
    csv = HEADER + (
        "2025-08-01,good,100,500,ACME,credit\n"
        "not-a-date,bad,xyz,,?,debit\n"
        "2025-08-02,good2,200,700,ACME,credit\n"
    )
    rows, report = parse_csv(csv.encode())
    assert report["rows_parsed"] == 2
    assert report["rows_skipped"] == 1


def test_tolerates_thousands_separator_and_bom():
    csv = "﻿" + HEADER + '2025-08-01,big,"1,234,567.89",0,ACME,credit\n'
    rows, _ = parse_csv(csv.encode())
    assert rows[0]["amount"] == pytest.approx(1234567.89)
