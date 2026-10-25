import { useState } from "react";
import { Link } from "react-router-dom";
import { getOrders } from "../api/index.js";
import { EmptyState, ErrorMessage, Spinner } from "../components/Feedback.jsx";
import Pagination from "../components/Pagination.jsx";
import { useApi } from "../hooks/useApi.js";
import { useDebouncedValue } from "../hooks/useDebouncedValue.js";
import { formatDateTime, formatINR, formatNumber } from "../utils/format.js";

const PAGE_SIZE = 10;

export default function OrdersPage() {
  const [side, setSide] = useState("");
  const [symbolText, setSymbolText] = useState("");
  const [page, setPage] = useState(1);
  const symbol = useDebouncedValue(symbolText, 300);

  // fetched every time the page is opened, so a trade you just made is always there
  const { data, error, loading, reload } = useApi(
    (signal) => getOrders({ side, symbol, page, page_size: PAGE_SIZE }, signal),
    [side, symbol, page]
  );

  const filtered = Boolean(side || symbol);

  return (
    <section>
      <div className="page-head">
        <h1>Orders</h1>
        <p className="muted">Your trade history, newest first.</p>
      </div>

      <div className="toolbar">
        <label className="field">
          <span>Side</span>
          <select value={side} onChange={(e) => { setSide(e.target.value); setPage(1); }}>
            <option value="">All</option>
            <option value="BUY">Buy</option>
            <option value="SELL">Sell</option>
          </select>
        </label>
        <label className="field">
          <span>Symbol</span>
          <input
            placeholder="e.g. TCS"
            value={symbolText}
            onChange={(e) => { setSymbolText(e.target.value.toUpperCase().replace(/[^A-Z0-9&.-]/g, "")); setPage(1); }}
          />
        </label>
      </div>

      {error ? (
        <ErrorMessage error={error} onRetry={reload} title="Could not load your orders" />
      ) : !data ? (
        <Spinner label="Loading orders…" />
      ) : data.data.length === 0 ? (
        <div className="card">
          {filtered ? (
            <EmptyState title="No orders match these filters" />
          ) : (
            <EmptyState title="You haven't placed any orders yet" actionTo="/market" actionLabel="Go to the market">
              Your buys and sells will show up here.
            </EmptyState>
          )}
        </div>
      ) : (
        <>
          <div className={`table-wrap ${loading ? "is-loading" : ""}`}>
            <table className="table">
              <thead>
                <tr>
                  <th>Date</th>
                  <th>Stock</th>
                  <th>Side</th>
                  <th className="num">Qty</th>
                  <th className="num">Price</th>
                  <th className="num">Total</th>
                </tr>
              </thead>
              <tbody>
                {data.data.map((o) => (
                  <tr key={o.id}>
                    <td>{formatDateTime(o.created_at)}</td>
                    <td>
                      <Link to={`/stocks/${encodeURIComponent(o.symbol)}`} className="symbol-link">
                        {o.symbol}
                      </Link>
                      <div className="muted small">{o.name}</div>
                    </td>
                    <td>
                      <span className={`badge ${o.side === "BUY" ? "badge-buy" : "badge-sell"}`}>{o.side}</span>
                    </td>
                    <td className="num">{formatNumber(o.quantity)}</td>
                    <td className="num">{formatINR(o.price)}</td>
                    <td className="num">{formatINR(o.total_value)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <Pagination pagination={data.pagination} onPageChange={setPage} noun="orders" />
        </>
      )}
    </section>
  );
}
