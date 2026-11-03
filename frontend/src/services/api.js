const cookie = (n) => document.cookie.split("; ").find((c) => c.startsWith(n + "="))?.split("=")[1] || "";

export class ApiError extends Error {
  constructor(status, code, message) { super(message); this.status = status; this.code = code; }
}

async function raw(path, { method = "GET", body } = {}) {
  const headers = {};
  if (body !== undefined) headers["Content-Type"] = "application/json";
  if (method !== "GET") headers["X-CSRF-Token"] = cookie("csrf_token");
  return fetch("/api/v1" + path, { method, headers, credentials: "include", body: body !== undefined ? JSON.stringify(body) : undefined });
}

export async function api(path, opts = {}) {
  let r = await raw(path, opts);
  if (r.status === 401 && !path.startsWith("/auth/")) {
    const rf = await raw("/auth/refresh", { method: "POST" });
    if (rf.ok) r = await raw(path, opts);
  }
  if (r.status === 204) return null;
  const ct = r.headers.get("content-type") || "";
  const data = ct.includes("json") ? await r.json() : null;
  if (!r.ok) {
    const e = data?.error;
    const detail = Array.isArray(data?.detail) ? data.detail.map((d) => `${d.loc?.slice(1).join(".")}: ${d.msg}`).join("; ") : null;
    throw new ApiError(r.status, e?.code || "error", e?.message || detail || `Request failed (${r.status})`);
  }
  return data;
}
export const get = (p) => api(p);
export const post = (p, body = {}) => api(p, { method: "POST", body });
export const patch = (p, body) => api(p, { method: "PATCH", body });
export const del = (p) => api(p, { method: "DELETE" });
