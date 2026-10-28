import React, { useEffect, useMemo, useState } from "react";
import { ChevronLeft, ChevronRight, Download, Search } from "lucide-react";

const PAGE = 25;
const num = (v) => (v === null || v === undefined ? "n/a" : Number(v).toLocaleString("en-GB", { maximumFractionDigits: 0 }));

export default function DataTable({ series, resolution, csvHref }) {
  const [q, setQ] = useState("");
  const [page, setPage] = useState(0);
  const unit = resolution === "daily" ? "MWh" : "MW";

  const rows = useMemo(() => {
    const needle = q.trim().toLowerCase();
    return needle ? series.filter((r) => `${r.time} ${r.label}`.toLowerCase().includes(needle)) : series;
  }, [series, q]);

  useEffect(() => setPage(0), [q, series]);
  const pages = Math.max(1, Math.ceil(rows.length / PAGE));
  const view = rows.slice(page * PAGE, page * PAGE + PAGE);

  return (
    <div className="rounded-lg border border-line bg-panel p-4">
      <div className="mb-3 flex flex-wrap items-center justify-between gap-3">
        <h2 className="text-base font-semibold text-slate-100">Data drill-down</h2>
        <div className="flex items-center gap-2">
          <label className="relative">
            <span className="sr-only">Search rows</span>
            <Search size={14} className="absolute left-2 top-2.5 text-slate-500" aria-hidden="true" />
            <input
              value={q}
              onChange={(e) => setQ(e.target.value)}
              placeholder="Search e.g. 2026-01-15"
              className="w-56 rounded-md border border-line bg-ink py-1.5 pl-7 pr-2 text-sm"
            />
          </label>
          <a href={csvHref} className="inline-flex items-center gap-1 rounded-md border border-line bg-ink px-3 py-1.5 text-sm hover:border-actual">
            <Download size={14} aria-hidden="true" /> Export CSV
          </a>
        </div>
      </div>
      <div className="overflow-x-auto">
        <table className="w-full text-left text-sm">
          <thead className="text-slate-400">
            <tr className="border-b border-line">
              <th className="py-2 pr-4 font-medium">{resolution === "daily" ? "Day" : "Period start (UTC)"}</th>
              <th className="py-2 pr-4 text-right font-medium">Actual ({unit})</th>
              <th className="py-2 pr-4 text-right font-medium">Forecast ({unit})</th>
              <th className="py-2 pr-4 text-right font-medium">Error ({unit})</th>
              <th className="py-2 font-medium">Forecast published (UTC)</th>
            </tr>
          </thead>
          <tbody>
            {view.map((r) => (
              <tr key={r.time} className="border-b border-line/50">
                <td className="py-1.5 pr-4">{r.time.replace("T", " ").replace("Z", "")}</td>
                <td className="py-1.5 pr-4 text-right text-actual">{num(r.actual)}</td>
                <td className="py-1.5 pr-4 text-right text-forecast">{num(r.forecast)}</td>
                <td className={`py-1.5 pr-4 text-right ${r.error > 0 ? "text-emerald-300" : "text-err"}`}>{num(r.error)}</td>
                <td className="py-1.5 text-slate-400">{r.publish_time ? r.publish_time.replace("T", " ").replace("Z", "") : "n/a (daily total)"}</td>
              </tr>
            ))}
            {view.length === 0 && (
              <tr><td colSpan={5} className="py-6 text-center text-slate-500">No rows match.</td></tr>
            )}
          </tbody>
        </table>
      </div>
      <div className="mt-3 flex items-center justify-between text-xs text-slate-400">
        <span>{rows.length.toLocaleString("en-GB")} rows</span>
        <div className="flex items-center gap-2">
          <button onClick={() => setPage((p) => Math.max(0, p - 1))} disabled={page === 0} className="rounded border border-line p-1 disabled:opacity-40" aria-label="Previous page">
            <ChevronLeft size={16} />
          </button>
          <span>Page {page + 1} of {pages}</span>
          <button onClick={() => setPage((p) => Math.min(pages - 1, p + 1))} disabled={page >= pages - 1} className="rounded border border-line p-1 disabled:opacity-40" aria-label="Next page">
            <ChevronRight size={16} />
          </button>
        </div>
      </div>
    </div>
  );
}
