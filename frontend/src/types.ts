export type Strategy = "match_min" | "undercut" | "margin_protected" | "premium";

export interface Product {
  id: number;
  sku: string;
  name: string;
  brand: string;
  category: string;
  ean: string | null;
  image_url: string | null;
  cost_price: number;
  current_price: number;
  msrp: number | null;
  map_price: number | null;
  currency: string;
  strategy: Strategy;
  min_margin_pct: number;
  active: boolean;
  created_at: string;
  updated_at: string;
  competitors_tracked: number;
  min_price: number | null;
  max_price: number | null;
  avg_price: number | null;
  position: number | null;
  price_index: number | null;
  open_alerts: number;
  last_change_pct: number | null;
  recommendation: RepricingRecommendation | null;
}

export interface CompetitorPrice {
  competitor_id: number;
  competitor_name: string;
  domain: string;
  price: number | null;
  currency: string;
  stock_status: string;
  url: string | null;
  captured_at: string | null;
  change_pct: number | null;
}

export interface ProductDetail extends Product {
  competitors: CompetitorPrice[];
}

export interface Competitor {
  id: number;
  name: string;
  domain: string;
  type: "retailer" | "marketplace";
  currency: string;
  active: boolean;
  price_source_type: "simulated" | "url";
  price_source_config: Record<string, unknown>;
  created_at: string;
  products_tracked: number;
}

export interface Alert {
  id: number;
  product_id: number;
  competitor_id: number | null;
  type: string;
  severity: "critical" | "warning" | "info";
  message: string;
  read: boolean;
  created_at: string;
  product_name: string | null;
  competitor_name: string | null;
}

export interface RepricingRecommendation {
  product_id: number;
  sku: string;
  name: string;
  current_price: number;
  suggested_price: number;
  margin_pct: number;
  delta_pct: number;
  rationale: string;
  new_position: number | null;
  floor: number | null;
  ceiling: number | null;
}

export interface RepricingPreview {
  recommendations: RepricingRecommendation[];
  total_potential_margin_impact: number | null;
}

export interface User {
  id: number;
  email: string;
  created_at: string;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
  user: User;
}

export interface SchedulerStatus {
  enabled: boolean;
  interval_seconds: number;
  running: boolean;
  last_run: string | null;
  last_error: string | null;
  last_result: {
    collected: number;
    alerts_created: number;
    skipped: number;
    errors: number;
  } | null;
}

export interface HistoryPoint {
  captured_at: string;
  price: number | null;
}

export interface HistorySeries {
  competitor_id: number;
  competitor_name: string;
  domain: string;
  points: HistoryPoint[];
}

export interface DashboardData {
  kpis: {
    products: number;
    competitors: number;
    open_alerts: number;
    critical_alerts: number;
    points_today: number;
    avg_price_index: number | null;
  };
  top_movers: Array<{
    product_id: number;
    sku: string;
    name: string;
    brand: string;
    category: string;
    current_price: number;
    change_pct: number | null;
    position: number | null;
    price_index: number | null;
  }>;
  price_index_distribution: Array<{
    product_id: number;
    name: string;
    sku: string;
    price_index: number | null;
  }>;
  recent_alerts: Alert[];
}
