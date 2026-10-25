import { useCallback, useEffect, useRef, useState } from "react";

/**
 * Custom hook: run an async request and track { data, error, loading }.
 *
 *   const { data, error, loading, reload } = useApi((signal) => getStock(symbol, signal), [symbol]);
 *
 * - re-runs whenever something in `deps` changes (like useEffect)
 * - cancels the previous request if a newer one starts (no out-of-order results)
 * - keeps the OLD data on screen while reloading, so tables don't flash empty
 * - `reload()` runs the request again (used by "Retry" buttons and after a trade)
 */
export function useApi(fetcher, deps) {
  const [state, setState] = useState({ data: null, error: null, loading: true });
  const [tick, setTick] = useState(0);
  const fetcherRef = useRef(fetcher);
  fetcherRef.current = fetcher; // always call the latest closure

  useEffect(() => {
    const controller = new AbortController();
    setState((prev) => ({ ...prev, loading: true, error: null }));
    fetcherRef
      .current(controller.signal)
      .then((data) => setState({ data, error: null, loading: false }))
      .catch((error) => {
        if (error.name === "AbortError") return; // superseded by a newer request / unmounted
        setState((prev) => ({ ...prev, error, loading: false }));
      });
    return () => controller.abort();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [...deps, tick]);

  const reload = useCallback(() => setTick((t) => t + 1), []);
  return { ...state, reload };
}
