"""Fetch real Elexon data for Jan 2026 and write CSV caches into backend/data/.
Run from the backend directory:  python scripts/fetch_data.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import elexon_service as svc  # noqa: E402

if __name__ == "__main__":
    actuals = svc.fetch_actuals_live()
    forecasts = svc.fetch_forecasts_live()
    svc.save_cache(actuals, forecasts)
    print(f"actuals: {len(actuals)} rows, forecasts: {len(forecasts)} rows -> {svc.DATA_DIR}")
