"""Data access + alignment logic for the UK wind forecast evaluation app.

Data flow (first match wins):
  1. CSV cache in backend/data/ (produced by scripts/fetch_data.py from the live Elexon API)
  2. Live Elexon BMRS API (if ALLOW_LIVE=1)
  3. Deterministic SYNTHETIC data (clearly flagged in the UI - never real numbers)

All timestamps are UTC (in January, UK local time == UTC).
"""
from __future__ import annotations

import logging
import os
import re
from datetime import timedelta
from functools import lru_cache
from pathlib import Path

import httpx
import numpy as np
import pandas as pd

log = logging.getLogger("elexon_service")

BASE_URL = os.getenv("ELEXON_BASE_URL", "https://data.elexon.co.uk/bmrs/api/v1")
DATA_DIR = Path(os.getenv("DATA_DIR", Path(__file__).parent / "data"))
ACTUALS_FILE = DATA_DIR / "actuals_jan2026.csv"
FORECASTS_FILE = DATA_DIR / "forecasts_jan2026.csv"
ALLOW_LIVE = os.getenv("ALLOW_LIVE", "1") == "1"

TARGET_START = pd.Timestamp("2026-01-01T00:00:00Z")
TARGET_END = pd.Timestamp("2026-02-01T00:00:00Z")  # exclusive
# Forecasts for 1 Jan delivery are published on 31 Dec or earlier; look back a week.
PUBLISH_FROM = pd.Timestamp("2025-12-25T00:00:00Z")

CUTOFF_RE = re.compile(r"^([01]\d|2[0-3]):([0-5]\d)$")
CUTOFF_OPTIONS = ["08:00", "09:00", "09:30", "11:00", "12:00", "17:00"]
DEFAULT_CUTOFF = "09:00"


# --------------------------------------------------------------------------- live fetch
def _get_json(client: httpx.Client, path: str, params: dict) -> list[dict]:
    resp = client.get(f"{BASE_URL}{path}", params=params, timeout=60)
    resp.raise_for_status()
    payload = resp.json()
    return payload["data"] if isinstance(payload, dict) and "data" in payload else payload


def fetch_actuals_live() -> pd.DataFrame:
    """FUELHH stream, WIND only, 1-31 Jan 2026 (chunked by 7 days)."""
    rows: list[dict] = []
    with httpx.Client() as client:
        day = TARGET_START
        while day < TARGET_END:
            nxt = min(day + timedelta(days=7), TARGET_END)
            params = {
                "settlementDateFrom": day.strftime("%Y-%m-%d"),
                "settlementDateTo": (nxt - timedelta(days=1)).strftime("%Y-%m-%d"),
                "fuelType": "WIND",
                "format": "json",
            }
            rows += _get_json(client, "/datasets/FUELHH/stream", params)
            day = nxt
    df = pd.DataFrame(rows)
    if df.empty:
        raise RuntimeError("FUELHH returned no rows")
    df = df[df["fuelType"] == "WIND"]
    return _clean_actuals(df)


def fetch_forecasts_live() -> pd.DataFrame:
    """WINDFOR stream by publish time (chunked by 2 days)."""
    rows: list[dict] = []
    with httpx.Client() as client:
        t = PUBLISH_FROM
        while t < TARGET_END:
            nxt = min(t + timedelta(days=2), TARGET_END)
            params = {
                "publishDateTimeFrom": t.strftime("%Y-%m-%dT%H:%MZ"),
                "publishDateTimeTo": nxt.strftime("%Y-%m-%dT%H:%MZ"),
                "format": "json",
            }
            rows += _get_json(client, "/datasets/WINDFOR/stream", params)
            t = nxt
    df = pd.DataFrame(rows)
    if df.empty:
        raise RuntimeError("WINDFOR returned no rows")
    return _clean_forecasts(df)


# --------------------------------------------------------------------------- cleaning
def _clean_actuals(df: pd.DataFrame) -> pd.DataFrame:
    out = pd.DataFrame(
        {
            "startTime": pd.to_datetime(df["startTime"], utc=True),
            "generation": pd.to_numeric(df["generation"], errors="coerce"),
        }
    )
    out = out.dropna().drop_duplicates("startTime").sort_values("startTime")
    out = out[(out.startTime >= TARGET_START) & (out.startTime < TARGET_END)]
    return out.reset_index(drop=True)


def _clean_forecasts(df: pd.DataFrame) -> pd.DataFrame:
    out = pd.DataFrame(
        {
            "startTime": pd.to_datetime(df["startTime"], utc=True),
            "publishTime": pd.to_datetime(df["publishTime"], utc=True),
            "generation": pd.to_numeric(df["generation"], errors="coerce"),
        }
    )
    out = out.dropna().drop_duplicates(["startTime", "publishTime"])
    out = out[(out.startTime >= TARGET_START) & (out.startTime < TARGET_END)]
    # a forecast published after its target period started is not a forecast
    out = out[out.publishTime <= out.startTime]
    return out.sort_values(["startTime", "publishTime"]).reset_index(drop=True)


