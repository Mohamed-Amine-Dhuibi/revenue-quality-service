# Revenue Quality Dashboard (frontend)

A React + TypeScript + Vite single-page app that consumes the backend's
`POST /analyse` and renders the report as a credit-reviewer dashboard:

- **Score gauge** + **recommendation banner** (trust / verify / decline) with the
  one-line justification, and a **"why this score"** penalty breakdown.
- **Inflow breakdown** donut (commercial / intercompany / personal / unclassified)
  and **top counterparties** bar, coloured by classification.
- **Four anomaly cards** — round-number bias, identical-amount repeats,
  end-of-month spike, related-party flows — each with its share-vs-baseline bar
  and the actual evidence rows.
- **Monthly inflow** chart with month-end value highlighted.

Charts use [Recharts](https://recharts.org); the gauge is hand-drawn SVG.

## Run

```bash
npm install
npm run dev        # http://localhost:5173
```

The backend must be running (default `http://localhost:8000`) with this origin
allowed in CORS (it is, by default). In the UI, paste your `RQS_API_KEY`, point
the API base at the backend, upload a CSV and analyse.

- `VITE_API_BASE` (build-time env) overrides the default API base URL.
- The API key is entered in the UI and cached in `localStorage` for convenience.

## Build

```bash
npm run build      # type-checks (tsc -b) then bundles to dist/
npm run preview    # serve the production build
```

## Structure

```
src/
  api.ts                 fetch wrapper for POST /analyse
  types.ts               TypeScript mirror of the API response
  format.ts, theme.ts    formatters + colour semantics
  App.tsx                upload <-> dashboard state machine
  components/
    UploadForm, Dashboard,
    ScoreGauge, Recommendation, StatCards,
    InflowDonut, ScorePenalties, AnomaliesGrid,
    MonthlyInflowChart, CounterpartiesChart
```
