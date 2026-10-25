import { useState } from "react";
import { Link, useParams } from "react-router-dom";
import { getStock } from "../api/index.js";
import Change from "../components/Change.jsx";
import { ErrorMessage, Spinner } from "../components/Feedback.jsx";
import PriceChart from "../components/PriceChart.jsx";
import TradeForm from "../components/TradeForm.jsx";
import { useTrading } from "../context/TradingContext.jsx";
import { useApi } from "../hooks/useApi.js";
import { formatINR, formatNumber } from "../utils/format.js";

export default function StockDetailPage() {
  const { symbol } = useParams();
  const { watchlistSymbols, addToWatchlist, removeFromWatchlist } = useTrading();
  const { data, error, reload } = useApi((signal) => getStock(symbol, signal).then((r) => r.data), [symbol]);
  const [busy, setBusy] = useState(false);
  const [watchError, setWatchError] = useState(null);

  if (error?.status === 404) {
    return (
      <div className="card">
        <div className="state">
          <h3>Stock not found</h3>
          <p>We don't have a stock with the symbol “{symbol}”.</p>
          <Link className="btn" to="/market">
            Back to market
          </Link>
        </div>
      </div>
    );
  }
  if (error) return <ErrorMessage error={error} onRetry={reload} title="Could not load this stock" />;
  // `data` may still hold the previously viewed stock for a moment after the URL changed
  if (!data || data.symbol !== symbol.toUpperCase()) return <Spinner label="Loading stock…" />;

  const stock = data;
  const inWatchlist = watchlistSymbols.has(stock.symbol);
  const last = stock.history[stock.history.length - 1];
  const highs = stock.history.map((d) => d.high);
  const lows = stock.history.map((d) => d.low);

  async function toggleWatchlist() {
    setBusy(true);
    setWatchError(null);
    try {
      if (inWatchlist) await removeFromWatchlist(stock.symbol);
      else await addToWatchlist(stock.symbol);
    } catch (err) {
      setWatchError(err);
    } finally {
      setBusy(false);
    }
  }

  return (
    <section>
      <Link to="/market" className="back-link">
        ← Market
      </Link>

      <div className="stock-head">
        <div>
          <h1>
            {stock.name} <span className="chip">{stock.symbol}</span>
          </h1>
          <p className="muted">{stock.sector}</p>
        </div>
        <div className="stock-price">
          <div className="price">{formatINR(stock.price)}</div>
          <Change change={stock.change} pct={stock.change_pct} />
          <div className="muted small">Close on {stock.as_of}</div>
        </div>
        <div>
          <button className={`btn ${inWatchlist ? "btn-active" : ""}`} onClick={toggleWatchlist} disabled={busy} aria-pressed={inWatchlist}>
            {busy ? "Saving…" : inWatchlist ? "★ In watchlist (remove)" : "☆ Add to watchlist"}
          </button>
          {watchError && (
            <p className="form-error" role="alert">
              {watchError.message}
            </p>
          )}
        </div>
      </div>

      <div className="detail-grid">
        <div className="card">
          <h2>Last {stock.history.length} trading days</h2>
          <PriceChart history={stock.history} />
          <dl className="stats">
            <div><dt>Open</dt><dd>{formatINR(last.open)}</dd></div>
            <div><dt>High</dt><dd>{formatINR(last.high)}</dd></div>
            <div><dt>Low</dt><dd>{formatINR(last.low)}</dd></div>
            <div><dt>Volume</dt><dd>{formatNumber(last.volume)}</dd></div>
            <div><dt>Period high</dt><dd>{formatINR(Math.max(...highs))}</dd></div>
            <div><dt>Period low</dt><dd>{formatINR(Math.min(...lows))}</dd></div>
          </dl>
        </div>
        <TradeForm stock={stock} />
      </div>
    </section>
  );
}
