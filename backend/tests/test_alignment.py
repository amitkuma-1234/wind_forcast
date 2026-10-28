import sys
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import elexon_service as svc  # noqa: E402


def ts(s):
    return pd.Timestamp(s, tz="UTC")


def make():
    target = ts("2026-01-05 12:00")
    actuals = pd.DataFrame({"startTime": [target], "generation": [1000.0]})
    forecasts = pd.DataFrame(
        {
            "startTime": [target] * 4,
            "publishTime": [ts("2026-01-03 09:00"), ts("2026-01-04 08:30"), ts("2026-01-04 10:00"), ts("2026-01-05 06:00")],
            "generation": [700.0, 800.0, 900.0, 990.0],
        }
    )
    return actuals, forecasts


def test_picks_latest_forecast_before_cutoff():
    a, f = make()
    df = svc.align(a, f, "09:00")
    assert len(df) == 1 and df.forecast[0] == 800.0 and df.error[0] == 200.0


def test_later_cutoff_sees_newer_forecast():
    a, f = make()
    assert svc.align(a, f, "11:00").forecast[0] == 900.0


def test_never_uses_same_day_forecast():
    a, f = make()
    assert svc.align(a, f, "23:59").forecast[0] == 900.0  # 990 published on D, not D-1


def test_no_eligible_forecast_drops_row():
    a, f = make()
    assert svc.align(a, f.iloc[[3]], "09:00").empty


def test_bad_cutoff():
    a, f = make()
    with pytest.raises(ValueError):
        svc.align(a, f, "25:00")


def test_metrics():
    a, f = make()
    m = svc.compute_metrics(svc.align(a, f, "09:00"), 50)
    assert m["mae_mw"] == 200 and m["rmse_mw"] == 200 and m["bias_pct"] == -20


def test_synthetic_pipeline_and_api(tmp_path):
    from fastapi.testclient import TestClient
    import main

    svc.ALLOW_LIVE = False
    svc.ACTUALS_FILE = tmp_path / "none.csv"
    svc.load_data(force=True)
    c = TestClient(main.app)
    assert c.get("/api/meta").json()["is_synthetic"] is True
    r = c.get("/api/analysis?cutoff=09:00&resolution=daily").json()
    assert r["kpis"]["n"] > 1000 and len(r["series"]) == 31
    assert c.get("/api/analysis?cutoff=9am").status_code == 422
    assert c.get("/api/analysis?start=2026-02-01").status_code == 422
    assert c.get("/api/analysis?start=2026-01-10&end=2026-01-05").status_code == 422
    assert c.get("/api/export.csv?cutoff=11:00").text.startswith("startTime,actual")
