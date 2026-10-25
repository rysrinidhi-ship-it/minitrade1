import { createContext, useCallback, useContext, useMemo } from "react";
import * as api from "../api/index.js";
import { useApi } from "../hooks/useApi.js";

/**
 * Shared state for the whole app: the wallet/portfolio and the watchlist.
 * The header, the stock page's trade form and the Portfolio page all read from here,
 * so after a trade ONE call to refreshPortfolio() updates all of them (no page reload).
 */
const TradingContext = createContext(null);

export function TradingProvider({ children }) {
  const portfolioReq = useApi((signal) => api.getPortfolio(signal).then((r) => r.data), []);
  const watchlistReq = useApi((signal) => api.getWatchlist(signal).then((r) => r.data), []);

  const { reload: refreshPortfolio } = portfolioReq;
  const { reload: refreshWatchlist } = watchlistReq;

  const watchlistSymbols = useMemo(
    () => new Set((watchlistReq.data || []).map((s) => s.symbol)),
    [watchlistReq.data]
  );

  const addToWatchlist = useCallback(
    async (symbol) => {
      try {
        await api.addToWatchlist(symbol);
      } catch (err) {
        if (err.status !== 409) throw err; // 409 = already there: fine, just resync below
      }
      refreshWatchlist();
    },
    [refreshWatchlist]
  );

  const removeFromWatchlist = useCallback(
    async (symbol) => {
      try {
        await api.removeFromWatchlist(symbol);
      } catch (err) {
        if (err.status !== 404) throw err; // 404 = already gone: fine, just resync below
      }
      refreshWatchlist();
    },
    [refreshWatchlist]
  );

  const value = useMemo(
    () => ({
      portfolio: portfolioReq.data,
      portfolioLoading: portfolioReq.loading,
      portfolioError: portfolioReq.error,
      refreshPortfolio,
      watchlist: watchlistReq.data || [],
      watchlistLoading: watchlistReq.loading,
      watchlistError: watchlistReq.error,
      watchlistSymbols,
      refreshWatchlist,
      addToWatchlist,
      removeFromWatchlist,
    }),
    [
      portfolioReq.data, portfolioReq.loading, portfolioReq.error, refreshPortfolio,
      watchlistReq.data, watchlistReq.loading, watchlistReq.error, watchlistSymbols,
      refreshWatchlist, addToWatchlist, removeFromWatchlist,
    ]
  );

  return <TradingContext.Provider value={value}>{children}</TradingContext.Provider>;
}

export function useTrading() {
  const ctx = useContext(TradingContext);
  if (!ctx) throw new Error("useTrading must be used inside <TradingProvider>");
  return ctx;
}
