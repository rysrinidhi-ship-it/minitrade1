import { Navigate, Route, Routes } from "react-router-dom";
import { TradingProvider } from "./context/TradingContext.jsx";
import Layout from "./components/Layout.jsx";
import MarketPage from "./pages/MarketPage.jsx";
import StockDetailPage from "./pages/StockDetailPage.jsx";
import WatchlistPage from "./pages/WatchlistPage.jsx";
import PortfolioPage from "./pages/PortfolioPage.jsx";
import OrdersPage from "./pages/OrdersPage.jsx";
import NotFoundPage from "./pages/NotFoundPage.jsx";

export default function App() {
  return (
    <TradingProvider>
      <Routes>
        <Route element={<Layout />}>
          <Route path="/" element={<Navigate to="/market" replace />} />
          <Route path="/market" element={<MarketPage />} />
          <Route path="/stocks/:symbol" element={<StockDetailPage />} />
          <Route path="/watchlist" element={<WatchlistPage />} />
          <Route path="/portfolio" element={<PortfolioPage />} />
          <Route path="/orders" element={<OrdersPage />} />
          <Route path="*" element={<NotFoundPage />} />
        </Route>
      </Routes>
    </TradingProvider>
  );
}
