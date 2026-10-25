import { Link } from "react-router-dom";
import { formatINR } from "../utils/format.js";
import Change from "./Change.jsx";

const COLUMNS = [
  { key: "symbol", label: "Symbol", numeric: false },
  { key: "name", label: "Company", numeric: false },
  { key: "sector", label: "Sector", numeric: false },
  { key: "price", label: "Last price", numeric: true },
  { key: "change_pct", label: "Day change", numeric: true },
];

/**
 * Table of stocks. When `sort`/`order`/`onSort` are given the headers become sort buttons.
 * `renderAction(stock)` can add a last column (e.g. a "Remove" button on the watchlist page).
 */
export default function StockTable({ stocks, sort, order, onSort, watchlistSymbols, renderAction, dimmed }) {
  const sortable = Boolean(onSort);
  return (
    <div className={`table-wrap ${dimmed ? "is-loading" : ""}`}>
      <table className="table">
        <thead>
          <tr>
            {COLUMNS.map((col) => {
              const active = sortable && sort === col.key;
              return (
                <th
                  key={col.key}
                  className={col.numeric ? "num" : ""}
                  aria-sort={active ? (order === "asc" ? "ascending" : "descending") : "none"}
                >
                  {sortable ? (
                    <button className="th-button" onClick={() => onSort(col.key)}>
                      {col.label}
                      <span className="sort-icon" aria-hidden="true">
                        {active ? (order === "asc" ? "▲" : "▼") : "↕"}
                      </span>
                    </button>
                  ) : (
                    col.label
                  )}
                </th>
              );
            })}
            {renderAction && <th aria-label="Actions" />}
          </tr>
        </thead>
        <tbody>
          {stocks.map((s) => (
            <tr key={s.symbol}>
              <td>
                <Link to={`/stocks/${encodeURIComponent(s.symbol)}`} className="symbol-link">
                  {watchlistSymbols?.has(s.symbol) && (
                    <span className="star" title="In your watchlist" aria-label="In your watchlist">
                      ★
                    </span>
                  )}
                  {s.symbol}
                </Link>
              </td>
              <td>{s.name}</td>
              <td>
                <span className="chip">{s.sector}</span>
              </td>
              <td className="num">{formatINR(s.price)}</td>
              <td className="num">
                <Change change={s.change} pct={s.change_pct} />
              </td>
              {renderAction && <td className="num">{renderAction(s)}</td>}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
