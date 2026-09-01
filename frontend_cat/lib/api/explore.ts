// Mirrors backend_cat/app/explore_schemas.py — keep in sync.

import { apiGet, apiPost } from "./client";

export const FILTER_CATEGORIES = [
  "employment_type",
  "property_type",
  "property_usage",
  "property_stage",
  "property_location",
] as const;

export type FilterCategory = (typeof FILTER_CATEGORIES)[number];

export type CategoryFilters = Record<FilterCategory, string[]>;

// Age/income/obligations are entered fresh every time, never stored — see
// backend_cat/app/explore_schemas.py's ExploreFiltersIn.
export interface ExploreFilters extends CategoryFilters {
  age: number | null;
  monthly_income: number | null;
  obligations: number[];
}

export const EMPTY_FILTERS: ExploreFilters = {
  employment_type: [],
  property_type: [],
  property_usage: [],
  property_stage: [],
  property_location: [],
  age: null,
  monthly_income: null,
  obligations: [],
};

export interface ExploreProduct {
  bank_name: string;
  product_name: string;
  employment_type: string;
  property_type: string[];
  property_usage: string[];
  property_stage: string[];
  property_location: string[];
  bank_foir_pct: number | null;
  customer_foir_pct: number | null;
  foir_pass: boolean | null;
  max_emi: number | null;
  bank_max_tenure_years: number | null;
  final_tenure_years: number | null;
  max_loan_amount: number | null;
  interest_rate_pct: number;
  interest_rate_is_estimated: boolean;
  interest_rate_upper_pct: number | null;
}

export interface FacetOption {
  value: string;
  label: string;
  count: number;
}

export interface ExploreResponse {
  results: ExploreProduct[];
  total: number;
  facets: Record<FilterCategory, FacetOption[]>;
}

export function exploreBanks(filters: ExploreFilters): Promise<ExploreResponse> {
  return apiPost<ExploreResponse, ExploreFilters>("/api/v1/explore/banks", filters);
}

export interface LiveRate {
  bank_name: string;
  rate_pct: number;
}

// Powers the scrolling rate ticker — only banks whose rate was actually
// confirmed against Ambak (see backend_cat/app/explore_api.py's
// live_rates), sorted lowest rate first.
export function fetchLiveRates(): Promise<LiveRate[]> {
  return apiGet<LiveRate[]>("/api/v1/explore/live-rates");
}
