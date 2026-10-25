import { NavLink, Outlet } from "react-router-dom";
import { useTrading } from "../context/TradingContext.jsx";
import { formatINR } from "../utils/format.js";

export default function Layout() {
  const { portfolio, portfolioError, refreshPortfolio } = useTrading();

  return (
    <div className="app">
      <header className="topbar">
        <div className="topbar-inner">
          <NavLink to="/market" className="brand">
            Mini<span>Trade</span>
          </NavLink>
          <nav className="nav" aria-label="Main">
            <NavLink to="/market">Market</NavLink>
            <NavLink to="/watchlist">Watchlist</NavLink>
            <NavLink to="/portfolio">Portfolio</NavLink>
            <NavLink to="/orders">Orders</NavLink>
          </nav>
          <div className="wallet" aria-live="polite">
            <span className="wallet-label">Wallet</span>
            {portfolioError ? (
              <button className="link-button" onClick={refreshPortfolio}>
                unavailable – retry
              </button>
            ) : (
              <strong>{portfolio ? formatINR(portfolio.wallet_balance) : "…"}</strong>
            )}
          </div>
        </div>
      </header>
      <main className="content">
        <Outlet />
      </main>
      <footer className="footer">Practice trading with virtual money. All prices are sample data.</footer>
    </div>
  );
}
