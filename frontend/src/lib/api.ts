import type {
  Alert,
  Competitor,
  DashboardData,
  HistorySeries,
  Product,
  ProductDetail,
  RepricingPreview,
  RepricingRecommendation,
  SchedulerStatus,
  TokenResponse,
  User,
} from "../types";
import { clearToken, getToken } from "./auth";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const token = getToken();
  const res = await fetch(path, {
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    ...init,
  });
  if (res.status === 401) {
    clearToken();
    window.dispatchEvent(new Event("pricelens:unauthorized"));
    throw new Error("Sessione scaduta");
  }
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      detail = body.detail ?? JSON.stringify(body);
    } catch {
      // ignore parse errors
    }
    throw new Error(detail);
  }
  if (res.status === 204) {
    return undefined as T;
  }
  return (await res.json()) as T;
}

export const api = {
  // auth
  login: (email: string, password: string) =>
    request<TokenResponse>("/api/auth/login", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    }),
  register: (email: string, password: string) =>
    request<TokenResponse>("/api/auth/register", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    }),
  me: () => request<User>("/api/auth/me"),

  dashboard: () => request<DashboardData>("/api/dashboard"),

  products: (params?: { search?: string; category?: string }) => {
    const q = new URLSearchParams();
    if (params?.search) q.set("search", params.search);
    if (params?.category) q.set("category", params.category);
    const qs = q.toString();
    return request<Product[]>(`/api/products${qs ? `?${qs}` : ""}`);
  },
  product: (id: number) => request<ProductDetail>(`/api/products/${id}`),
  productHistory: (id: number, days = 30) =>
    request<HistorySeries[]>(`/api/products/${id}/history?days=${days}`),
  createProduct: (payload: Partial<Product>) =>
    request<Product>("/api/products", { method: "POST", body: JSON.stringify(payload) }),
  updateProduct: (id: number, payload: Partial<Product>) =>
    request<Product>(`/api/products/${id}`, { method: "PATCH", body: JSON.stringify(payload) }),
  deleteProduct: (id: number) =>
    request<void>(`/api/products/${id}`, { method: "DELETE" }),
  categories: () => request<string[]>("/api/products/categories"),

  competitors: () => request<Competitor[]>("/api/competitors"),
  createCompetitor: (payload: Partial<Competitor>) =>
    request<Competitor>("/api/competitors", { method: "POST", body: JSON.stringify(payload) }),
  updateCompetitor: (id: number, payload: Partial<Competitor>) =>
    request<Competitor>(`/api/competitors/${id}`, { method: "PATCH", body: JSON.stringify(payload) }),
  deleteCompetitor: (id: number) =>
    request<void>(`/api/competitors/${id}`, { method: "DELETE" }),

  alerts: (params?: { unread?: boolean; severity?: string }) => {
    const q = new URLSearchParams();
    if (params?.unread !== undefined) q.set("unread", String(params.unread));
    if (params?.severity) q.set("severity", params.severity);
    const qs = q.toString();
    return request<Alert[]>(`/api/alerts${qs ? `?${qs}` : ""}`);
  },
  alertCounts: () =>
    request<{ total: number; unread: number; critical_unread: number }>("/api/alerts/counts"),
  markAlertRead: (id: number) => request<Alert>(`/api/alerts/${id}/read`, { method: "POST" }),
  markAllRead: () => request<{ marked_read: number }>("/api/alerts/read-all", { method: "POST" }),

  repricingPreview: () => request<RepricingPreview>("/api/repricing/preview"),
  applyRepricing: (product_id: number, suggested_price: number) =>
    request<RepricingRecommendation>("/api/repricing/apply", {
      method: "POST",
      body: JSON.stringify({ product_id, suggested_price }),
    }),

  collect: () =>
    request<{ collected: number; alerts_created: number; errors: number }>("/api/collect", {
      method: "POST",
    }),

  schedulerStatus: () => request<SchedulerStatus>("/api/scheduler/status"),

  exportProductsUrl: (format: "csv" | "xlsx") => `/api/export/products?format=${format}`,
  exportAlertsUrl: (format: "csv" | "xlsx") => `/api/export/alerts?format=${format}`,
  exportHistoryUrl: (productId: number, format: "csv" | "xlsx") =>
    `/api/export/history/${productId}?format=${format}`,
};

export function downloadExport(path: string) {
  const token = getToken();
  fetch(path, { headers: { Authorization: `Bearer ${token ?? ""}` } })
    .then((r) => {
      if (!r.ok) throw new Error("Export fallito");
      return r.blob();
    })
    .then((blob) => {
      const url = URL.createObjectURL(blob);
      const el = document.createElement("a");
      el.href = url;
      el.download = path.includes("xlsx") ? "export.xlsx" : "export.csv";
      document.body.appendChild(el);
      el.click();
      el.remove();
      URL.revokeObjectURL(url);
    })
    .catch((e) => alert((e as Error).message));
}
