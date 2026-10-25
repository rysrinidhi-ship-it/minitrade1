import { Link } from "react-router-dom";
import Change from "../components/Change.jsx";
import { EmptyState, ErrorMessage, Spinner } from "../components/Feedback.jsx";
import { useTrading } from "../context/TradingContext.jsx";
import { formatINR, formatNumber, formatPct, formatSignedINR, trendClass } from "../utils/format.js";

export default function PortfolioPage() {
  // Shared state: this is the same object the header wallet and the trade form read,
  // so it is already up to date after a trade.
  const { portfolio, portfolioLoading, portfolioError, refreshPortfolio } = useTrading();

  if (portfolioError) return <ErrorMessage error={portfolioError} onRetry={refreshPortfolio} title="Could not load your portfolio" />;
  if (!portfolio) return <Spinner label="Loading portfolio…" />;

  const p = portfolio;
  return (
    <section>
      <div className="page-head">
        <h1>Portfolio</h1>
        <p className="muted">Your cash and holdings, valued at the latest closing prices.</p>
      </div>

      <div className={`cards ${portfolioLoading ? "is-loading" : ""}`}>
        <div className="card metric">
          <span className="metric-label">Wallet balance</span>
          <strong>{formatINR(p.wallet_balance)}</strong>
        </div>
        <div className="card metric">
          <span className="metric-label">Invested</span>
          <strong>{formatINR(p.invested_value)}</strong>
        </div>
        <div className="card metric">
          <span className="metric-label">Current value</span>
          <strong>{formatINR(p.current_value)}</strong>
        </div>
        <div className="card metric">
          <span className="metric-label">Total P&amp;L</span>
          <strong className={trendClass(p.total_pnl)}>{formatSignedINR(p.total_pnl)}</strong>
          <span className={trendClass(p.total_pnl)}>{formatPct(p.total_pnl_pct)}</span>
        </div>
        <div className="card metric">
          <span className="metric-label">Account value (cash + shares)</span>
          <strong>{formatINR(p.account_value)}</strong>
        </div>
      </div>

      <h2>Holdings</h2>
      {p.holdings.length === 0 ? (
        <div className="card">
          <EmptyState title="You don't own any stocks yet" actionTo="/market" actionLabel="Find a stock to buy">
            Your wallet is ready: {formatINR(p.wallet_balance)}.
          </EmptyState>
        </div>
      ) : (
        <div className={`table-wrap ${portfolioLoading ? "is-loading" : ""}`}>
          <table className="table">
            <thead>
              <tr>
                <th>Stock</th>
                <th className="num">Qty</th>
                <th className="num">Avg buy price</th>
                <th className="num">Current price</th>
                <th className="num">Invested</th>
                <th className="num">Current value</th>
                <th className="num">P&amp;L</th>
              </tr>
            </thead>
            <tbody>
              {p.holdings.map((h) => (
                <tr key={h.symbol}>
                  <td>
                    <Link to={`/stocks/${encodeURIComponent(h.symbol)}`} className="symbol-link">
                      {h.symbol}
                    </Link>
                    <div className="muted small">{h.name}</div>
                  </td>
                  <td className="num">{formatNumber(h.quantity)}</td>
                  <td className="num">{formatINR(h.avg_buy_price)}</td>
                  <td className="num">{formatINR(h.current_price)}</td>
                  <td className="num">{formatINR(h.invested)}</td>
                  <td className="num">{formatINR(h.current_value)}</td>
                  <td className="num">
                    <Change change={h.pnl} pct={h.pnl_pct} />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}
