const API_BASE = (import.meta.env.VITE_API_BASE_URL || "").replace(/\/$/, "");
export const API_BASE_URL = API_BASE;
let csrfToken = "";

type ApiOptions = RequestInit & { body?: BodyInit | null };

async function getCsrfToken() {
  const response = await fetch(`${API_BASE}/api/auth/csrf/`, { credentials: "include" });
  const data = await response.json();
  if (!response.ok) throw new Error(data.detail || "Unable to initialise secure session.");
  csrfToken = data.csrfToken;
  return csrfToken;
}

export async function api<T = any>(path: string, options: ApiOptions = {}): Promise<T> {
  const method = (options.method || "GET").toUpperCase();
  const headers = new Headers(options.headers || {});
  if (options.body && !(options.body instanceof FormData)) headers.set("Content-Type", "application/json");
  if (!["GET", "HEAD", "OPTIONS"].includes(method)) {
    if (!csrfToken) await getCsrfToken();
    headers.set("X-CSRFToken", csrfToken);
  }
  const response = await fetch(`${API_BASE}${path}`, {
    ...options, method, headers, credentials: "include",
  });
  if (response.status === 204) return undefined as T;
  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    const detail = data.detail || Object.entries(data).map(([key, value]) => `${key}: ${Array.isArray(value) ? value.join(", ") : String(value)}`).join(" · ");
    throw new Error(detail || `Request failed (${response.status}).`);
  }
  return data as T;
}

export async function login(username: string, password: string) {
  await getCsrfToken();
  const response = await api<{user: User}>("/api/auth/login/", { method: "POST", body: JSON.stringify({ username, password }) });
  await getCsrfToken(); // Django rotates the CSRF secret on successful login.
  return response;
}
export async function logout() {
  await api("/api/auth/logout/", { method: "POST", body: JSON.stringify({}) });
  csrfToken = "";
}
export type School = { id: number; name: string; code: string; currency: string; role: string };
export type User = { id: number; username: string; name: string; schools: School[] };
