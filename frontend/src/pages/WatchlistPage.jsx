import { useState } from "react";
import { EmptyState, ErrorMessage, Spinner } from "../components/Feedback.jsx";
import StockTable from "../components/StockTable.jsx";
import { useTrading } from "../context/TradingContext.jsx";

export default function WatchlistPage() {
  const { watchlist, watchlistLoading, watchlistError, refreshWatchlist, removeFromWatchlist } = useTrading();
  const [removing, setRemoving] = useState(null);
  const [actionError, setActionError] = useState(null);

  async function remove(symbol) {
    setRemoving(symbol);
    setActionError(null);
    try {
      await removeFromWatchlist(symbol);
    } catch (err) {
      setActionError(err);
    } finally {
      setRemoving(null);
    }
  }

  return (
    <section>
      <div className="page-head">
        <h1>Watchlist</h1>
        <p className="muted">Stocks you are keeping an eye on. Add more from a stock's page.</p>
      </div>
      {actionError && <ErrorMessage error={actionError} title="Could not update the watchlist" />}
      {watchlistError ? (
        <ErrorMessage error={watchlistError} onRetry={refreshWatchlist} title="Could not load your watchlist" />
      ) : watchlistLoading && watchlist.length === 0 ? (
        <Spinner label="Loading watchlist…" />
      ) : watchlist.length === 0 ? (
        <div className="card">
          <EmptyState title="Your watchlist is empty" actionTo="/market" actionLabel="Browse the market">
            Open any stock and press “Add to watchlist”.
          </EmptyState>
        </div>
      ) : (
        <StockTable
          stocks={watchlist}
          renderAction={(s) => (
            <button className="btn btn-small" disabled={removing === s.symbol} onClick={() => remove(s.symbol)}>
              {removing === s.symbol ? "Removing…" : "Remove"}
            </button>
          )}
        />
      )}
    </section>
  );
}
