import { isNetworkError } from "../api/client";

export function LoadingMessage({ children }) {
  return (
    <p className="state-message">
      <span className="spinner" aria-hidden="true" />
      {children}
    </p>
  );
}

// error: the caught Error/ApiError. onRetry: re-run whatever fetch failed. Per plan.md
// Section 21, a network failure between frontend and backend must show "Connection lost,
// please retry" with a retry option — every screen that calls this with an onRetry gets that
// affordance uniformly, instead of leaving the user stuck with a full page reload.
export function ErrorMessage({ error, children, onRetry }) {
  const isNetwork = error != null && isNetworkError(error);
  const text = children ?? (isNetwork ? "Connection lost, please retry." : error?.message);
  return (
    <p className="state-message error" role="alert">
      {text}
      {onRetry && (
        <>
          {" "}
          <button type="button" className="secondary" onClick={onRetry}>
            Retry
          </button>
        </>
      )}
    </p>
  );
}

export function InfoMessage({ children }) {
  return <p className="state-message">{children}</p>;
}