# --------------------------------------------------------------------------- synthetic fallback
def synthetic_data(seed: int = 2026) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Deterministic SYNTHETIC wind data for demo/offline use. NOT real Elexon data."""
    rng = np.random.default_rng(seed)
    idx = pd.date_range(TARGET_START, TARGET_END, freq="30min", inclusive="left")
    n = len(idx)
    noise = np.zeros(n)
    for i in range(1, n):
        noise[i] = 0.985 * noise[i - 1] + rng.normal(0, 0.06)
    base = 0.45 + 0.8 * noise + 0.04 * np.sin(2 * np.pi * (idx.hour + idx.minute / 60) / 24)
    cap = 22000.0
    actual = np.clip(base, 0.03, 0.95) * cap
    actuals = pd.DataFrame({"startTime": idx, "generation": actual})

    truth = pd.Series(actual, index=idx)
    pubs = pd.date_range(PUBLISH_FROM, TARGET_END - timedelta(hours=1), freq="3h")
    frames = []
    for p in pubs:
        tgt = idx[(idx > p) & (idx <= p + timedelta(hours=60))]
        if len(tgt) == 0:
            continue
        horizon_h = np.asarray((tgt - p).total_seconds()) / 3600
        sd = cap * (0.015 + 0.0035 * horizon_h)  # error grows with lead time
        f = truth.loc[tgt].values * 0.97 + rng.normal(0, 1, len(tgt)) * sd  # mild under-forecast
        frames.append(pd.DataFrame({"startTime": tgt, "publishTime": p, "generation": np.clip(f, 0, cap)}))
    forecasts = pd.concat(frames, ignore_index=True)
    forecasts = forecasts[forecasts.publishTime <= forecasts.startTime]
    return actuals, forecasts


# --------------------------------------------------------------------------- loading
_STATE: dict = {}


def load_data(force: bool = False) -> dict:
    """Return {'actuals', 'forecasts', 'source'} (cached in process memory)."""
    if _STATE and not force:
        return _STATE
    actuals = forecasts = None
    source = "synthetic"
    if ACTUALS_FILE.exists() and FORECASTS_FILE.exists():
        try:
            actuals = _clean_actuals(pd.read_csv(ACTUALS_FILE))
            forecasts = _clean_forecasts(pd.read_csv(FORECASTS_FILE))
            source = "elexon-cache"
        except Exception as exc:
            log.warning("Cache unreadable (%s)", exc)
            actuals = forecasts = None
    if actuals is None and ALLOW_LIVE:
        try:
            actuals, forecasts = fetch_actuals_live(), fetch_forecasts_live()
            save_cache(actuals, forecasts)
            source = "elexon-live"
        except Exception as exc:
            log.warning("Live Elexon fetch failed (%s); using synthetic data", exc)
            actuals = forecasts = None
    if actuals is None or actuals.empty or forecasts is None or forecasts.empty:
        actuals, forecasts = synthetic_data()
        source = "synthetic"
    _STATE.clear()
    _STATE.update(actuals=actuals, forecasts=forecasts, source=source)
    _align_cached.cache_clear()
    return _STATE


def save_cache(actuals: pd.DataFrame, forecasts: pd.DataFrame) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    actuals.to_csv(ACTUALS_FILE, index=False)
    forecasts.to_csv(FORECASTS_FILE, index=False)


# --------------------------------------------------------------------------- core logic
def align(actuals: pd.DataFrame, forecasts: pd.DataFrame, cutoff: str, lead_days: int = 1) -> pd.DataFrame:
    """For every target period pick the LATEST forecast published at or before the cutoff
    on D-lead_days (D = delivery day of the target period), then join with actuals.

    error = actual - forecast (positive => forecast was too low / under-forecast).
    """
    m = CUTOFF_RE.match(cutoff)
    if not m:
        raise ValueError(f"cutoff must be HH:MM, got {cutoff!r}")
    hh, mm = int(m.group(1)), int(m.group(2))

    f = forecasts.copy()
    delivery_day = f["startTime"].dt.normalize()
    f["cutoffTime"] = delivery_day - pd.Timedelta(days=lead_days) + pd.Timedelta(hours=hh, minutes=mm)
    f = f[f["publishTime"] <= f["cutoffTime"]]
    f = f.sort_values(["startTime", "publishTime"]).groupby("startTime", as_index=False).last()
    f = f.rename(columns={"generation": "forecast"})

    a = actuals.rename(columns={"generation": "actual"})[["startTime", "actual"]]
    df = a.merge(f[["startTime", "publishTime", "cutoffTime", "forecast"]], on="startTime", how="inner")
    df["error"] = df["actual"] - df["forecast"]
    df["abs_error"] = df["error"].abs()
    df["horizon_h"] = (df["startTime"] - df["publishTime"]).dt.total_seconds() / 3600
    return df.sort_values("startTime").reset_index(drop=True)


@lru_cache(maxsize=32)
def _align_cached(cutoff: str) -> pd.DataFrame:
    d = load_data()
    return align(d["actuals"], d["forecasts"], cutoff)


def get_aligned(cutoff: str, start: str | None, end: str | None) -> pd.DataFrame:
    df = _align_cached(cutoff)
    if start:
        df = df[df["startTime"] >= pd.Timestamp(start, tz="UTC")]
    if end:  # inclusive end date
        df = df[df["startTime"] < pd.Timestamp(end, tz="UTC") + pd.Timedelta(days=1)]
    return df.reset_index(drop=True)


# --------------------------------------------------------------------------- metrics
def _f(x) -> float | None:
    return None if x is None or not np.isfinite(x) else round(float(x), 2)


def step_hours(df: pd.DataFrame) -> float:
    if len(df) < 2:
        return 0.5
    return float(df["startTime"].diff().dropna().median().total_seconds() / 3600) or 0.5


def compute_metrics(df: pd.DataFrame, price_gbp_mwh: float) -> dict:
    if df.empty:
        return {"n": 0}
    h = step_hours(df)
    err = df["error"].to_numpy()
    mae = float(np.mean(np.abs(err)))
    rmse = float(np.sqrt(np.mean(err**2)))
    act_mwh = float(df["actual"].sum() * h)
    fc_mwh = float(df["forecast"].sum() * h)
    mean_actual = float(df["actual"].mean())
    # bias: (forecast - actual) / actual. Positive => OVER-forecast.
    bias_pct = (fc_mwh - act_mwh) / act_mwh * 100 if act_mwh else float("nan")
    nrmse = rmse / mean_actual if mean_actual else float("nan")
    # Heuristic 0-100 score: NRMSE of 50% of mean output maps to 100. Not a market-standard metric.
    risk = float(np.clip(nrmse / 0.5 * 100, 0, 100)) if np.isfinite(nrmse) else None
    exposure = float(np.sum(np.abs(err)) * h * price_gbp_mwh)
    level = None if risk is None else ("Low" if risk < 25 else "Medium" if risk < 50 else "High")
    return {
        "n": int(len(df)),
        "step_hours": h,
        "actual_mwh": _f(act_mwh),
        "forecast_mwh": _f(fc_mwh),
        "mae_mw": _f(mae),
        "rmse_mw": _f(rmse),
        "mean_error_mw": _f(np.mean(err)),
        "bias_pct": _f(bias_pct),
        "p90_abs_error_mw": _f(np.percentile(np.abs(err), 90)),
        "nrmse_pct": _f(nrmse * 100),
        "risk_score": _f(risk),
        "risk_level": level,
        "exposure_gbp": _f(exposure),
        "price_gbp_mwh": price_gbp_mwh,
        "mean_horizon_h": _f(df["horizon_h"].mean()),
        "latest_publish_time": df["publishTime"].max().strftime("%Y-%m-%dT%H:%M:%SZ"),
        "earliest_publish_time": df["publishTime"].min().strftime("%Y-%m-%dT%H:%M:%SZ"),
    }


def series_rows(df: pd.DataFrame, resolution: str) -> list[dict]:
    if df.empty:
        return []
    if resolution == "daily":
        h = step_hours(df)
        g = df.assign(day=df["startTime"].dt.strftime("%Y-%m-%d")).groupby("day")
        out = g.agg(actual=("actual", "sum"), forecast=("forecast", "sum"), n=("actual", "size")).reset_index()
        out["actual"] *= h
        out["forecast"] *= h
        out["error"] = out["actual"] - out["forecast"]
        out["abs_error"] = out["error"].abs()
        return [
            {
                "time": r.day,
                "label": r.day,
                "actual": _f(r.actual),
                "forecast": _f(r.forecast),
                "error": _f(r.error),
                "abs_error": _f(r.abs_error),
                "publish_time": None,
                "periods": int(r.n),
            }
            for r in out.itertuples()
        ]
    return [
        {
            "time": r.startTime.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "label": r.startTime.strftime("%d %b %H:%M"),
            "actual": _f(r.actual),
            "forecast": _f(r.forecast),
            "error": _f(r.error),
            "abs_error": _f(r.abs_error),
            "publish_time": r.publishTime.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "periods": 1,
        }
        for r in df.itertuples()
    ]


def histogram(df: pd.DataFrame, bins: int = 20) -> list[dict]:
    if df.empty:
        return []
    counts, edges = np.histogram(df["error"].to_numpy(), bins=bins)
    return [
        {"label": f"{edges[i]:.0f}", "from": _f(edges[i]), "to": _f(edges[i + 1]), "count": int(counts[i])}
        for i in range(len(counts))
    ]


def by_hour(df: pd.DataFrame) -> list[dict]:
    if df.empty:
        return []
    g = df.assign(hour=df["startTime"].dt.hour).groupby("hour")
    out = g.agg(mae=("abs_error", "mean"), bias=("error", "mean")).reset_index()
    return [{"hour": int(r.hour), "mae": _f(r.mae), "mean_error": _f(r.bias)} for r in out.itertuples()]
