"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useEffect, useState, type ReactNode } from "react";
import { Controller, useForm, useWatch } from "react-hook-form";

import { ButtonGroup } from "@/components/ui/ButtonGroup";
import { FormattedNumberInput } from "@/components/ui/FormattedNumberInput";
import { MultiSelectButtons } from "@/components/ui/MultiSelectButtons";
import { ApiError } from "@/lib/api/client";
import { matchLenders } from "@/lib/api/lenders";
import {
  DOCUMENT_TYPES,
  DOCUMENTS_BY_EMPLOYMENT_TYPE,
  EMPLOYMENT_TYPES,
  INCOME_FIELD_BY_EMPLOYMENT_TYPE,
  PROPERTY_TYPES,
  type BorrowerProfile,
  type EmploymentType,
  type MatchResponse,
} from "@/lib/api/types";

import { lenderFinderSchema, type LenderFinderFormValues } from "./schema";
import { ResultsPanel } from "./ResultsPanel";

const INCOME_FIELDS = ["net_monthly_salary", "annual_turnover", "annual_gross_receipts", "monthly_pension"] as const;

const YES_NO_OPTIONS = [
  { value: "yes", label: "Yes" },
  { value: "no", label: "No" },
] as const;

// Purely cosmetic — one small icon per employment type, matching the icon
// style shown next to each option.
const EMPLOYMENT_TYPE_ICONS: Record<string, ReactNode> = {
  salaried: (
    <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2" />
      <circle cx="9" cy="7" r="4" />
      <path d="M22 21v-2a4 4 0 0 0-3-3.87" />
      <path d="M16 3.13a4 4 0 0 1 0 7.75" />
    </svg>
  ),
  self_employed: (
    <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <rect x="2" y="7" width="20" height="14" rx="2" />
      <path d="M16 21V5a2 2 0 0 0-2-2h-4a2 2 0 0 0-2 2v16" />
    </svg>
  ),
  professional: (
    <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="12" cy="8" r="6" />
      <path d="M15.5 13.5 17 22l-5-3-5 3 1.5-8.5" />
    </svg>
  ),
  pensioner: (
    <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10Z" />
      <path d="m9 12 2 2 4-4" />
    </svg>
  ),
};

