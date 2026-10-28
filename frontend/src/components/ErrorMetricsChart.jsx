import React from "react";
import { Bar, BarChart, CartesianGrid, ReferenceLine, ResponsiveContainer, Scatter, ScatterChart, Tooltip, XAxis, YAxis } from "recharts";

const num = (v) => Number(v).toLocaleString("en-GB", { maximumFractionDigits: 0 });
const tip = { background: "#0a1020", border: "1px solid #223250", borderRadius: 8 };

function Panel({ title, sub, children }) {
  return (
    <div className="rounded-lg border border-line bg-panel p-4">
      <h3 className="text-sm font-semibold text-slate-100">{title}</h3>
      <p className="mb-2 text-xs text-slate-400">{sub}</p>
      <div className="h-[240px]">{children}</div>
    </div>
  );
}

export default function ErrorMetricsChart({ series, histogram, byHour, resolution }) {
  const unit = resolution === "daily" ? "MWh" : "MW";
  const scatter = (series || []).map((r, i) => ({ x: i, label: r.label, error: r.error }));
  return (
    <section aria-label="Error analysis" className="grid grid-cols-1 gap-3 xl:grid-cols-3">
      <Panel title="Error distribution" sub="Count of settlement periods by error size (MW). Left of zero = over-forecast.">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={histogram} margin={{ top: 4, right: 4, left: 0, bottom: 0 }}>
            <CartesianGrid stroke="#223250" strokeDasharray="3 3" />
            <XAxis dataKey="label" stroke="#64748b" tick={{ fontSize: 10 }} minTickGap={12} />
            <YAxis stroke="#64748b" tick={{ fontSize: 10 }} width={40} />
            <Tooltip contentStyle={tip} formatter={(v) => [v, "Periods"]} labelFormatter={(l) => `Bin from ${l} MW`} />
            <Bar dataKey="count" fill="#fb7185" isAnimationActive={false} />
          </BarChart>
        </ResponsiveContainer>
      </Panel>

      <Panel title="Error per period" sub={`Each dot is one ${resolution === "daily" ? "day" : "settlement period"} (actual − forecast, ${unit}).`}>
        <ResponsiveContainer width="100%" height="100%">
          <ScatterChart margin={{ top: 4, right: 8, left: 0, bottom: 0 }}>
            <CartesianGrid stroke="#223250" strokeDasharray="3 3" />
            <XAxis type="number" dataKey="x" stroke="#64748b" tick={false} name="Period" />
            <YAxis type="number" dataKey="error" stroke="#64748b" tick={{ fontSize: 10 }} tickFormatter={num} width={56} name="Error" />
            <ReferenceLine y={0} stroke="#64748b" />
            <Tooltip
              contentStyle={tip}
              cursor={{ strokeDasharray: "3 3" }}
              content={({ active, payload }) =>
                active && payload && payload.length ? (
                  <div style={tip} className="p-2 text-xs">
                    <div>{payload[0].payload.label}</div>
                    <div>Error: {num(payload[0].payload.error)} {unit}</div>
                  </div>
                ) : null
              }
            />
            <Scatter data={scatter} fill="#38bdf8" fillOpacity={0.55} isAnimationActive={false} />
          </ScatterChart>
        </ResponsiveContainer>
      </Panel>

      <Panel title="Error by hour of day" sub="Mean absolute error (MW) for each UTC hour. Shows when the forecast is weakest.">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={byHour} margin={{ top: 4, right: 4, left: 0, bottom: 0 }}>
            <CartesianGrid stroke="#223250" strokeDasharray="3 3" />
            <XAxis dataKey="hour" stroke="#64748b" tick={{ fontSize: 10 }} />
            <YAxis stroke="#64748b" tick={{ fontSize: 10 }} tickFormatter={num} width={48} />
            <Tooltip contentStyle={tip} formatter={(v) => [`${num(v)} MW`, "MAE"]} labelFormatter={(h) => `${String(h).padStart(2, "0")}:00 UTC`} />
            <Bar dataKey="mae" fill="#fbbf24" isAnimationActive={false} />
          </BarChart>
        </ResponsiveContainer>
      </Panel>
    </section>
  );
}
