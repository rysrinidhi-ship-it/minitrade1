import { Link } from "react-router-dom";

export function Spinner({ label = "Loading…" }) {
  return (
    <div className="state" role="status">
      <div className="spinner" aria-hidden="true" />
      <p>{label}</p>
    </div>
  );
}

export function ErrorMessage({ error, onRetry, title = "Something went wrong" }) {
  return (
    <div className="state state-error" role="alert">
      <h3>{title}</h3>
      <p>{error?.message || "Unexpected error"}</p>
      {onRetry && (
        <button className="btn" onClick={onRetry}>
          Try again
        </button>
      )}
    </div>
  );
}

export function EmptyState({ title, children, actionTo, actionLabel }) {
  return (
    <div className="state">
      <h3>{title}</h3>
      {children && <p>{children}</p>}
      {actionTo && (
        <Link className="btn" to={actionTo}>
          {actionLabel}
        </Link>
      )}
    </div>
  );
}
