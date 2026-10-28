import React from "react";
import { Bar, Brush, CartesianGrid, ComposedChart, Legend, Line, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

const num = (v) => (v === null || v === undefined ? "n/a" : Number(v).toLocaleString("en-GB", { maximumFractionDigits: 0 }));

export default function ForecastChart({ series, resolution }) {
  const unit = resolution === "daily" ? "MWh" : "MW";
  if (!series || series.length === 0) {
    return <div className="rounded-lg border border-line bg-panel p-6 text-sm text-slate-400">No data to chart.</div>;
  }
  const tickGap = resolution === "daily" ? 20 : 90;
  return (
    <div className="rounded-lg border border-line bg-panel p-4">
      <h2 className="text-base font-semibold text-slate-100">Actual vs forecast wind generation</h2>
      <p className="mb-3 text-xs text-slate-400">
        Lines use the left axis ({unit}). Bars show the error (actual minus forecast) on the right axis. Drag the slider below to zoom.
      </p>
      <div className="h-[380px]" role="img" aria-label={`Time series of actual and forecast wind generation in ${unit}`}>
        <ResponsiveContainer width="100%" height="100%">
          <ComposedChart data={series} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
            <CartesianGrid stroke="#223250" strokeDasharray="3 3" />
            <XAxis dataKey="label" stroke="#64748b" tick={{ fontSize: 11 }} minTickGap={tickGap} />
            <YAxis yAxisId="gen" stroke="#64748b" tick={{ fontSize: 11 }} tickFormatter={num} width={70} />
            <YAxis yAxisId="err" orientation="right" stroke="#64748b" tick={{ fontSize: 11 }} tickFormatter={num} width={70} />
            <Tooltip
              contentStyle={{ background: "#0a1020", border: "1px solid #223250", borderRadius: 8 }}
              formatter={(v, name) => [`${num(v)} ${unit}`, name]}
            />
            <Legend />
            <Bar yAxisId="err" dataKey="error" name="Error (actual − forecast)" fill="#fb7185" fillOpacity={0.45} isAnimationActive={false} />
            <Line yAxisId="gen" type="monotone" dataKey="actual" name="Actual" stroke="#38bdf8" strokeWidth={2} dot={false} isAnimationActive={false} />
            <Line yAxisId="gen" type="monotone" dataKey="forecast" name="Forecast" stroke="#fbbf24" strokeWidth={2} dot={false} isAnimationActive={false} />
            <Brush dataKey="label" height={24} stroke="#38bdf8" fill="#0a1020" travellerWidth={8} />
          </ComposedChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
