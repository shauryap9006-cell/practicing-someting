/**
 * Shared API configuration for RailTwin-X cockpit pages.
 * Reads NEXT_PUBLIC_API_URL from environment; falls back to localhost:8000.
 */

export const API_BASE =
  (typeof process !== "undefined" && process.env.NEXT_PUBLIC_API_URL) ||
  "http://localhost:8000";

/**
 * authFetch - auto-attaches Bearer token from localStorage to every request.
 * Throws on non-ok HTTP responses with the backend detail message.
 */
export async function authFetch(
  url: string,
  options: RequestInit = {}
): Promise<Response> {
  const token =
    typeof window !== "undefined"
      ? localStorage.getItem("railtwin_token")
      : null;

  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(options.headers as Record<string, string>),
  };

  if (token) {
    headers["Authorization"] = "Bearer " + token;
  }

  const res = await fetch(url, { ...options, headers });

  if (!res.ok) {
    let detail = "HTTP " + res.status;
    try {
      const body = await res.json();
      detail = body?.detail || body?.message || detail;
    } catch {}
    throw new Error(detail);
  }

  return res;
}

export async function authGet<T>(url: string): Promise<T> {
  const res = await authFetch(url);
  return res.json() as Promise<T>;
}

export async function authPost<T>(url: string, body: unknown): Promise<T> {
  const res = await authFetch(url, { method: "POST", body: JSON.stringify(body) });
  return res.json() as Promise<T>;
}

export async function authPut<T>(url: string, body: unknown): Promise<T> {
  const res = await authFetch(url, { method: "PUT", body: JSON.stringify(body) });
  return res.json() as Promise<T>;
}