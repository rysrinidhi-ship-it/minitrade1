const inr = new Intl.NumberFormat("en-IN", { style: "currency", currency: "INR", minimumFractionDigits: 2 });
const num = new Intl.NumberFormat("en-IN");

export const formatINR = (value) => (value === null || value === undefined ? "—" : inr.format(value));
export const formatNumber = (value) => (value === null || value === undefined ? "—" : num.format(value));

/** +1.23% / -0.50% / 0.00% */
export function formatPct(value) {
  if (value === null || value === undefined) return "—";
  const sign = value > 0 ? "+" : "";
  return `${sign}${value.toFixed(2)}%`;
}

/** +₹18.19 / -₹37.53 */
export function formatSignedINR(value) {
  if (value === null || value === undefined) return "—";
  const sign = value > 0 ? "+" : value < 0 ? "-" : "";
  return `${sign}${inr.format(Math.abs(value))}`;
}

export function formatDateTime(iso) {
  return new Date(iso).toLocaleString("en-IN", { day: "2-digit", month: "short", year: "numeric", hour: "2-digit", minute: "2-digit" });
}

export function formatDate(iso) {
  // "2026-10-23" -> parse as a plain calendar date (avoid timezone shifting)
  const [y, m, d] = iso.split("-").map(Number);
  return new Date(y, m - 1, d).toLocaleDateString("en-IN", { day: "2-digit", month: "short" });
}

/** CSS class for gain / loss / flat. Colour is never the only signal: values also carry +/- signs and arrows. */
export const trendClass = (value) => (value > 0 ? "gain" : value < 0 ? "loss" : "flat");
export const trendArrow = (value) => (value > 0 ? "▲" : value < 0 ? "▼" : "–");
