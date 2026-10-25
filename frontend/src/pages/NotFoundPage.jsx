import { EmptyState } from "../components/Feedback.jsx";

export default function NotFoundPage() {
  return (
    <div className="card">
      <EmptyState title="Page not found" actionTo="/market" actionLabel="Back to the market">
        The page you are looking for doesn't exist.
      </EmptyState>
    </div>
  );
}
