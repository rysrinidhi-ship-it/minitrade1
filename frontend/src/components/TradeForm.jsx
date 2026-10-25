import { useState } from "react";
import { placeOrder } from "../api/index.js";
import { useTrading } from "../context/TradingContext.jsx";
import { formatINR } from "../utils/format.js";

/** Buy / sell form for one stock. Market orders only: they execute at the latest close. */
export default function TradeForm({ stock }) {
  const { portfolio, refreshPortfolio } = useTrading();
  const [side, setSide] = useState("BUY");
  const [qtyText, setQtyText] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(null);

  const owned = portfolio?.holdings.find((h) => h.symbol === stock.symbol)?.quantity ?? 0;
  const balance = portfolio?.wallet_balance;
  const quantity = /^\d+$/.test(qtyText) ? Number(qtyText) : null; // whole numbers only
  const validQuantity = quantity !== null && quantity >= 1;
  const estimate = validQuantity ? quantity * stock.price : null;

  // Friendly hints only. The server re-checks everything and has the final say.
  let hint = null;
  if (qtyText !== "" && !validQuantity) hint = "Enter a whole number of shares (1 or more).";
  else if (validQuantity && side === "BUY" && balance !== undefined && estimate > balance)
    hint = "This costs more than your wallet balance.";
  else if (validQuantity && side === "SELL" && quantity > owned)
    hint = `You own only ${owned} share${owned === 1 ? "" : "s"} of ${stock.symbol}.`;

  function changeSide(next) {
    setSide(next);
    setError(null);
    setSuccess(null);
  }

  async function handleSubmit(event) {
    event.preventDefault();
    if (!validQuantity || submitting) return; // also guards against double-clicks
    setSubmitting(true);
    setError(null);
    setSuccess(null);
    try {
      const { data } = await placeOrder({ symbol: stock.symbol, side, quantity });
      setSuccess(
        `${side === "BUY" ? "Bought" : "Sold"} ${data.quantity} × ${data.symbol} at ${formatINR(data.price)} — total ${formatINR(data.total_value)}`
      );
      setQtyText("");
    } catch (err) {
      setError(err);
    } finally {
      setSubmitting(false);
      refreshPortfolio(); // wallet + holdings change after a trade (and re-sync after a rejection)
    }
  }

  const fieldError = error?.details?.fields?.quantity;

  return (
    <form className="card trade" onSubmit={handleSubmit} noValidate>
      <h2>Place order</h2>

      <div className="segmented" role="group" aria-label="Order side">
        <button type="button" className={side === "BUY" ? "active buy" : ""} aria-pressed={side === "BUY"} onClick={() => changeSide("BUY")}>
          Buy
        </button>
        <button type="button" className={side === "SELL" ? "active sell" : ""} aria-pressed={side === "SELL"} onClick={() => changeSide("SELL")}>
          Sell
        </button>
      </div>

      <label className="field">
        <span>Quantity</span>
        <input
          inputMode="numeric"
          autoComplete="off"
          placeholder="e.g. 10"
          value={qtyText}
          onChange={(e) => setQtyText(e.target.value.trim())}
          aria-invalid={Boolean(hint || fieldError)}
        />
      </label>

      <dl className="summary">
        <div>
          <dt>Execution price (latest close)</dt>
          <dd>{formatINR(stock.price)}</dd>
        </div>
        <div>
          <dt>{side === "BUY" ? "Estimated cost" : "Estimated proceeds"}</dt>
          <dd>{estimate !== null ? formatINR(estimate) : "—"}</dd>
        </div>
        <div>
          <dt>Wallet balance</dt>
          <dd>{balance !== undefined ? formatINR(balance) : "…"}</dd>
        </div>
        <div>
          <dt>You own</dt>
          <dd>
            {owned} share{owned === 1 ? "" : "s"}
          </dd>
        </div>
      </dl>

      {hint && <p className="form-hint">{hint}</p>}
      {error && (
        <p className="form-error" role="alert">
          {fieldError ? `Quantity ${fieldError}.` : error.message}
        </p>
      )}
      {success && (
        <p className="form-success" role="status">
          {success}
        </p>
      )}

      <button className={`btn btn-block ${side === "BUY" ? "btn-buy" : "btn-sell"}`} disabled={!validQuantity || submitting}>
        {submitting ? "Placing order…" : `${side === "BUY" ? "Buy" : "Sell"} ${stock.symbol}`}
      </button>
      <p className="muted small">Market order: it executes immediately at the latest closing price.</p>
    </form>
  );
}
