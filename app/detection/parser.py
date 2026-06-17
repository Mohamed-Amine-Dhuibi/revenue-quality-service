"""CSV parsing and validation.

Turns the raw uploaded bytes into a list of clean transaction dicts plus a
parse report (how many rows were read / skipped and why). Defensive on purpose:
real bank exports have stray whitespace, BOMs, blank lines, and the odd
malformed row, and a lender-facing service must degrade gracefully rather than
500 on a single bad line.
"""
from __future__ import annotations

import csv
import io
from datetime import date, datetime

REQUIRED_COLUMNS = {
    "date",
    "description",
    "amount",
    "balance_after",
    "counterparty_raw",
    "type",
}


class CsvValidationError(ValueError):
    """Raised when the CSV is structurally unusable (missing columns / no rows)."""


def _parse_date(raw: str) -> date:
    raw = (raw or "").strip()
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%Y/%m/%d", "%d-%m-%Y"):
        try:
            return datetime.strptime(raw, fmt).date()
        except ValueError:
            continue
    raise ValueError(f"unrecognised date: {raw!r}")


def _parse_amount(raw: str) -> float:
    # Tolerate thousands separators and surrounding spaces; reject blanks.
    cleaned = (raw or "").replace(",", "").replace("SAR", "").strip()
    if cleaned == "":
        raise ValueError("empty amount")
    return float(cleaned)


def parse_csv(raw_bytes: bytes) -> tuple[list[dict], dict]:
    """Parse uploaded CSV bytes into normalised rows + a parse report.

    Returns ``(rows, report)``. Each row dict has keys: ``date`` (date),
    ``description`` (str), ``amount`` (float, signed), ``balance_after``
    (float | None), ``counterparty_raw`` (str), ``type`` (str), ``is_inflow``
    (bool). ``report`` has ``rows_total``, ``rows_parsed``, ``rows_skipped``,
    ``skipped_examples``.
    """
    text = raw_bytes.decode("utf-8-sig", errors="replace")
    reader = csv.DictReader(io.StringIO(text))

    if reader.fieldnames is None:
        raise CsvValidationError("CSV appears to be empty.")
    header = {h.strip().lower() for h in reader.fieldnames}
    missing = REQUIRED_COLUMNS - header
    if missing:
        raise CsvValidationError(
            f"CSV missing required column(s): {', '.join(sorted(missing))}."
        )

    rows: list[dict] = []
    skipped: list[dict] = []
    total = 0
    for raw in reader:
        total += 1
        # Normalise keys to lower-case so header casing doesn't matter.
        r = {(k or "").strip().lower(): v for k, v in raw.items()}
        try:
            amount = _parse_amount(r.get("amount", ""))
            txn_type = (r.get("type") or "").strip().lower()
            try:
                balance = _parse_amount(r.get("balance_after", ""))
            except ValueError:
                balance = None
            rows.append(
                {
                    "date": _parse_date(r.get("date", "")),
                    "description": (r.get("description") or "").strip(),
                    "amount": amount,
                    "balance_after": balance,
                    "counterparty_raw": (r.get("counterparty_raw") or "").strip(),
                    "type": txn_type,
                    # Trust the sign of the amount, fall back to the type label.
                    "is_inflow": amount > 0 or (amount == 0 and txn_type == "credit"),
                }
            )
        except ValueError as exc:
            if len(skipped) < 10:
                skipped.append({"row_number": total + 1, "reason": str(exc)})

    if not rows:
        raise CsvValidationError("CSV contained no parseable transaction rows.")

    report = {
        "rows_total": total,
        "rows_parsed": len(rows),
        "rows_skipped": len(skipped),
        "skipped_examples": skipped,
    }
    return rows, report
