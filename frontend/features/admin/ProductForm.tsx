"use client";

import { useState } from "react";

import { errorMessage } from "@/lib/api/client";
import {
  DOCUMENT_TYPES,
  DOCUMENTS_BY_EMPLOYMENT_TYPE,
  EMPLOYMENT_TYPES,
  INCOME_FIELD_BY_EMPLOYMENT_TYPE,
  PROPERTY_TYPES,
} from "@/lib/api/types";
import type { AdminProductDetail } from "@/lib/api/admin";

// While the form is being filled out, the employment type and every numeric
// field can be genuinely empty ("") rather than pre-filled with a fake
// number — showing e.g. "Salaried, CIBIL 700-900" by default made a blank
// "add a new employment type" form look like it was already showing real
// data for an existing entry. Only once every field has a real value can it
// become an actual AdminProductDetail for submission. The two interest-rate
// fields it stores here (min/max) aren't part of AdminProductDetail at all —
// see minRate/maxRate below for why.
type Draft = Omit<
  {
    [K in keyof AdminProductDetail]: AdminProductDetail[K] extends number
      ? number | ""
      : K extends "employment_type"
        ? AdminProductDetail[K] | ""
        : AdminProductDetail[K];
  },
  "interest_rate_pct" | "interest_rate_range"
>;

const EMPTY: Draft = {
  employment_type: "",
  min_cibil: "",
  max_cibil: "",
  min_loan_amount: "",
  max_loan_amount: "",
  income_threshold: "",
  documents_accepted: [],
  property_types_accepted: [],
  processing_fee: "",
  lender_type: "",
  co_borrower_required: false,
};

// The database only stores one rate (interest_rate_pct, the "starting from"
// rate used for ranking — lower ranks higher) plus a free-text display
// string. Asking the admin to type both a number AND a matching string like
// "7.25%-9.5%" is error-prone busywork, so the form instead asks for a
// minimum and maximum and derives both stored fields from that pair.
function parseRateRange(range: string, fallback: number): { min: number | ""; max: number | "" } {
  const matches = range.match(/\d+(\.\d+)?/g);
  if (matches && matches.length >= 2) {
    return { min: Number(matches[0]), max: Number(matches[1]) };
  }
  if (matches && matches.length === 1) {
    return { min: Number(matches[0]), max: Number(matches[0]) };
  }
  return { min: fallback, max: fallback };
}

