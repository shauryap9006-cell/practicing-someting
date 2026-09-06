/**
 * Shared API configuration for RailTwin-X cockpit pages.
 * Reads the Vite API URL. An empty value keeps same-origin deployments same-origin.
 */
import { getCurrentSession, refreshSession } from '@/mock/auth';

export const API_BASE =
  (import.meta.env.VITE_API_URL || "").replace(/\/$/, "");

/**
 * authFetch - auto-attaches the active session's Bearer token.
 * Throws on non-ok HTTP responses with the backend detail message.
 */
export async function authFetch(
  url: string,
  options: RequestInit = {}
): Promise<Response> {
  const token = getCurrentSession()?.user?.token || null;

  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(options.headers as Record<string, string>),
  };

  if (token) {
    headers["Authorization"] = "Bearer " + token;
  }

  let res = await fetch(url, { ...options, headers });

  if (res.status === 401 && getCurrentSession()?.refreshToken) {
    const refreshed = await refreshSession();
    if (refreshed?.user.token) {
      headers["Authorization"] = "Bearer " + refreshed.user.token;
      res = await fetch(url, { ...options, headers });
    }
  }

  if (!res.ok) {
    let detail = "HTTP " + res.status;
    try {
      const body = await res.json();
      detail = body?.error?.message || body?.detail?.message || body?.detail || body?.message || detail;
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
