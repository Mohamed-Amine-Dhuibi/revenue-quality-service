# Revenue Quality Scoring Service

A FastAPI service that ingests a bank-statement CSV and judges how trustworthy a
borrower's **reported revenue** is. It classifies every inflow, detects
manipulation patterns, produces a **0–100 revenue quality score**, and returns a
lending **recommendation** — all from a single `POST /analyse` call.

Built for the *Soft Eng Take-Home — Revenue Quality Scoring (D)* case study
(borrower: **Hawk Tech Services LLC**, Riyadh; reported turnover SAR 9M; facility
requested SAR 400k).

---

## What it returns

`POST /analyse` (multipart CSV upload) responds with:

1. **`inflow_breakdown`** — total inflows split into `commercial_likely`,
   `intercompany_or_related_party_likely`, `personal_to_business_likely`,
   `unclassified`, each with SAR total, count and percentage.
2. **`pattern_anomalies`** — `round_number_bias`, `identical_amount_repeats`,
   `end_of_month_spike`, `suspected_intercompany_or_related_party_flows`, each
   with the evidence behind it.
3. **`revenue_quality_score`** — integer 0–100 (100 = trustworthy, 0 = fabricated).
4. **`recommendation`** — `trust_reported_revenue` / `verify_with_vat_returns` /
   `decline`, plus a one-sentence justification.

Plus rich context for building a report: parse stats, the analysed period,
annualised-inflow estimate, a transparent `score_breakdown`, and samples of the
exact transactions that triggered each flag.

---

## Project structure

```
revenue-quality-service/
├── app/
│   ├── config.py              # env-driven settings (RQS_* / .env)
│   ├── main.py                # FastAPI app factory
│   ├── schemas.py             # Pydantic response models
│   ├── api/
│   │   ├── routes.py          # POST /analyse, GET /health
│   │   └── security.py        # X-API-Key authentication
│   ├── core/
│   │   ├── constants.py       # every threshold & weight, named + commented
│   │   └── normalize.py       # text tokenisation + borrower-token learning
│   └── detection/
│       ├── parser.py          # tolerant CSV parsing & validation
│       ├── classifier.py      # inflow -> 4 buckets
│       ├── anomalies.py       # the 4 pattern detectors
│       ├── scoring.py         # score + recommendation
│       └── pipeline.py        # orchestrates the whole analysis
├── tests/                     # unit tests for detection + API tests
├── data/sample_hawk_tech.csv  # the case-study dataset
├── Dockerfile / docker-compose.yml
└── requirements.txt
```

Why this shape: the **detection engine is pure functions** with no web
dependencies, so the heuristics are unit-testable in isolation; the **api**
layer only handles HTTP, auth and serialisation. Every tunable lives in
`core/constants.py`.

---

## Quickstart

### Local (Python 3.11+)

```bash
cp .env.example .env            # then edit RQS_API_KEY
pip install -r requirements.txt
export RQS_API_KEY="my-secret"  # or rely on .env
uvicorn app.main:app --reload
```

### Docker

```bash
export RQS_API_KEY="my-secret"
docker compose up --build
```

### Call it

```bash
curl -s -X POST http://localhost:8000/analyse \
  -H "X-API-Key: my-secret" \
  -F "file=@data/sample_hawk_tech.csv" | python -m json.tool
```

`GET /health` is unauthenticated for liveness checks. Interactive docs live at
`/docs`.

---

## Tests

```bash
pytest
```

Tests cover the parser, the classifier, each anomaly detector, the scoring
function (clamping + monotonicity), and the authenticated endpoint end-to-end on
the real sample file.

---

## Defending the heuristics

> Detailed rationale, thresholds and external references are documented here.
> *(Filled in once the detection engine and research pass land — see commits.)*

---

## Security

- Every `/analyse` call requires a valid `X-API-Key`; the key is read from the
  environment and never committed (`.env` is git-ignored).
- Upload size is capped (`RQS_MAX_UPLOAD_BYTES`, default 10 MB).
- The container runs as a non-root user.
