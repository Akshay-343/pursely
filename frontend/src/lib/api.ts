const BASE = "/api/v1";
const K = { a: "mt_access", r: "mt_refresh" };

export const tokens = {
  get: () => localStorage.getItem(K.a),
  set: (a: string, r: string) => { localStorage.setItem(K.a, a); localStorage.setItem(K.r, r); },
  clear: () => { localStorage.removeItem(K.a); localStorage.removeItem(K.r); },
};

let refreshing: Promise<boolean> | null = null;
async function refresh(): Promise<boolean> {
  const r = localStorage.getItem(K.r);
  if (!r) return false;
  refreshing ??= fetch(`${BASE}/auth/refresh`, {
    method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ refresh_token: r }),
  }).then(async (res) => {
    if (!res.ok) return false;
    const d = await res.json();
    tokens.set(d.access_token, d.refresh_token);
    return true;
  }).finally(() => { refreshing = null; });
  return refreshing;
}

export class ApiError extends Error {
  constructor(public status: number, message: string) { super(message); }
}

function errMsg(body: any, status: number) {
  const d = body?.detail;
  if (typeof d === "string") return d;
  if (Array.isArray(d)) return d.map((e) => `${(e.loc ?? []).slice(1).join(".")}: ${e.msg}`).join("; ");
  if (d?.errors) return d.errors.join("; ");
  return `Request failed (${status})`;
}

export async function api<T = any>(path: string, opts: { method?: string; body?: unknown; form?: FormData } = {}): Promise<T> {
  const go = () => fetch(BASE + path, {
    method: opts.method ?? (opts.body || opts.form ? "POST" : "GET"),
    headers: {
      ...(opts.body ? { "Content-Type": "application/json" } : {}),
      ...(tokens.get() ? { Authorization: `Bearer ${tokens.get()}` } : {}),
    },
    body: opts.form ?? (opts.body ? JSON.stringify(opts.body) : undefined),
  });
  let res = await go();
  if (res.status === 401 && !path.startsWith("/auth/") && (await refresh())) res = await go();
  if (res.status === 401 && !path.startsWith("/auth/login")) { tokens.clear(); window.dispatchEvent(new Event("mt-logout")); }
  if (res.status === 204) return undefined as T;
  const body = await res.json().catch(() => null);
  if (!res.ok) throw new ApiError(res.status, errMsg(body, res.status));
  return body as T;
}

export async function download(path: string, filename: string) {
  const res = await fetch(BASE + path, { headers: { Authorization: `Bearer ${tokens.get()}` } });
  const url = URL.createObjectURL(await res.blob());
  Object.assign(document.createElement("a"), { href: url, download: filename }).click();
  URL.revokeObjectURL(url);
}

export async function login(email: string, password: string) {
  const res = await fetch(`${BASE}/auth/login`, {
    method: "POST", headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body: new URLSearchParams({ username: email, password }),
  });
  const body = await res.json().catch(() => null);
  if (!res.ok) throw new ApiError(res.status, errMsg(body, res.status));
  tokens.set(body.access_token, body.refresh_token);
}

export async function register(email: string, password: string, currency: string) {
  const body = await api("/auth/register", { body: { email, password, default_currency: currency } });
  tokens.set(body.access_token, body.refresh_token);
}

export type Category = { id: number; name: string; kind: "expense" | "income"; color: string; icon?: string | null };
export type Account = { id: number; name: string; type: string; currency: string; opening_balance: string };
export type Tx = {
  id: number; amount: string; kind: "expense" | "income"; date: string; note: string | null; tags: string[];
  category_id: number | null; account_id: number | null; category?: Category | null; account?: Account | null;
};
export type Sub = {
  id: number; name: string; amount: string; currency: string; cycle: string; next_billing_date: string;
  category_id: number | null; account_id: number | null; status: string; remind_days_before: number;
  auto_post: boolean; notes: string | null;
};
export type User = { id: number; email: string; default_currency: string; email_reminders: boolean; has_password: boolean; google_linked: boolean };
export type Attachment = { id: number; transaction_id: number; filename: string; content_type: string; size: number };

export async function fetchBlobUrl(path: string): Promise<string> {
  const res = await fetch(BASE + path, { headers: { Authorization: `Bearer ${tokens.get()}` } });
  if (!res.ok) throw new ApiError(res.status, "Could not load file");
  return URL.createObjectURL(await res.blob());
}

export type AuthConfig = { google_client_id: string; email_enabled: boolean; demo: boolean };
export const authConfig = () => api<AuthConfig>("/auth/config");

export async function googleLogin(credential: string) {
  const body = await api("/auth/google", { body: { credential } });
  tokens.set(body.access_token, body.refresh_token);
}
export async function demoLogin() {
  const body = await api("/auth/demo", { method: "POST" });
  tokens.set(body.access_token, body.refresh_token);
}
export const forgotPassword = (email: string) => api<{ detail: string }>("/auth/forgot-password", { body: { email } });
export const resetPassword = (token: string, password: string) => api("/auth/reset-password", { body: { token, password } });