export function ProductForm({
  initial,
  lockEmploymentType,
  employmentTypeOptions,
  onSubmit,
  onCancel,
  submitLabel,
}: {
  initial?: AdminProductDetail;
  lockEmploymentType?: boolean;
  // Restricts the dropdown to employment types this bank doesn't already
  // have a product for — so it's not possible to even pick a type that
  // already exists and get confused about which one you're editing.
  employmentTypeOptions?: readonly { value: string; label: string }[];
  onSubmit: (detail: AdminProductDetail) => Promise<void>;
  onCancel: () => void;
  submitLabel: string;
}) {
  const [detail, setDetail] = useState<Draft>(initial ?? EMPTY);
  const initialRates = initial ? parseRateRange(initial.interest_rate_range, initial.interest_rate_pct) : null;
  const [minRate, setMinRate] = useState<number | "">(initialRates?.min ?? "");
  const [maxRate, setMaxRate] = useState<number | "">(initialRates?.max ?? "");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const options = employmentTypeOptions ?? EMPLOYMENT_TYPES;
  const income = detail.employment_type ? INCOME_FIELD_BY_EMPLOYMENT_TYPE[detail.employment_type] : null;
  // Which extra documents make sense to offer depends on employment type —
  // same mapping the borrower-facing form uses. Bank statement isn't in this
  // list at all: every lender requires it, so it's shown as a fixed,
  // always-on item below rather than a real choice.
  const relevantDocs: readonly string[] = detail.employment_type
    ? DOCUMENTS_BY_EMPLOYMENT_TYPE[detail.employment_type]
    : [];
  const documentOptions = DOCUMENT_TYPES.filter((d) => d.value !== "bank_statement" && relevantDocs.includes(d.value));

  function toggle(list: string[], value: string): string[] {
    return list.includes(value) ? list.filter((v) => v !== value) : [...list, value];
  }

  function handleEmploymentTypeChange(value: string) {
    const employmentType = value as AdminProductDetail["employment_type"] | "";
    const stillValidDocs = employmentType
      ? DOCUMENTS_BY_EMPLOYMENT_TYPE[employmentType]
      : ([] as readonly string[]);
    setDetail({
      ...detail,
      employment_type: employmentType,
      documents_accepted: detail.documents_accepted.filter((d) =>
        stillValidDocs.includes(d),
      ) as AdminProductDetail["documents_accepted"],
    });
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (detail.employment_type === "") {
      setError("Select an employment type.");
      return;
    }
    if (
      detail.min_cibil === "" ||
      detail.max_cibil === "" ||
      detail.min_loan_amount === "" ||
      detail.max_loan_amount === "" ||
      detail.income_threshold === "" ||
      minRate === "" ||
      maxRate === ""
    ) {
      setError("Fill in every field.");
      return;
    }
    if (minRate > maxRate) {
      setError("Minimum interest rate can't be higher than the maximum.");
      return;
    }
    if (detail.documents_accepted.length === 0) {
      setError("Pick at least one document.");
      return;
    }
    if (detail.property_types_accepted.length === 0) {
      setError("Pick at least one property type.");
      return;
    }
    setError(null);
    setSaving(true);
    try {
      const interest_rate_range = minRate === maxRate ? `${minRate}%` : `${minRate}%-${maxRate}%`;
      await onSubmit({ ...detail, interest_rate_pct: minRate, interest_rate_range } as AdminProductDetail);
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setSaving(false);
    }
  }

  return (
    <form onSubmit={handleSubmit} className="flex flex-col gap-5 rounded-2xl border border-zinc-200 bg-white p-6 shadow-sm dark:border-zinc-800 dark:bg-zinc-900">
      <div className="flex flex-col gap-1.5">
        <label className="text-sm font-medium text-zinc-700 dark:text-zinc-300">Employment type</label>
        <select
          disabled={lockEmploymentType}
          value={detail.employment_type}
          onChange={(e) => handleEmploymentTypeChange(e.target.value)}
          className="rounded-lg border border-zinc-300 px-3 py-2 text-sm disabled:bg-zinc-100 dark:border-zinc-700 dark:bg-zinc-950 dark:disabled:bg-zinc-800"
        >
          <option value="" disabled>
            Select employment type
          </option>
          {options.map((o) => (
            <option key={o.value} value={o.value}>
              {o.label}
            </option>
          ))}
        </select>
      </div>

      {detail.employment_type === "pensioner" && (
        <label className="flex items-center gap-2 text-sm text-zinc-700 dark:text-zinc-300">
          <input
            type="checkbox"
            checked={detail.co_borrower_required}
            onChange={(e) => setDetail({ ...detail, co_borrower_required: e.target.checked })}
          />
          Requires a co-borrower
        </label>
      )}

      <div className="grid grid-cols-2 gap-4">
        <div className="flex flex-col gap-1.5">
          <label className="text-sm font-medium text-zinc-700 dark:text-zinc-300">Minimum CIBIL</label>
          <input
            type="number"
            required
            placeholder="e.g. 700"
            value={detail.min_cibil}
            onChange={(e) => setDetail({ ...detail, min_cibil: e.target.value === "" ? "" : Number(e.target.value) })}
            className="rounded-lg border border-zinc-300 px-3 py-2 text-sm dark:border-zinc-700 dark:bg-zinc-950"
          />
        </div>
        <div className="flex flex-col gap-1.5">
          <label className="text-sm font-medium text-zinc-700 dark:text-zinc-300">Maximum CIBIL</label>
          <input
            type="number"
            required
            placeholder="e.g. 900"
            value={detail.max_cibil}
            onChange={(e) => setDetail({ ...detail, max_cibil: e.target.value === "" ? "" : Number(e.target.value) })}
            className="rounded-lg border border-zinc-300 px-3 py-2 text-sm dark:border-zinc-700 dark:bg-zinc-950"
          />
        </div>
      </div>

      <div className="grid grid-cols-2 gap-4">
        <div className="flex flex-col gap-1.5">
          <label className="text-sm font-medium text-zinc-700 dark:text-zinc-300">Minimum loan amount (₹)</label>
          <input
            type="number"
            required
            placeholder="e.g. 300000"
            value={detail.min_loan_amount}
            onChange={(e) => setDetail({ ...detail, min_loan_amount: e.target.value === "" ? "" : Number(e.target.value) })}
            className="rounded-lg border border-zinc-300 px-3 py-2 text-sm dark:border-zinc-700 dark:bg-zinc-950"
          />
        </div>
        <div className="flex flex-col gap-1.5">
          <label className="text-sm font-medium text-zinc-700 dark:text-zinc-300">Maximum loan amount (₹)</label>
          <input
            type="number"
            required
            placeholder="e.g. 10000000"
            value={detail.max_loan_amount}
            onChange={(e) => setDetail({ ...detail, max_loan_amount: e.target.value === "" ? "" : Number(e.target.value) })}
            className="rounded-lg border border-zinc-300 px-3 py-2 text-sm dark:border-zinc-700 dark:bg-zinc-950"
          />
        </div>
      </div>

      <div className="flex flex-col gap-1.5">
        <label className="text-sm font-medium text-zinc-700 dark:text-zinc-300">
          {income ? `Minimum ${income.label.replace(" (₹)", "")} required (₹)` : "Minimum income required (₹)"}
        </label>
        <input
          type="number"
          required
          placeholder={income ? income.placeholder.replace("eg. ", "e.g. ") : "Select an employment type first"}
          value={detail.income_threshold}
          onChange={(e) => setDetail({ ...detail, income_threshold: e.target.value === "" ? "" : Number(e.target.value) })}
          className="rounded-lg border border-zinc-300 px-3 py-2 text-sm dark:border-zinc-700 dark:bg-zinc-950"
        />
      </div>

      <div className="flex flex-col gap-1.5">
        <span className="text-sm font-medium text-zinc-700 dark:text-zinc-300">Documents accepted</span>
        <div className="flex flex-wrap gap-2">
          <span className="rounded-full border border-emerald-600 bg-emerald-50 px-3 py-1.5 text-xs font-medium text-emerald-700 dark:border-emerald-700 dark:bg-emerald-950/40 dark:text-emerald-300">
            Bank statement · always required
          </span>
          {!detail.employment_type && (
            <span className="px-1 py-1.5 text-xs text-zinc-400">Select an employment type to see more options.</span>
          )}
          {documentOptions.map((doc) => (
            <button
              type="button"
              key={doc.value}
              onClick={() => setDetail({ ...detail, documents_accepted: toggle(detail.documents_accepted, doc.value) as AdminProductDetail["documents_accepted"] })}
              className={`rounded-full border px-3 py-1.5 text-xs font-medium ${
                detail.documents_accepted.includes(doc.value)
                  ? "border-emerald-600 bg-emerald-600 text-white"
                  : "border-zinc-300 bg-white text-zinc-700 dark:border-zinc-700 dark:bg-zinc-900 dark:text-zinc-200"
              }`}
            >
              {doc.label}
            </button>
          ))}
        </div>
      </div>

      <div className="flex flex-col gap-1.5">
        <span className="text-sm font-medium text-zinc-700 dark:text-zinc-300">Property types accepted</span>
        <div className="flex flex-wrap gap-2">
          {PROPERTY_TYPES.map((p) => (
            <button
              type="button"
              key={p.value}
              onClick={() => setDetail({ ...detail, property_types_accepted: toggle(detail.property_types_accepted, p.value) as AdminProductDetail["property_types_accepted"] })}
              className={`rounded-full border px-3 py-1.5 text-xs font-medium ${
                detail.property_types_accepted.includes(p.value)
                  ? "border-emerald-600 bg-emerald-600 text-white"
                  : "border-zinc-300 bg-white text-zinc-700 dark:border-zinc-700 dark:bg-zinc-900 dark:text-zinc-200"
              }`}
            >
              {p.label}
            </button>
          ))}
        </div>
      </div>

      <div className="grid grid-cols-2 gap-4">
        <div className="flex flex-col gap-1.5">
          <label className="text-sm font-medium text-zinc-700 dark:text-zinc-300">Minimum interest rate (%)</label>
          <input
            type="number"
            step="0.01"
            required
            placeholder="e.g. 7.25"
            value={minRate}
            onChange={(e) => setMinRate(e.target.value === "" ? "" : Number(e.target.value))}
            className="rounded-lg border border-zinc-300 px-3 py-2 text-sm dark:border-zinc-700 dark:bg-zinc-950"
          />
        </div>
        <div className="flex flex-col gap-1.5">
          <label className="text-sm font-medium text-zinc-700 dark:text-zinc-300">Maximum interest rate (%)</label>
          <input
            type="number"
            step="0.01"
            required
            placeholder="e.g. 9.5"
            value={maxRate}
            onChange={(e) => setMaxRate(e.target.value === "" ? "" : Number(e.target.value))}
            className="rounded-lg border border-zinc-300 px-3 py-2 text-sm dark:border-zinc-700 dark:bg-zinc-950"
          />
        </div>
      </div>

      <div className="grid grid-cols-2 gap-4">
        <div className="flex flex-col gap-1.5">
          <label className="text-sm font-medium text-zinc-700 dark:text-zinc-300">Processing fee (display text)</label>
          <input
            type="text"
            placeholder="e.g. 0.5% of loan amount"
            value={detail.processing_fee}
            onChange={(e) => setDetail({ ...detail, processing_fee: e.target.value })}
            className="rounded-lg border border-zinc-300 px-3 py-2 text-sm dark:border-zinc-700 dark:bg-zinc-950"
          />
        </div>
        <div className="flex flex-col gap-1.5">
          <label className="text-sm font-medium text-zinc-700 dark:text-zinc-300">Bank type</label>
          <input
            type="text"
            placeholder="e.g. Private Bank, PSU Bank, HFC, NBFC"
            value={detail.lender_type}
            onChange={(e) => setDetail({ ...detail, lender_type: e.target.value })}
            className="rounded-lg border border-zinc-300 px-3 py-2 text-sm dark:border-zinc-700 dark:bg-zinc-950"
          />
        </div>
      </div>

      {error && <p className="text-sm text-red-600">{error}</p>}

      <div className="flex gap-3">
        <button
          type="submit"
          disabled={saving}
          className="rounded-lg bg-emerald-600 px-5 py-2.5 text-sm font-semibold text-white hover:bg-emerald-700 disabled:opacity-50"
        >
          {saving ? "Saving…" : submitLabel}
        </button>
        <button
          type="button"
          onClick={onCancel}
          className="rounded-lg border border-zinc-300 px-5 py-2.5 text-sm font-semibold text-zinc-700 dark:border-zinc-700 dark:text-zinc-200"
        >
          Cancel
        </button>
      </div>
    </form>
  );
}
