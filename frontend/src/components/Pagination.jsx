export default function Pagination({ pagination, onPageChange, noun = "items" }) {
  if (!pagination) return null;
  const { page, page_size, total, total_pages } = pagination;
  const from = total === 0 ? 0 : (page - 1) * page_size + 1;
  const to = Math.min(page * page_size, total);
  return (
    <nav className="pagination" aria-label="Pagination">
      <span>
        {from}–{to} of {total} {noun}
      </span>
      <div className="pagination-buttons">
        <button className="btn btn-small" onClick={() => onPageChange(page - 1)} disabled={page <= 1}>
          ← Previous
        </button>
        <span className="pagination-page">
          Page {page} of {total_pages}
        </span>
        <button className="btn btn-small" onClick={() => onPageChange(page + 1)} disabled={page >= total_pages}>
          Next →
        </button>
      </div>
    </nav>
  );
}
