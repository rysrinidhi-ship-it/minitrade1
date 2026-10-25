import { useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { getSectors, getStocks } from "../api/index.js";
import { EmptyState, ErrorMessage, Spinner } from "../components/Feedback.jsx";
import Pagination from "../components/Pagination.jsx";
import StockTable from "../components/StockTable.jsx";
import { useTrading } from "../context/TradingContext.jsx";
import { useApi } from "../hooks/useApi.js";
import { useDebouncedValue } from "../hooks/useDebouncedValue.js";

const PAGE_SIZE = 10;
const NUMERIC_COLUMNS = ["price", "change_pct"];

export default function MarketPage() {
  // Filters live in the URL (?q=&sector=&sort=&order=&page=) so a refresh or "back" keeps them.
  const [params, setParams] = useSearchParams();
  const q = params.get("q") ?? "";
  const sector = params.get("sector") ?? "";
  const sort = params.get("sort") ?? "symbol";
  const order = params.get("order") ?? "asc";
  const page = Math.max(1, parseInt(params.get("page") ?? "1", 10) || 1);

  const { watchlistSymbols } = useTrading();

  function updateParams(changes) {
    setParams(
      (prev) => {
        const next = new URLSearchParams(prev);
        Object.entries(changes).forEach(([key, value]) => {
          if (value === null || value === "") next.delete(key);
          else next.set(key, String(value));
        });
        return next;
      },
      { replace: true }
    );
  }

  // The text box updates instantly; the URL (and therefore the request) only after typing pauses.
  const [searchText, setSearchText] = useState(q);
  const debouncedSearch = useDebouncedValue(searchText.trim(), 300);
  useEffect(() => {
    if (debouncedSearch !== q) updateParams({ q: debouncedSearch, page: null });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [debouncedSearch]);

  const sectorsReq = useApi((signal) => getSectors(signal).then((r) => r.data), []);
  const stocksReq = useApi(
    (signal) => getStocks({ search: q, sector, sort, order, page, page_size: PAGE_SIZE }, signal),
    [q, sector, sort, order, page]
  );

  function handleSort(column) {
    if (column === sort) updateParams({ order: order === "asc" ? "desc" : "asc", page: null });
    else updateParams({ sort: column, order: NUMERIC_COLUMNS.includes(column) ? "desc" : "asc", page: null });
  }

  function clearFilters() {
    setSearchText("");
    setParams({}, { replace: true });
  }

  const hasFilters = Boolean(q || sector);
  const result = stocksReq.data;

  return (
    <section>
      <div className="page-head">
        <h1>Market</h1>
        <p className="muted">Browse stocks, open one to see its 30-day chart and trade it.</p>
      </div>

      <div className="toolbar">
        <label className="field grow">
          <span>Search</span>
          <input
            type="search"
            placeholder="Symbol or company name"
            value={searchText}
            onChange={(e) => setSearchText(e.target.value)}
          />
        </label>
        <label className="field">
          <span>Sector</span>
          <select value={sector} onChange={(e) => updateParams({ sector: e.target.value, page: null })}>
            <option value="">All sectors</option>
            {(sectorsReq.data || []).map((s) => (
              <option key={s} value={s}>
                {s}
              </option>
            ))}
          </select>
        </label>
        <label className="field">
          <span>Sort by</span>
          <select
            value={sort}
            onChange={(e) => updateParams({ sort: e.target.value, order: NUMERIC_COLUMNS.includes(e.target.value) ? "desc" : "asc", page: null })}
          >
            <option value="symbol">Symbol</option>
            <option value="name">Company</option>
            <option value="sector">Sector</option>
            <option value="price">Price</option>
            <option value="change_pct">Day change %</option>
          </select>
        </label>
        <button className="btn" onClick={() => updateParams({ order: order === "asc" ? "desc" : "asc", page: null })} aria-label="Toggle sort direction">
          {order === "asc" ? "Ascending ▲" : "Descending ▼"}
        </button>
      </div>

      {stocksReq.error ? (
        <ErrorMessage error={stocksReq.error} onRetry={stocksReq.reload} title="Could not load stocks" />
      ) : !result ? (
        <Spinner label="Loading stocks…" />
      ) : result.data.length === 0 ? (
        <div className="card">
          <EmptyState title="No stocks match your filters">
            {hasFilters ? "Try a different search or sector." : "There are no stocks to show yet."}
          </EmptyState>
          {hasFilters && (
            <p className="center">
              <button className="btn" onClick={clearFilters}>
                Clear filters
              </button>
            </p>
          )}
        </div>
      ) : (
        <>
          <StockTable
            stocks={result.data}
            sort={sort}
            order={order}
            onSort={handleSort}
            watchlistSymbols={watchlistSymbols}
            dimmed={stocksReq.loading}
          />
          <Pagination pagination={result.pagination} onPageChange={(p) => updateParams({ page: p })} noun="stocks" />
        </>
      )}
    </section>
  );
}
