// Mirrors backend/app/schemas.py — keep in sync.

export const EMPLOYMENT_TYPES = [
  { value: "salaried", label: "Salaried" },
  { value: "self_employed", label: "Self-employed" },
  { value: "professional", label: "Professional" },
  { value: "pensioner", label: "Pensioner" },
] as const;

// Which income question applies, and which BorrowerProfile field it fills, per
// employment type — mirrors backend/app/load_birbal_dataset.py's
// INCOME_BY_EMPLOYMENT_TYPE, which decides the same thing on the data side.
export const INCOME_FIELD_BY_EMPLOYMENT_TYPE = {
  salaried: { field: "net_monthly_salary", label: "Net monthly salary (₹)", placeholder: "eg. 60,000" },
  self_employed: { field: "annual_turnover", label: "Annual business turnover (₹)", placeholder: "eg. 40,00,000" },
  professional: {
    field: "annual_gross_receipts",
    label: "Annual gross receipts (₹)",
    placeholder: "eg. 24,00,000",
  },
  pensioner: { field: "monthly_pension", label: "Monthly pension (₹)", placeholder: "eg. 35,000" },
} as const;

export const DOCUMENT_TYPES = [
  { value: "itr_form16", label: "ITR / Form 16" },
  { value: "itr", label: "ITR" },
  { value: "salary_slip", label: "Salary slip" },
  { value: "cash_income", label: "Cash income" },
  { value: "gst", label: "GST" },
  { value: "business_proof", label: "Business proof" },
  { value: "pension_proof", label: "Pension proof" },
  { value: "bank_statement", label: "Bank statement" },
] as const;

// Which of the extra documents (beyond the always-required bank statement)
// are actually relevant to show for each employment type — matches how the
// real birbal.club site narrows this list too, not just a guess. Kept
// generous per type (e.g. "Cash income" stays available for Pensioners too)
// so nobody's blocked from picking a document they genuinely have.
export const DOCUMENTS_BY_EMPLOYMENT_TYPE: Record<EmploymentType, DocumentType[]> = {
  salaried: ["itr_form16", "salary_slip", "cash_income"],
  self_employed: ["gst", "itr", "business_proof", "cash_income"],
  professional: ["itr", "business_proof", "cash_income"],
  pensioner: ["pension_proof", "cash_income"],
};

export const PROPERTY_TYPES = [
  { value: "standard_urban", label: "Standard urban property" },
  { value: "semi_urban_village", label: "Semi-urban village" },
  { value: "under_construction", label: "Under construction" },
  { value: "others", label: "Others" },
] as const;

export type EmploymentType = (typeof EMPLOYMENT_TYPES)[number]["value"];
export type DocumentType = (typeof DOCUMENT_TYPES)[number]["value"];
export type PropertyType = (typeof PROPERTY_TYPES)[number]["value"];

export interface BorrowerProfile {
  cibil_score: number;
  loan_amount_required: number;
  employment_type: EmploymentType;
  // Only one of these four is ever relevant for a given employment_type — see
  // INCOME_FIELD_BY_EMPLOYMENT_TYPE above — so only that one gets filled in.
  net_monthly_salary?: number;
  annual_turnover?: number;
  annual_gross_receipts?: number;
  monthly_pension?: number;
  // Only meaningful for Pensioner profiles; always sent, harmlessly ignored
  // by every rule that isn't checking for it.
  has_co_borrower: boolean;
  documents_available: DocumentType[];
  property_type: PropertyType;
}

export interface ProductMatch {
  bank_name: string;
  product_name: string;
  interest_rate_pct: number | null;
  interest_rate_range: string | null;
  processing_fee_pct: number | null;
  processing_fee: string | null;
  lender_type: string | null;
  max_eligible_amount: number | null;
  approval_likelihood_tier: "low" | "medium" | "high" | null;
  // Lender relationship/priority standing — null where no bias data has been
  // entered for this bank (see backend/app/database.py's BankBiasFactModel).
  recent_borrowers_processed: number | null;
  relationship_note: string | null;
  score: number;
  reasons: string[];
}

export interface MatchResponse {
  lenders: ProductMatch[];
  meta: {
    products_considered: number;
    products_eligible: number;
  };
}
