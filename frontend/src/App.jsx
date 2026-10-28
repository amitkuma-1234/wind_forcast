import React, { useEffect, useState } from "react";
import { AlertTriangle, Loader2 } from "lucide-react";
import { exportUrl, fetchAnalysis, fetchMeta } from "./api.js";
import KPICards from "./components/KPICards.jsx";
import ForecastChart from "./components/ForecastChart.jsx";
import ErrorMetricsChart from "./components/ErrorMetricsChart.jsx";
import DataTable from "./components/DataTable.jsx";

const field = "rounded-md border border-line bg-ink px-2 py-1.5 text-sm";

export default function App() {
  const [meta, setMeta] = useState(null);
  const [cutoff, setCutoff] = useState("09:00");
  const [start, setStart] = useState("2026-01-01");
  const [end, setEnd] = useState("2026-01-31");
  const [resolution, setResolution] = useState("30min");
  const [price, setPrice] = useState(50);
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    fetchMeta()
      .then((m) => { setMeta(m); setCutoff(m.default_cutoff); })
      .catch((e) => { setError(e.message); setLoading(false); });
  }, []);

  useEffect(() => {
    if (!meta) return;
    if (start > end) { setError("Start date must be on or before end date."); return; }
    let live = true;
    setLoading(true);
    setError(null);
    fetchAnalysis({ cutoff, start, end, resolution, price })
      .then((d) => live && setData(d))
      .catch((e) => live && setError(e.message))
      .finally(() => live && setLoading(false));
    return () => { live = false; };
  }, [meta, cutoff, start, end, resolution, price]);

  const k = data?.kpis;
  return (
    <div className="mx-auto max-w-[1400px] px-4 py-6">
      <header className="mb-5">
        <h1 className="text-2xl font-semibold text-slate-50">Wind forecast desk</h1>
        <p className="mt-1 max-w-3xl text-sm text-slate-400">
          For each half-hour of a delivery day, this shows the latest Elexon wind forecast that existed at your chosen cutoff on the day before,
          and how far it was from what the wind actually produced. Great Britain, national level, January 2026.
        </p>
      </header>

      {meta?.is_synthetic && (
        <div role="alert" className="mb-4 flex items-start gap-2 rounded-lg border border-forecast/50 bg-forecast/10 p-3 text-sm text-forecast">
          <AlertTriangle size={18} className="mt-0.5 shrink-0" aria-hidden="true" />
          <span>This view is showing synthetic demo data, because the Elexon cache is missing and the live API could not be reached. Do not use these numbers for trading decisions.</span>
        </div>
      )}

      <section aria-label="Filters" className="mb-5 flex flex-wrap items-end gap-4 rounded-lg border border-line bg-panel p-4">
        <label className="flex flex-col gap-1 text-xs text-slate-400">
          Decision cutoff on D-1 (UTC)
          <select className={field} value={cutoff} onChange={(e) => setCutoff(e.target.value)}>
            {(meta?.cutoff_options || ["09:00"]).map((c) => <option key={c} value={c}>{c}</option>)}
          </select>
        </label>
        <label className="flex flex-col gap-1 text-xs text-slate-400">
          From
          <input type="date" className={field} min="2026-01-01" max="2026-01-31" value={start} onChange={(e) => e.target.value && setStart(e.target.value)} />
        </label>
        <label className="flex flex-col gap-1 text-xs text-slate-400">
          To
          <input type="date" className={field} min="2026-01-01" max="2026-01-31" value={end} onChange={(e) => e.target.value && setEnd(e.target.value)} />
        </label>
        <div className="flex flex-col gap-1 text-xs text-slate-400">
          View
          <div className="inline-flex overflow-hidden rounded-md border border-line" role="group" aria-label="Resolution">
            {[["30min", "30-minute"], ["daily", "Daily total"]].map(([v, l]) => (
              <button key={v} onClick={() => setResolution(v)} aria-pressed={resolution === v}
                className={`px-3 py-1.5 text-sm ${resolution === v ? "bg-actual text-ink" : "bg-ink text-slate-300"}`}>{l}</button>
            ))}
          </div>
        </div>
        <label className="flex flex-col gap-1 text-xs text-slate-400">
          Assumed imbalance price (£/MWh)
          <input type="number" min="0" max="5000" step="5" className={`${field} w-28`} value={price}
            onChange={(e) => setPrice(Math.max(0, Math.min(5000, Number(e.target.value) || 0)))} />
        </label>
        {loading && <Loader2 className="mb-2 animate-spin text-actual" size={20} aria-label="Loading" />}
      </section>

      {error && (
        <div role="alert" className="mb-4 rounded-lg border border-err/50 bg-err/10 p-3 text-sm text-err">{error}</div>
      )}

      {data && (
        <div className="space-y-4">
          {k?.n > 0 && (
            <p className="text-sm text-slate-400">
              Using {k.n.toLocaleString("en-GB")} periods. Forecasts used were published between {k.earliest_publish_time.replace("T", " ").replace("Z", "")} and{" "}
              {k.latest_publish_time.replace("T", " ").replace("Z", "")} UTC, never later than {cutoff} UTC on the day before delivery.
            </p>
          )}
          <KPICards kpis={k} />
          <ForecastChart series={data.series} resolution={data.resolution} />
          <ErrorMetricsChart series={data.series} histogram={data.histogram} byHour={data.by_hour} resolution={data.resolution} />
          <DataTable series={data.series} resolution={data.resolution} csvHref={exportUrl({ cutoff, start, end })} />
        </div>
      )}

      <footer className="mt-8 border-t border-line pt-4 text-xs text-slate-500">
        Source: Elexon BMRS (FUELHH actuals, WINDFOR forecasts). Error = actual − forecast. Bias = (forecast − actual) ÷ actual, so a positive bias means over-forecast.
        The risk score and £ exposure are illustrative: £ exposure = total absolute error in MWh × the price you enter.
      </footer>
    </div>
  );
}
