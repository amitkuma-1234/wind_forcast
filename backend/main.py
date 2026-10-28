"""FastAPI application: UK wind forecast vs actual evaluation (Jan 2026 day-ahead decisions)."""
from __future__ import annotations

import io
import logging
from typing import Literal

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response

import elexon_service as svc

logging.basicConfig(level=logging.INFO)

app = FastAPI(title="UK Wind Forecast Evaluation API", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # read-only public data; tighten if auth is ever added
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

DATE_PATTERN = r"^2026-01-(0[1-9]|[12]\d|3[01])$"
CUTOFF_PATTERN = r"^([01]\d|2[0-3]):[0-5]\d$"


def _check_range(start: str | None, end: str | None) -> None:
    if start and end and start > end:
        raise HTTPException(status_code=422, detail="start must be on or before end")


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok"}


@app.get("/api/meta")
def meta() -> dict:
    d = svc.load_data()
    return {
        "source": d["source"],
        "is_synthetic": d["source"] == "synthetic",
        "cutoff_options": svc.CUTOFF_OPTIONS,
        "default_cutoff": svc.DEFAULT_CUTOFF,
        "range": {"start": "2026-01-01", "end": "2026-01-31"},
        "actual_rows": int(len(d["actuals"])),
        "forecast_rows": int(len(d["forecasts"])),
    }


@app.get("/api/analysis")
def analysis(
    cutoff: str = Query(svc.DEFAULT_CUTOFF, pattern=CUTOFF_PATTERN, description="UTC HH:MM on D-1"),
    start: str | None = Query(None, pattern=DATE_PATTERN, description="YYYY-MM-DD, Jan 2026"),
    end: str | None = Query(None, pattern=DATE_PATTERN, description="YYYY-MM-DD, Jan 2026"),
    resolution: Literal["30min", "daily"] = "30min",
    price: float = Query(50.0, ge=0, le=5000, description="Assumed imbalance price GBP/MWh (illustrative)"),
) -> dict:
    _check_range(start, end)
    d = svc.load_data()
    df = svc.get_aligned(cutoff, start, end)
    return {
        "source": d["source"],
        "is_synthetic": d["source"] == "synthetic",
        "cutoff": cutoff,
        "resolution": resolution,
        "kpis": svc.compute_metrics(df, price),
        "series": svc.series_rows(df, resolution),
        "histogram": svc.histogram(df),
        "by_hour": svc.by_hour(df),
    }


@app.get("/api/export.csv")
def export_csv(cutoff: str = Query(svc.DEFAULT_CUTOFF, pattern=CUTOFF_PATTERN, description="UTC HH:MM on D-1"), start: str | None = Query(None, pattern=DATE_PATTERN, description="YYYY-MM-DD, Jan 2026"), end: str | None = Query(None, pattern=DATE_PATTERN, description="YYYY-MM-DD, Jan 2026")) -> Response:
    _check_range(start, end)
    df = svc.get_aligned(cutoff, start, end)
    out = df[["startTime", "actual", "forecast", "error", "abs_error", "publishTime", "horizon_h"]].copy()
    for c in ("startTime", "publishTime"):
        out[c] = out[c].dt.strftime("%Y-%m-%dT%H:%M:%SZ")
    buf = io.StringIO()
    out.round(2).to_csv(buf, index=False)
    name = f"wind_forecast_vs_actual_cutoff_{cutoff.replace(':', '')}.csv"
    return Response(
        buf.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{name}"'},
    )


@app.post("/api/refresh")
def refresh() -> dict:
    d = svc.load_data(force=True)
    return {"source": d["source"]}
