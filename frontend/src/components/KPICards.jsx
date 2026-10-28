import React from "react";
import { Activity, Gauge, Scale, ShieldAlert, Sigma, Wind } from "lucide-react";

const fmt = (v, d = 0) =>
  v === null || v === undefined ? "n/a" : Number(v).toLocaleString("en-GB", { maximumFractionDigits: d });

function Card({ icon: Icon, label, value, unit, note, tone = "text-slate-100" }) {
  return (
    <div className="rounded-lg border border-line bg-panel p-4">
      <div className="flex items-center gap-2 text-sm text-slate-400">
        <Icon size={16} aria-hidden="true" />
        <span>{label}</span>
      </div>
      <div className={`mt-2 text-2xl font-semibold ${tone}`}>
        {value}
        {unit && <span className="ml-1 text-sm font-normal text-slate-400">{unit}</span>}
      </div>
      {note && <div className="mt-1 text-xs text-slate-500">{note}</div>}
    </div>
  );
}

export default function KPICards({ kpis }) {
  if (!kpis || !kpis.n) {
    return (
      <div className="rounded-lg border border-line bg-panel p-4 text-sm text-slate-400">
        No overlapping forecast and actual periods for this selection. Widen the date range or choose a later cutoff.
      </div>
    );
  }
  const bias = kpis.bias_pct;
  const biasText = bias === null ? "n/a" : `${bias > 0 ? "+" : ""}${fmt(bias, 2)}%`;
  const biasNote = bias === null ? "" : bias > 0 ? "Over-forecast: wind came in lower than expected" : "Under-forecast: wind came in higher than expected";
  const riskTone = kpis.risk_level === "High" ? "text-err" : kpis.risk_level === "Medium" ? "text-forecast" : "text-emerald-300";

  return (
    <section aria-label="Key figures" className="grid grid-cols-1 gap-3 sm:grid-cols-2 xl:grid-cols-3">
      <Card icon={Wind} label="Actual wind generation" value={fmt(kpis.actual_mwh)} unit="MWh" tone="text-actual" />
      <Card icon={Wind} label="Forecast wind generation" value={fmt(kpis.forecast_mwh)} unit="MWh" tone="text-forecast" />
      <Card icon={Activity} label="Mean absolute error (MAE)" value={fmt(kpis.mae_mw)} unit="MW" note={`90% of periods within ${fmt(kpis.p90_abs_error_mw)} MW`} />
      <Card icon={Sigma} label="Root mean squared error (RMSE)" value={fmt(kpis.rmse_mw)} unit="MW" note={`${fmt(kpis.nrmse_pct, 1)}% of mean wind output`} />
      <Card icon={Scale} label="Forecast bias" value={biasText} note={biasNote} />
      <Card
        icon={ShieldAlert}
        label="Imbalance risk score"
        value={`${fmt(kpis.risk_score, 0)} / 100`}
        tone={riskTone}
        note={`${kpis.risk_level}. Illustrative exposure £${fmt(kpis.exposure_gbp)} at £${kpis.price_gbp_mwh}/MWh`}
      />
    </section>
  );
}
