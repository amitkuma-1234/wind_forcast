async function getJson(url) {
  const res = await fetch(url);
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      detail = typeof body.detail === "string" ? body.detail : JSON.stringify(body.detail);
    } catch (_) { /* keep status text */ }
    throw new Error(`Request failed (${res.status}): ${detail}`);
  }
  return res.json();
}

export const fetchMeta = () => getJson("/api/meta");

export function buildQuery({ cutoff, start, end, resolution, price }) {
  const p = new URLSearchParams();
  if (cutoff) p.set("cutoff", cutoff);
  if (start) p.set("start", start);
  if (end) p.set("end", end);
  if (resolution) p.set("resolution", resolution);
  if (price !== undefined && price !== "") p.set("price", String(price));
  return p.toString();
}

export const fetchAnalysis = (params) => getJson(`/api/analysis?${buildQuery(params)}`);
export const exportUrl = ({ cutoff, start, end }) => `/api/export.csv?${buildQuery({ cutoff, start, end })}`;
