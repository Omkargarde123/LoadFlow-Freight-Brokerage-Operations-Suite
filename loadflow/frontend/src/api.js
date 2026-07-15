// In production (combined deploy) this is unset, so requests go to the same
// origin the app is served from — no CORS, no separate URL to configure.
// In local dev, set VITE_API_URL in .env.development to point at :8000.
const BASE_URL = import.meta.env.VITE_API_URL || "";
const API_PREFIX = "/api";

function getToken() {
  return localStorage.getItem("loadflow_token");
}

async function request(path, { method = "GET", body, auth = true } = {}) {
  const headers = { "Content-Type": "application/json" };
  if (auth) {
    const token = getToken();
    if (token) headers["Authorization"] = `Bearer ${token}`;
  }
  const res = await fetch(`${BASE_URL}${API_PREFIX}${path}`, {
    method,
    headers,
    body: body ? JSON.stringify(body) : undefined,
  });
  let data = null;
  try {
    data = await res.json();
  } catch (e) {
    /* no body */
  }
  if (!res.ok) {
    const message = (data && (data.detail || JSON.stringify(data))) || res.statusText;
    const err = new Error(typeof message === "string" ? message : JSON.stringify(message));
    err.status = res.status;
    throw err;
  }
  return data;
}

export const api = {
  registerOrg: (payload) => request("/auth/register-org", { method: "POST", body: payload, auth: false }),
  registerShipper: (payload) => request("/auth/register-shipper", { method: "POST", body: payload, auth: false }),
  login: (payload) => request("/auth/login", { method: "POST", body: payload, auth: false }),
  me: () => request("/auth/me"),

  permissionCatalog: () => request("/permissions/catalog"),
  listRoles: () => request("/roles"),
  createRole: (payload) => request("/roles", { method: "POST", body: payload }),
  updateRole: (id, payload) => request(`/roles/${id}`, { method: "PUT", body: payload }),
  deleteRole: (id) => request(`/roles/${id}`, { method: "DELETE" }),

  listStaff: () => request("/staff"),
  inviteStaff: (payload) => request("/staff", { method: "POST", body: payload }),
  updateStaff: (id, payload) => request(`/staff/${id}`, { method: "PUT", body: payload }),

  listCarriers: () => request("/compliance/carriers/list"),
  listShippers: () => request("/loads/lookup/shippers"),
  getCompliance: (orgId) => request(`/compliance/${orgId}`),
  upsertCompliance: (orgId, payload) => request(`/compliance/${orgId}`, { method: "PUT", body: payload }),

  listLoads: (params = {}) => {
    const qs = new URLSearchParams(Object.entries(params).filter(([, v]) => v)).toString();
    return request(`/loads${qs ? `?${qs}` : ""}`);
  },
  getLoad: (id) => request(`/loads/${id}`),
  createLoad: (payload) => request("/loads", { method: "POST", body: payload }),
  assignCarrier: (id, payload) => request(`/loads/${id}/assign-carrier`, { method: "POST", body: payload }),
  overrideCompliance: (id) => request(`/loads/${id}/override-compliance`, { method: "POST" }),
  confirmRate: (id, payload) => request(`/loads/${id}/rate-confirmation`, { method: "POST", body: payload }),
  updateStatus: (id, payload) => request(`/loads/${id}/status`, { method: "POST", body: payload }),

  dashboard: () => request("/dashboard"),
  auditLog: () => request("/audit/permission-denied"),

  setToken: (token) => localStorage.setItem("loadflow_token", token),
  clearToken: () => localStorage.removeItem("loadflow_token"),
  getToken,
};
