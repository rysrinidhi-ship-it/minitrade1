import { request } from "./client.js";

// Each function returns the parsed JSON ({ data, pagination? }).
export const getStocks = (params, signal) => request("/stocks", { params, signal });
export const getSectors = (signal) => request("/sectors", { signal });
export const getStock = (symbol, signal) => request(`/stocks/${encodeURIComponent(symbol)}`, { signal });

export const getWatchlist = (signal) => request("/watchlist", { signal });
export const addToWatchlist = (symbol) => request("/watchlist", { method: "POST", body: { symbol } });
export const removeFromWatchlist = (symbol) =>
  request(`/watchlist/${encodeURIComponent(symbol)}`, { method: "DELETE" });

export const placeOrder = ({ symbol, side, quantity }) =>
  request("/orders", { method: "POST", body: { symbol, side, quantity } });
export const getOrders = (params, signal) => request("/orders", { params, signal });

export const getPortfolio = (signal) => request("/portfolio", { signal });
