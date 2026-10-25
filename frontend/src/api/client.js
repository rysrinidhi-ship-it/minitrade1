// One place that talks HTTP. Everything else in the app calls the functions in api/index.js.

const BASE_URL = (import.meta.env.VITE_API_BASE_URL || "http://localhost:8000/api").replace(/\/$/, "");

/** Error thrown for every failed request, whatever the cause. */
export class ApiError extends Error {
  constructor(message, { status = 0, code = "UNKNOWN", details = null } = {}) {
    super(message);
    this.name = "ApiError";
    this.status = status; // HTTP status, 0 = server not reachable
    this.code = code; // machine readable, e.g. INSUFFICIENT_FUNDS
    this.details = details;
  }
}

function buildUrl(path, params) {
  const query = new URLSearchParams();
  Object.entries(params || {}).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== "") query.set(key, value);
  });
  const qs = query.toString();
  return `${BASE_URL}${path}${qs ? `?${qs}` : ""}`;
}

export async function request(path, { method = "GET", body, params, signal } = {}) {
  let response;
  try {
    response = await fetch(buildUrl(path, params), {
      method,
      signal,
      headers: body !== undefined ? { "Content-Type": "application/json" } : undefined,
      body: body !== undefined ? JSON.stringify(body) : undefined,
    });
  } catch (err) {
    if (err.name === "AbortError") throw err; // a cancelled request is not an error to show
    throw new ApiError("Cannot reach the server. Is the backend running?", { code: "NETWORK_ERROR" });
  }

  if (response.status === 204) return null;

  let payload = null;
  try {
    payload = await response.json();
  } catch {
    /* body was not JSON */
  }

  if (!response.ok) {
    // the backend always answers errors as { error: { code, message, details } }
    const e = payload?.error;
    throw new ApiError(e?.message || `Request failed (${response.status})`, {
      status: response.status,
      code: e?.code,
      details: e?.details,
    });
  }
  return payload;
}
