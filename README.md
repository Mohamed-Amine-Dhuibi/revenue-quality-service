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
│   └── fixtures/sample_hawk_tech.csv   # case-study dataset (test fixture only)
├── frontend/                  # React + TS dashboard (consumes POST /analyse)
├── Dockerfile / docker-compose.yml
└── requirements.txt
```

The sample CSV lives under `tests/fixtures/` (it is test data, not something the
service ships) — upload your own statement via the dashboard or the API.

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

### Docker (full stack — API + dashboard)

One command builds and runs **both** the API and the React dashboard:

```bash
export RQS_API_KEY="my-secret"
docker compose up --build
# dashboard -> http://localhost:5173   API -> http://localhost:8000
```

### Call it

```bash
curl -s -X POST http://localhost:8000/analyse \
  -H "X-API-Key: my-secret" \
  -F "file=@tests/fixtures/sample_hawk_tech.csv" | python -m json.tool
```

`GET /health` is unauthenticated for liveness checks. Interactive docs live at
`/docs` — note the API key goes in the **Authorize** button (top-right), since
`X-API-Key` is a header security scheme (Swagger doesn't render it inline).

---

## Dashboard (frontend)

A React + TypeScript dashboard in [`frontend/`](frontend/) turns the JSON report
into a credit-reviewer view: score gauge, recommendation banner, "why this
score" penalty bars, inflow-breakdown donut, top counterparties, four anomaly
cards with evidence, and a monthly inflow chart with month-end value
highlighted.

```bash
cd frontend && npm install && npm run dev   # http://localhost:5173
```

The backend enables CORS for the Vite dev origin by default. Enter your
`RQS_API_KEY` in the UI, upload a CSV, and analyse. See
[`frontend/README.md`](frontend/README.md) for details.

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

Detection logic is the core of this service, so each rule below states **what it
does, the threshold it uses, why that threshold, and the standard it rests on.**
Every threshold is a named constant in
[`app/core/constants.py`](app/core/constants.py).

Guiding principle from the forensic-accounting literature: these patterns are
**red flags that warrant scrutiny, not proof of fabrication.** That is exactly
why the middle verdict is *verify*, not *decline* — the service quantifies
suspicion, it does not convict.

### 1. Inflow classification — the dominant signal

The biggest driver of revenue quality is **how much inflow is genuine
third-party revenue** vs the company's own money recycled to look like sales.

- **Related-party / intercompany inflows are a recognised revenue-inflation red
  flag.** ISA 550 requires auditors to scrutinise significant related-party
  transactions outside the normal course of business; IFRS 10 / ASC 810 require
  intra-group transactions to be **eliminated in full** on consolidation
  *precisely because, left in, they artificially inflate group revenue.* Lenders
  discount them for the same reason. (ISA 550 is an auditing, not lending,
  standard — the lender-discount step is a defensible inference.)
- We classify **conservatively**: related-party is flagged only on an explicit
  `INTERCOMPANY` / `OWN ACCT` marker, or a counterparty that **shares a learned
  brand/owner token** with the borrower's own labelled transfers — never on
  generic words like "Group"/"Holding" alone (legitimate customers carry those).
  This is what stops the service mislabelling "Peak Advisory **Group**" as
  intercompany.
- **Legitimacy comes from markers, never from the counterparty's name.** We
  deliberately keep *no* "known big corporate" allow-list: a name in a bank
  narration is unverified free text, so auto-trusting big brands would overfit to
  a given sample and reward the cheapest fabrication trick — naming fake inflows
  after real companies (e.g. an `STC IT SUPPLIER` line proves nothing on its own).
- **Two confidence tiers (precision by construction).** Signals are split into
  **STRONG** (explicit markers + learned brand/owner tokens → classify directly)
  and **WEAK** (honorific + person-name shape, corporate-form names, generic
  revenue words → only fire when nothing stronger matched). A WEAK signal can
  never override a STRONG one, so widening the lexicon raises recall on unseen
  statements without costing precision. Each
  inflow carries a `high`/`medium`/`low` confidence, surfaced as
  `meta.classification_confidence` and a `report.review_queue` of the
  non-high-confidence rows. The lexicons are **sector-agnostic** (bank wires,
  cards/POS, SADAD/SARIE, cheques, collections, invoices, contracts), not
  IT-specific. On the Hawk data every inflow is high-confidence, so the
  breakdown is fully evidenced.

### 2. Round-number bias

- **Rule:** an inflow that is an exact multiple of `ROUND_NUMBER_DIVISOR`
  (1,000) and at least `ROUND_NUMBER_MIN_AMOUNT` (1,000) is "round".
- **Why:** round numbers are codified as a characteristic of *inappropriate
  journal entries* in **AU-C 240.A49 / PCAOB AS 2401**. Best practice is a
  **"large AND round" filter** — roundness alone is noisy, so it is paired with a
  materiality floor, which is why we require both an exact ×1,000 multiple *and*
  a minimum amount. A genuine 2-decimal invoice (tax, fractional rates, fees) has
  only ≈0.1% chance of being an exact ×1,000 multiple.
- **Honest caveat:** the "×1,000" definition is an operationalisation, not
  standard text, and round numbers are a flag, not proof — so this factor is
  capped (`W_ROUND` = 18) and measured as *share of value*, never a single hit.

### 3. A note on Benford's Law — the right tool for this data size

The brief didn't ask for it, but the obvious statistical question is *"why not
Benford's Law?"* — so here's the reasoning. Benford's Law is the textbook
digit-distribution test (leading digit 1 ≈ 30.1%, digit 9 < 5%; chi-square
critical values 15.507 first-digit / 112.022 first-two-digit at the 5% level).
It's powerful on large ledgers — but the forensic literature (Nigrini) is
explicit that digit-distribution testing is **unreliable below ~5,000 records.**
This statement has **202 inflows**, two orders of magnitude too few, so a Benford
test would mostly emit false positives here. Exact round-number screening
(section 2) captures the same "manufactured figures" intuition and stays valid at
any sample size — so it's the better fit for bank-statement data. (For the same
reason we don't lean on Mean-Absolute-Deviation conformity bands: the
commonly-quoted MAD cutoffs didn't hold up under review.)

### 4. Identical-amount repeats

- **Rule:** an exact amount recurring ≥ `IDENTICAL_REPEAT_MIN_COUNT` (3) times
  among inflows is a repeat cluster.
- **Why:** independent customers paying real invoices rarely land on the
  identical figure repeatedly; tight clusters of one amount are the classic
  duplicate signal used in **continuous-auditing duplicate detection** and
  **round-tripping / circular-flow** analysis.
- **Honest caveat:** unlike Benford or the audit standards, there is **no single
  canonical numeric threshold** in the literature for "how many repeats =
  synthetic revenue" (our research confirmed this gap). ≥3 is a defensible
  internal default; the factor is weighted modestly (`W_REPEAT` = 12) and only
  ever corroborates the other signals.

### 5. End-of-month spike (period-end window dressing)

- **Rule:** share of inflow *value* landing in the last `MONTH_END_WINDOW_DAYS`
  (3) days of each month — normal below ~15%, penalty ramps to a maximum at 40%.
- **Why:** **period-end "stuffing" / window dressing** — accelerating recognition
  to hit a monthly target — is a recognised manipulation whose signature is value
  concentrated at period end (Das & Shroff, *Detection of Channel Stuffing*).
  Three trailing days are ~10% of a month by chance, so a value share several
  times that is the tell. `W_MONTH_END` = 20.

### 6. Score and recommendation bands

Transparent additive model (start at 100, subtract weighted penalties — see
[`scoring.py`](app/detection/scoring.py)). Weights encode priors: related-party
value is the single heaviest factor (`W_RELATED_PARTY` = 35) because it most
directly contradicts "this is external revenue". Bands: **≥ 70 → trust**,
**40–69 → verify_with_vat_returns**, **< 40 → decline**.

### 7. Why "verify with VAT returns" — and the Saudi angle

- **VAT-to-turnover reconciliation** is the standard independent check that
  recorded sales actually appear on filed returns at the correct rates — the
  canonical revenue cross-check.
- In **Saudi Arabia / GCC this is unusually decisive**: **ZATCA Phase 2
  e-invoicing** is rolling out in waves by revenue, descending to SMEs
  (~SAR 1M turnover by end-2025), with near-real-time invoice clearance on the
  Fatoora platform. For a Riyadh SME like Hawk Tech, VAT / e-invoice records are
  a near-real-time, government-held ground truth — so "verify against VAT
  returns" is both cheap and conclusive, making it the right call when the score
  lands mid-band (Hawk: **51**).

### References

- Journal of Accountancy — *Fraud and round numbers* (2018): AU-C 240.A49 /
  PCAOB AS 2401 round-number red flag, "large AND round" screening.
- Nigrini, *Forensic Analytics* (2nd ed.) & Journal of Accountancy (Sep 2022):
  Benford thresholds, runs test, ~5,000-record minimum.
- NIH/PMC `PMC8720889`: Benford digit-distribution conformity testing.
- IAASB **ISA 550** (Related Parties); **IFRS 10 / ASC 810** consolidation
  (intra-group elimination).
- Das & Shroff, *Detection of Channel Stuffing* (Notre Dame): period-end
  window-dressing signature.
- Ocrolus *Bank Statement Income Calculator* docs: example of a fintech
  large-deposit threshold (vendor default, ≥50% above average).
- RossMartin — *Reconcile your VAT to your turnover*; Wafeq / EY / Deloitte —
  ZATCA Phase 2 e-invoicing waves & timeline.

> Sourcing notes: the Benford cutoffs and audit-standard red flags are primary /
> peer-reviewed; the Ocrolus default and ZATCA operational details come from
> vendor docs corroborated by Big-Four alerts; specific MAD conformity bands were
> adversarially refuted during research and are intentionally not cited.

---

## Security

- Every `/analyse` call requires a valid `X-API-Key`; the key is read from the
  environment and never committed (`.env` is git-ignored).
- Upload size is capped (`RQS_MAX_UPLOAD_BYTES`, default 10 MB).
- The container runs as a non-root user.
