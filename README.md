# UK wind forecast evaluation (day-ahead, January 2026)

A web app for a power-purchasing desk: see the latest Elexon wind forecast that was available at the day-ahead
decision time, and measure how accurate it was against actual generation.

**Live app:** `<add Vercel/Heroku URL here>`

> **AI disclosure:** this project was built with the help of an AI assistant (Anthropic Claude), which produced the first
> draft of the code, tests and documentation. The author is responsible for reviewing and verifying it.

## Core idea
For a delivery day **D**, the trader decides on **D-1** before the day-ahead gate closes. For every half-hour on D the app
picks the **latest WINDFOR forecast with `publishTime` <= cutoff on D-1** (default 09:00 UTC), joins it to FUELHH `WIND`
actuals on `startTime`, and computes `error = actual - forecast`. Forecasts published later are never used.

**Cutoff assumption.** The GB day-ahead auctions (e.g. EPEX, N2EX) close in the morning of D-1 (around 09:50 UK time; please
verify with the exchange). 09:00 UTC is therefore the default, with 08:00-17:00 selectable. In January UK time equals UTC.
The 11:00/12:00/17:00 options are for what-if comparison, not real gate closures.

## Metrics
MAE and RMSE (MW), P90 absolute error, bias % = (forecast - actual) / actual (positive = over-forecast), NRMSE.
**Imbalance risk score** (0-100) is an illustrative heuristic (NRMSE of 50% maps to 100); **£ exposure** = sum |error| MWh x
a user-entered price. Neither is a market-standard figure.

## Files
```
backend/            FastAPI service (Python)
  main.py             API routes + validation
  elexon_service.py   fetch, clean, cutoff alignment, metrics, synthetic fallback
  scripts/fetch_data.py   download real Elexon data into backend/data/*.csv
  tests/              pytest unit + API tests
  data/               CSV cache (commit real data here for deployment)
frontend/           React + Vite + Tailwind + Recharts
  src/App.jsx         page, filters, state
  src/components/     KPICards, ForecastChart, ErrorMetricsChart, DataTable
api/index.py        Vercel serverless entrypoint
vercel.json         Vercel config
docker-compose.yml  local run (backend :8000, frontend :8080)
generate_zip.py     packages the repo into a zip
VIDEO_SCRIPT.md     10-minute demo script
```

## Run locally
**Docker:** `docker compose up --build`, then open http://localhost:8080 (API docs: http://localhost:8000/docs).

**Without Docker:**
```
cd backend && pip install -r requirements.txt && python scripts/fetch_data.py && uvicorn main:app --reload
cd frontend && npm install && npm run dev      # http://localhost:5173 (proxies /api to :8000)
```
Tests: `cd backend && python -m pytest`.

## Data and fallback
1. `backend/data/*.csv` cache, else 2. live Elexon API, else 3. **synthetic demo data** (the UI shows a warning banner).
**Run `python scripts/fetch_data.py` and commit the CSVs before deploying**, so the deployed app shows real data.

## Deploy
**Vercel:** import the repo (root directory), commit the CSV cache, deploy. `vercel.json` builds the frontend and serves
FastAPI from `api/index.py`. **Heroku:** use the container stack with `heroku.yml`/`docker-compose` images (frontend nginx proxies `/api` to the backend).
After deploying, open the URL in an incognito window and check `/api/health`.

## Limitations
Elexon endpoint parameters were written from the public API documentation and not exercised against the live API in the
authoring environment; run `fetch_data.py` once to confirm. If WINDFOR is hourly, only periods present in both datasets are compared.
