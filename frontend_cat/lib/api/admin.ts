// Mirrors backend/app/admin_schemas.py and backend/app/admin_api.py.

import { ApiError } from "./client";
import type { DocumentType, EmploymentType, PropertyType } from "./types";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

export interface AdminProductDetail {
  employment_type: EmploymentType;
  min_cibil: number;
  max_cibil: number;
  min_loan_amount: number;
  max_loan_amount: number;
  income_threshold: number;
  documents_accepted: DocumentType[];
  property_types_accepted: PropertyType[];
  interest_rate_pct: number;
  interest_rate_range: string;
  processing_fee: string;
  lender_type: string;
  co_borrower_required: boolean;
}

export interface AdminProductOut extends AdminProductDetail {
  bank_name: string;
}

export interface AdminBankSummary {
  bank_name: string;
  source: string;
  employment_types: EmploymentType[];
}

export interface AdminBiasIn {
  recent_borrowers_processed: number;
  relationship_note: string;
}

export interface AdminBiasOut extends AdminBiasIn {
  bank_name: string;
}

async function adminRequest<TResponse>(
  path: string,
  token: string,
  options: { method?: string; body?: unknown } = {},
): Promise<TResponse> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    method: options.method ?? "GET",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
    },
    body: options.body !== undefined ? JSON.stringify(options.body) : undefined,
  });

  if (!response.ok) {
    const detail = await response.text();
    throw new ApiError(detail || `Request failed with status ${response.status}`, response.status);
  }
  if (response.status === 204) return undefined as TResponse;
  return response.json() as Promise<TResponse>;
}

export const adminApi = {
  listBanks: (token: string) => adminRequest<AdminBankSummary[]>("/api/v1/admin/banks", token),

  getBankProducts: (token: string, bankName: string) =>
    adminRequest<AdminProductOut[]>(`/api/v1/admin/banks/${encodeURIComponent(bankName)}/products`, token),

  createBankProduct: (token: string, bankName: string, detail: AdminProductDetail) =>
    adminRequest<AdminProductOut>(`/api/v1/admin/banks/${encodeURIComponent(bankName)}/products`, token, {
      method: "POST",
      body: detail,
    }),

  updateBankProduct: (token: string, bankName: string, employmentType: string, detail: AdminProductDetail) =>
    adminRequest<AdminProductOut>(
      `/api/v1/admin/banks/${encodeURIComponent(bankName)}/products/${employmentType}`,
      token,
      { method: "PUT", body: detail },
    ),

  deleteBankProduct: (token: string, bankName: string, employmentType: string) =>
    adminRequest<void>(`/api/v1/admin/banks/${encodeURIComponent(bankName)}/products/${employmentType}`, token, {
      method: "DELETE",
    }),

  deleteBank: (token: string, bankName: string) =>
    adminRequest<void>(`/api/v1/admin/banks/${encodeURIComponent(bankName)}`, token, { method: "DELETE" }),

  listBias: (token: string) => adminRequest<AdminBiasOut[]>("/api/v1/admin/bias", token),

  upsertBias: (token: string, bankName: string, data: AdminBiasIn) =>
    adminRequest<AdminBiasOut>(`/api/v1/admin/bias/${encodeURIComponent(bankName)}`, token, {
      method: "PUT",
      body: data,
    }),

  deleteBias: (token: string, bankName: string) =>
    adminRequest<void>(`/api/v1/admin/bias/${encodeURIComponent(bankName)}`, token, { method: "DELETE" }),
};