export function LenderFinderForm() {
  const [results, setResults] = useState<MatchResponse | null>(null);
  const [submitError, setSubmitError] = useState<string | null>(null);

  const {
    register,
    control,
    handleSubmit,
    setValue,
    formState: { errors, isSubmitting },
  } = useForm<LenderFinderFormValues>({
    resolver: zodResolver(lenderFinderSchema),
    defaultValues: {
      has_co_borrower: false,
      documents_available: [],
    },
  });

  const employmentType = useWatch({ control, name: "employment_type" }) as EmploymentType | undefined;
  const income = employmentType ? INCOME_FIELD_BY_EMPLOYMENT_TYPE[employmentType] : undefined;

  // Which documents make sense to show depends on employment type too — a
  // Salaried borrower has no use for "GST", a Pensioner has no use for
  // "Salary slip". Bank statement always stays, since it's required for
  // everyone regardless of employment type. Nothing extra shows until an
  // employment type is picked.
  const relevantDocumentValues = employmentType ? DOCUMENTS_BY_EMPLOYMENT_TYPE[employmentType] : [];
  const documentOptions = DOCUMENT_TYPES.filter(
    (d) => d.value === "bank_statement" || relevantDocumentValues.includes(d.value),
  );
  const documentsAvailable = useWatch({ control, name: "documents_available" });

  // Switching employment type changes which income question applies, and
  // which documents are even shown — clear anything no longer valid so a
  // stale value from a previous selection never gets sent.
  useEffect(() => {
    for (const field of INCOME_FIELDS) {
      if (field !== income?.field) {
        setValue(field, undefined);
      }
    }
    if (employmentType !== "pensioner") {
      setValue("has_co_borrower", false);
    }
    const validValues = new Set<string>(documentOptions.map((d) => d.value));
    const stillValid = (documentsAvailable ?? []).filter((d) => validValues.has(d));
    if (stillValid.length !== (documentsAvailable ?? []).length) {
      setValue("documents_available", stillValid);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps -- documentOptions/documentsAvailable are derived from employmentType itself; including them would loop
  }, [employmentType, income?.field, setValue]);

  async function onSubmit(values: LenderFinderFormValues) {
    setSubmitError(null);
    setResults(null);
    try {
      const response = await matchLenders(values as BorrowerProfile);
      setResults(response);
    } catch (err) {
      setSubmitError(err instanceof ApiError ? err.message : "Something went wrong. Please try again.");
    }
  }

  return (
    <div className="mx-auto flex w-full max-w-6xl flex-col gap-8">
      <form onSubmit={handleSubmit(onSubmit)} className="flex w-full flex-col gap-7 rounded-2xl border border-teal-100 bg-gradient-to-br from-cyan-50 via-teal-50 to-white p-6 shadow-sm dark:border-zinc-800 dark:from-teal-950/30 dark:via-zinc-900 dark:to-zinc-900 sm:p-10">
        <h2 className="text-xl font-semibold text-zinc-900 dark:text-zinc-50">Your details</h2>

        <div className="grid grid-cols-1 gap-5 sm:grid-cols-2">
          <div className="flex flex-col gap-1.5">
            <label htmlFor="cibil_score" className="text-base font-medium text-zinc-700 dark:text-zinc-300">
              CIBIL score
            </label>
            <input
              id="cibil_score"
              type="number"
              placeholder="eg. 780"
              className="rounded-lg border border-zinc-200 bg-white/80 px-4 py-2.5 text-base outline-none focus:border-teal-500 dark:border-zinc-700 dark:bg-zinc-950"
              {...register("cibil_score", { valueAsNumber: true })}
            />
            {errors.cibil_score && <p className="text-xs text-red-600">{errors.cibil_score.message}</p>}
          </div>

          <div className="flex flex-col gap-1.5">
            <label htmlFor="loan_amount_required" className="text-base font-medium text-zinc-700 dark:text-zinc-300">
              Loan amount required (₹)
            </label>
            <Controller
              name="loan_amount_required"
              control={control}
              render={({ field }) => (
                <FormattedNumberInput
                  id="loan_amount_required"
                  placeholder="eg. 50,00,000"
                  value={field.value}
                  onChange={field.onChange}
                />
              )}
            />
            {errors.loan_amount_required && <p className="text-xs text-red-600">{errors.loan_amount_required.message}</p>}
          </div>
        </div>

        <div className="flex flex-col gap-1.5">
          <span className="text-base font-medium text-zinc-700 dark:text-zinc-300">Employment type</span>
          <Controller
            name="employment_type"
            control={control}
            render={({ field }) => (
              <ButtonGroup
                name="employment_type"
                options={EMPLOYMENT_TYPES}
                value={field.value}
                onChange={field.onChange}
                icons={EMPLOYMENT_TYPE_ICONS}
              />
            )}
          />
          {errors.employment_type && <p className="text-xs text-red-600">{errors.employment_type.message}</p>}
        </div>

        {/* Which income question shows here, and which field it fills, changes
            with employment type — Salaried asks salary, Self-employed asks
            turnover, Professional asks gross receipts, Pensioner asks pension.
            Nothing renders until an employment type is picked. */}
        {income && (
          <div className="flex flex-col gap-1.5">
            <label htmlFor={income.field} className="text-base font-medium text-zinc-700 dark:text-zinc-300">
              {income.label}
            </label>
            <Controller
              key={income.field}
              name={income.field}
              control={control}
              render={({ field }) => (
                <FormattedNumberInput id={income.field} placeholder={income.placeholder} value={field.value} onChange={field.onChange} />
              )}
            />
            {errors[income.field] && <p className="text-xs text-red-600">{errors[income.field]?.message}</p>}
          </div>
        )}

        {/* Only Pensioner profiles get asked this — some lenders in the
            dataset require a co-borrower for pensioners, most don't. */}
        {employmentType === "pensioner" && (
          <div className="flex flex-col gap-1.5">
            <span className="text-base font-medium text-zinc-700 dark:text-zinc-300">Do you have a co-borrower?</span>
            <Controller
              name="has_co_borrower"
              control={control}
              render={({ field }) => (
                <ButtonGroup
                  name="has_co_borrower"
                  options={YES_NO_OPTIONS}
                  value={field.value ? "yes" : "no"}
                  onChange={(v) => field.onChange(v === "yes")}
                />
              )}
            />
          </div>
        )}

        <div className="flex flex-col gap-1.5">
          <span className="text-base font-medium text-zinc-700 dark:text-zinc-300">Documents you can provide</span>
          <Controller
            name="documents_available"
            control={control}
            render={({ field }) => (
              <MultiSelectButtons
                name="documents_available"
                options={documentOptions}
                values={field.value ?? []}
                onChange={field.onChange}
                requiredValue="bank_statement"
              />
            )}
          />
          {errors.documents_available && <p className="text-xs text-red-600">{errors.documents_available.message}</p>}
        </div>

        <div className="flex flex-col gap-1.5">
          <span className="text-base font-medium text-zinc-700 dark:text-zinc-300">Property type</span>
          <Controller
            name="property_type"
            control={control}
            render={({ field }) => (
              <ButtonGroup name="property_type" options={PROPERTY_TYPES} value={field.value} onChange={field.onChange} />
            )}
          />
          {errors.property_type && <p className="text-xs text-red-600">{errors.property_type.message}</p>}
          <p className="text-xs text-zinc-500 dark:text-zinc-400">
            &ldquo;Others&rdquo; covers all non-municipal village land, known regionally as gaothan, gramthal, gunthewari, abadi, lal dora, nazul, or revenue land.
          </p>
        </div>

        {submitError && <p className="text-sm text-red-600">{submitError}</p>}

        <button
          type="submit"
          disabled={isSubmitting}
          className="rounded-lg bg-teal-600 px-5 py-3.5 text-base font-semibold text-white transition-colors hover:bg-teal-700 disabled:opacity-50"
        >
          {isSubmitting ? "Finding your lenders…" : "Show my top 3 lenders"}
        </button>
      </form>

      {results && <ResultsPanel results={results} />}
    </div>
  );
}
