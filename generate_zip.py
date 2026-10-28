"""Package the project into uk_energy_wind_forecast_app.zip (skips node_modules, dist, caches).
Usage: python generate_zip.py
"""
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "uk_energy_wind_forecast_app.zip"
SKIP_DIRS = {"node_modules", "dist", "__pycache__", ".pytest_cache", ".venv", ".git"}

with zipfile.ZipFile(OUT, "w", zipfile.ZIP_DEFLATED) as z:
    for p in sorted(ROOT.rglob("*")):
        if p.is_dir() or p == OUT or p.suffix == ".zip" or SKIP_DIRS & set(p.relative_to(ROOT).parts):
            continue
        z.write(p, p.relative_to(ROOT))
print(f"Wrote {OUT} ({OUT.stat().st_size / 1024:.0f} KB)")
