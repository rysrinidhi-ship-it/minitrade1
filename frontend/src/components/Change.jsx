import { formatPct, formatSignedINR, trendArrow, trendClass } from "../utils/format.js";

/** "▲ +₹18.19 (+2.37%)" in green / red. The arrow + sign mean colour is not the only signal. */
export default function Change({ change, pct, showAmount = true }) {
  if (change === null || change === undefined) return <span className="flat">—</span>;
  return (
    <span className={trendClass(change)}>
      <span aria-hidden="true">{trendArrow(change)}</span> {showAmount && `${formatSignedINR(change)} `}
      {showAmount ? `(${formatPct(pct)})` : formatPct(pct)}
    </span>
  );
}
