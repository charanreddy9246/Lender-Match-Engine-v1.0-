"use client";

import { useEffect, useState } from "react";

import type { ExploreProduct } from "@/lib/api/explore";

import { labelFor } from "./labels";
import { calculateEmiForLoanAmount, calculateLoanAmountForTenure } from "./loanMath";

// Matches the order backend_cat/app/explore.py's CATEGORY_VALUES uses for
// employment_type, so groups appear in a consistent, sensible order.
const EMPLOYMENT_TYPE_ORDER = ["salaried", "self_employed", "pensioner", "cash_income", "nri"];

function groupByEmploymentType(results: ExploreProduct[]): { employmentType: string; products: ExploreProduct[] }[] {
  const groups = new Map<string, ExploreProduct[]>();
  for (const product of results) {
    const list = groups.get(product.employment_type) ?? [];
    list.push(product);
    groups.set(product.employment_type, list);
  }
  return EMPLOYMENT_TYPE_ORDER.filter((key) => groups.has(key)).map((key) => ({
    employmentType: key,
    products: groups.get(key)!,
  }));
}

function AffordabilityPanel({
  product,
  requestedLoanAmount,
}: {
  product: ExploreProduct;
  requestedLoanAmount: number | null;
}) {
  const hasFoir = product.customer_foir_pct !== null;
  const hasTenure = product.final_tenure_years !== null;
  const hasMaxEmi = product.max_emi !== null;
  const maxTenure = product.final_tenure_years;

  // Starts at the maximum allowed tenure, but the customer can drag it down
  // — the loan amount recalculates live for whatever tenure they actually
  // want, instead of always assuming they'll take the longest one.
  const [selectedTenure, setSelectedTenure] = useState(maxTenure ?? 0);

  // Only re-syncs when maxTenure's *value* actually changes (e.g. the
  // customer edited their age) — not on every re-render, so toggling an
  // unrelated filter doesn't wipe out a manual slider adjustment.
  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect -- intentional: syncs local slider state to a prop that can change independently (age), not derivable during render without losing the user's ability to drag it afterward.
    setSelectedTenure(maxTenure ?? 0);
  }, [maxTenure]);

  // Starts at the bank's lowest published rate (what interest_rate_pct
  // always is — see get_bank_interest_rate_pct in domain.py). Editable for
  // every bank, not just ones with a published range: a bank that only ever
  // published a single "X% onwards" figure still gets an editable box, since
  // the person using this tool may know the borrower's actual quoted rate —
  // it just isn't clamped to a published ceiling that doesn't exist. Banks
  // with a real published range (interest_rate_upper_pct) *do* get clamped
  // to that range, so the field can't wander outside a number the bank
  // actually publishes.
  //
  // The input keeps its own raw text state (not a number) so the field can
  // sit empty or mid-edit (e.g. "8.") while typing — a numeric state would
  // force-fill back to a default the instant the field went empty, making it
  // impossible to backspace and retype. Calculations fall back to the bank's
  // lowest rate while the text is empty/invalid, so nothing breaks mid-edit;
  // the value is only clamped/floored once the field loses focus.
  const hasRateRange = product.interest_rate_upper_pct !== null;
  const RATE_FLOOR_PCT = 0.01; // guards against 0%, which breaks the EMI formula (division by zero)
  const [rateInputText, setRateInputText] = useState(product.interest_rate_pct.toFixed(2));

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect -- same reasoning as selectedTenure above: syncs to a prop that can change independently.
    setRateInputText(product.interest_rate_pct.toFixed(2));
  }, [product.interest_rate_pct]);

  const parsedRate = Number(rateInputText);
  const selectedRate = rateInputText.trim() !== "" && Number.isFinite(parsedRate) ? parsedRate : product.interest_rate_pct;

  if (!hasFoir && !hasTenure && !hasMaxEmi) return null;

  // The bank's own max tenure and the tenure actually available to this
  // customer (see calculate_final_tenure_years in domain.py) can differ when
  // the customer's age leaves fewer years than the bank would otherwise
  // allow — flag that so it isn't mistaken for a data error.
  const bankMaxTenure = product.bank_max_tenure_years;
  const ageIsLimitingTenure =
    hasTenure && bankMaxTenure !== null && maxTenure !== null && maxTenure < bankMaxTenure;

  const pass = product.foir_pass;
  const statColor = pass === false ? "text-red-700 dark:text-red-400" : "text-emerald-700 dark:text-emerald-400";
  const loanAmountForSelection =
    product.max_emi !== null
      ? calculateLoanAmountForTenure(product.max_emi, selectedTenure, selectedRate)
      : null;

  // Compares what the customer asked to borrow against what this bank can
  // actually stretch to for them (same figure shown as "Loan Amount" above,
  // recalculated at this bank's real rate — see loanMath.ts). Only
  // meaningful once they've typed a requested amount.
  const hasRequestedAmount = requestedLoanAmount !== null && requestedLoanAmount > 0;
  const meetsRequestedAmount =
    hasRequestedAmount && loanAmountForSelection !== null && loanAmountForSelection >= requestedLoanAmount!;
  const fallsShortOfRequestedAmount =
    hasRequestedAmount && loanAmountForSelection !== null && loanAmountForSelection < requestedLoanAmount!;

  // The big headline number answers "can I get what I actually asked for,"
  // not an abstract ceiling — so once they've told us an amount and they
  // qualify for it, show *that* amount instead of the bank's max. Falls
  // back to the max ceiling when there's no request yet, or when they asked
  // for more than they qualify for (loanAmountForSelection is already the
  // real eligible number in that case — see the shortfall message below).
  const headlineAmount = meetsRequestedAmount ? requestedLoanAmount : loanAmountForSelection;
  const headlineLabel = meetsRequestedAmount
    ? "Your Requested Loan Amount"
    : `Loan Amount — for ${selectedTenure} yr tenure`;

  // The EMI this specific requested amount would actually require — separate
  // from Max EMI (the bank's ceiling, driven purely by FOIR/income). This is
  // what the borrower would really pay, so it can land above or below Max EMI.
  const proposedEmi = hasRequestedAmount
    ? calculateEmiForLoanAmount(requestedLoanAmount!, selectedTenure, selectedRate)
    : null;
  const proposedEmiWithinBudget = proposedEmi !== null && hasMaxEmi && proposedEmi <= product.max_emi!;

  // Describe whatever tenure the calculation actually used (selectedTenure
  // — the slider), not the age-based ceiling (maxTenure) it defaults to.
  // Dragging the slider below that ceiling is the customer's own choice,
  // not something age caused, so it gets its own wording rather than being
  // misreported as an age-driven reduction.
  const tenureIsUserReduced = hasTenure && selectedTenure < maxTenure!;
  const tenureDescription = !hasTenure
    ? null
    : tenureIsUserReduced
      ? `the ${selectedTenure}-yr tenure you selected`
      : ageIsLimitingTenure
        ? `a tenure reduced to ${maxTenure} yrs because of your age`
        : `a ${maxTenure}-yr tenure`;

  return (
    <div
      className={`flex flex-col gap-3 rounded-xl border-2 p-4 ${
        pass === false
          ? "border-red-300 bg-red-50 dark:border-red-900 dark:bg-red-950/30"
          : "border-emerald-300 bg-emerald-50 dark:border-emerald-900 dark:bg-emerald-950/30"
      }`}
    >
      {headlineAmount !== null && (
        <div>
          <p className="text-[10px] font-bold uppercase tracking-wider text-zinc-500 dark:text-zinc-400">
            {headlineLabel}
          </p>
          <p className={`text-4xl font-black leading-tight ${statColor}`}>
            {headlineAmount > 0 ? `₹${Math.round(headlineAmount).toLocaleString("en-IN")}` : "—"}
          </p>
        </div>
      )}

      {/* Read-only figures — top-aligned so Max EMI / Proposed EMI / FOIR
          line up cleanly even though their content isn't the same height. */}
      <div className="flex flex-wrap items-start gap-x-8 gap-y-3">
        {hasMaxEmi && (
          <div className="flex min-w-[110px] flex-col gap-0.5">
            <p className="text-[10px] font-bold uppercase tracking-wider text-zinc-500 dark:text-zinc-400">
              Max Allowed EMI / month
            </p>
            <p className="text-xs font-semibold text-zinc-500 dark:text-zinc-400">Bank&apos;s ceiling, from FOIR</p>
            <p className={`text-xl font-black leading-tight ${statColor}`}>
              {product.max_emi! > 0 ? `₹${Math.round(product.max_emi!).toLocaleString("en-IN")}` : "—"}
            </p>
          </div>
        )}
        {proposedEmi !== null && (
          <div className="flex min-w-[130px] flex-col gap-0.5">
            <p className="text-[10px] font-bold uppercase tracking-wider text-zinc-500 dark:text-zinc-400">
              Proposed EMI ({selectedRate.toFixed(2)}%{product.interest_rate_is_estimated ? ", unverified" : ""})
            </p>
            <p className="text-xs font-semibold text-zinc-500 dark:text-zinc-400">For your requested amount</p>
            <p
              className={`text-xl font-black leading-tight ${
                proposedEmiWithinBudget
                  ? "text-emerald-700 dark:text-emerald-400"
                  : "text-red-700 dark:text-red-400"
              }`}
            >
              {proposedEmi > 0 ? `₹${Math.round(proposedEmi).toLocaleString("en-IN")}` : "—"}
            </p>
          </div>
        )}
        {hasFoir && (
          <div className="flex min-w-[110px] flex-col gap-0.5">
            <p className="text-[10px] font-bold uppercase tracking-wider text-zinc-500 dark:text-zinc-400">FOIR</p>
            <p className="text-xs font-semibold text-zinc-500 dark:text-zinc-400">Share of income already committed</p>
            <p className="text-xl font-black leading-tight text-zinc-800 dark:text-zinc-100">
              {product.customer_foir_pct?.toFixed(1)}%{" "}
              <span className={statColor}>{pass ? "✓" : "✗"}</span>{" "}
              <span className="text-xs font-semibold text-zinc-500 dark:text-zinc-400">
                of {product.bank_foir_pct}% limit
              </span>
            </p>
          </div>
        )}
      </div>

      {/* Adjustable inputs — grouped and visually set apart from the
          read-only figures above, so it's clear these two are the ones you
          can change. */}
      {((hasTenure && maxTenure! > 0) || hasMaxEmi) && (
        <div className="flex flex-wrap items-end gap-x-8 gap-y-3 rounded-lg border border-zinc-900/10 bg-white/60 px-3 py-2.5 dark:border-zinc-100/10 dark:bg-black/15">
          {hasTenure && maxTenure! > 0 && (
            <div className="flex min-w-[110px] flex-col gap-1">
              <div className="flex items-center justify-between gap-2 text-[10px] font-bold uppercase tracking-wider text-zinc-500 dark:text-zinc-400">
                <span>Tenure</span>
                <span>
                  {selectedTenure}/{maxTenure} yrs
                </span>
              </div>
              <input
                type="range"
                min={1}
                max={maxTenure!}
                step={1}
                value={selectedTenure}
                onChange={(e) => setSelectedTenure(Number(e.target.value))}
                className="h-1 w-24 cursor-pointer accent-teal-600"
              />
            </div>
          )}
          {hasMaxEmi && (
            <div className="flex flex-col gap-1">
              <p className="text-[10px] font-bold uppercase tracking-wider text-zinc-500 dark:text-zinc-400">
                Interest rate
              </p>
              <div className="flex items-center gap-1.5">
                <input
                  type="number"
                  min={hasRateRange ? product.interest_rate_pct : RATE_FLOOR_PCT}
                  max={hasRateRange ? product.interest_rate_upper_pct! : undefined}
                  step={0.05}
                  value={rateInputText}
                  onChange={(e) => setRateInputText(e.target.value)}
                  onBlur={() => {
                    const floor = hasRateRange ? product.interest_rate_pct : RATE_FLOOR_PCT;
                    const clamped = hasRateRange
                      ? Math.min(Math.max(selectedRate, floor), product.interest_rate_upper_pct!)
                      : Math.max(selectedRate, floor);
                    setRateInputText(clamped.toFixed(2));
                  }}
                  className={`w-16 rounded-md border px-1.5 py-0.5 text-xs font-semibold outline-none focus:border-teal-500 ${
                    product.interest_rate_is_estimated
                      ? "border-amber-400 bg-amber-50 text-amber-900 dark:border-amber-600 dark:bg-amber-950/40 dark:text-amber-200"
                      : "border-zinc-300 dark:border-zinc-700 dark:bg-zinc-950"
                  }`}
                />
                <span
                  className={`text-xs font-semibold ${
                    product.interest_rate_is_estimated
                      ? "text-amber-700 dark:text-amber-400"
                      : "text-zinc-500 dark:text-zinc-400"
                  }`}
                >
                  {product.interest_rate_is_estimated
                    ? `${product.interest_rate_pct.toFixed(2)}% not verified — edit if you know their actual rate`
                    : hasRateRange
                      ? `${product.interest_rate_pct.toFixed(2)}%–${product.interest_rate_upper_pct!.toFixed(2)}% published range`
                      : `${product.interest_rate_pct.toFixed(2)}% confirmed rate`}
                </span>
              </div>
            </div>
          )}
        </div>
      )}

      {ageIsLimitingTenure && (
        <p className="text-xs font-medium text-amber-700 dark:text-amber-400">
          Your age is reducing {product.bank_name}&apos;s usual {bankMaxTenure}-yr tenure — you&apos;re
          eligible for {maxTenure} {maxTenure === 1 ? "yr" : "yrs"} based on your age.
        </p>
      )}

      {meetsRequestedAmount && (
        <p className="text-xs font-semibold text-emerald-700 dark:text-emerald-400">
          ✓ You&apos;re eligible for your full requested ₹{requestedLoanAmount!.toLocaleString("en-IN")}.
        </p>
      )}

      {fallsShortOfRequestedAmount && (
        <p className="text-xs font-medium text-red-700 dark:text-red-400">
          Your Proposed EMI of ₹{Math.round(proposedEmi!).toLocaleString("en-IN")} is more than {product.bank_name}
          &apos;s ₹{Math.round(product.max_emi!).toLocaleString("en-IN")}/month budget for you ({product.bank_foir_pct}
          % FOIR limit) — so at {tenureDescription} and {selectedRate.toFixed(2)}% interest
          {product.interest_rate_is_estimated ? " (not verified)" : ""}, you&apos;re only eligible for ₹
          {Math.round(loanAmountForSelection!).toLocaleString("en-IN")} of the ₹
          {requestedLoanAmount!.toLocaleString("en-IN")} you requested.
        </p>
      )}
    </div>
  );
}

function BankCard({
  product,
  requestedLoanAmount,
}: {
  product: ExploreProduct;
  requestedLoanAmount: number | null;
}) {
  return (
    <div className="flex flex-col gap-3 rounded-xl border-l-4 border-teal-600 bg-white p-4 shadow-sm transition-shadow hover:shadow-md dark:bg-zinc-900">
      <div className="flex items-start justify-between gap-2">
        <h3 className="text-base font-bold text-zinc-900 dark:text-zinc-50">{product.bank_name}</h3>
        <span className="shrink-0 rounded-full bg-teal-600 px-3 py-1 text-xs font-bold text-white">
          {product.product_name}
        </span>
      </div>

      <AffordabilityPanel product={product} requestedLoanAmount={requestedLoanAmount} />

      <dl className="grid grid-cols-1 gap-x-4 gap-y-2.5 text-sm sm:grid-cols-2">
        <div>
          <dt className="text-xs font-bold uppercase tracking-wide text-teal-700 dark:text-teal-400">Usage</dt>
          <dd className="text-zinc-700 dark:text-zinc-300">{product.property_usage.map(labelFor).join(", ") || "—"}</dd>
        </div>
        <div>
          <dt className="text-xs font-bold uppercase tracking-wide text-teal-700 dark:text-teal-400">Stage</dt>
          <dd className="text-zinc-700 dark:text-zinc-300">{product.property_stage.map(labelFor).join(", ") || "—"}</dd>
        </div>
        <div>
          <dt className="text-xs font-bold uppercase tracking-wide text-teal-700 dark:text-teal-400">Location</dt>
          <dd className="text-zinc-700 dark:text-zinc-300">{product.property_location.map(labelFor).join(", ") || "—"}</dd>
        </div>
        <div className="sm:col-span-2">
          <dt className="text-xs font-bold uppercase tracking-wide text-teal-700 dark:text-teal-400">Property type</dt>
          <dd className="text-zinc-700 dark:text-zinc-300">{product.property_type.map(labelFor).join(", ") || "—"}</dd>
        </div>
      </dl>
    </div>
  );
}

export function ResultsList({
  results,
  total,
  loading,
  requestedLoanAmount,
  onClear,
}: {
  results: ExploreProduct[];
  total: number;
  loading: boolean;
  requestedLoanAmount: number | null;
  onClear: () => void;
}) {
  return (
    <div className="flex flex-1 flex-col gap-4">
      <div className="flex items-baseline justify-between gap-2 border-b-2 border-zinc-900 pb-3 dark:border-zinc-100">
        <div className="flex items-baseline gap-2">
          <span className="text-2xl font-black text-zinc-900 dark:text-zinc-50">{loading ? "…" : total}</span>
          <span className="text-sm font-semibold uppercase tracking-wide text-zinc-500 dark:text-zinc-400">
            {loading ? "Loading" : `Result${total === 1 ? "" : "s"}`}
          </span>
        </div>
        <button
          onClick={onClear}
          className="rounded-full border border-teal-600 px-3 py-1 text-sm font-bold text-teal-700 hover:bg-teal-50 dark:border-teal-500 dark:text-teal-400 dark:hover:bg-teal-950/40"
        >
          Clear filters
        </button>
      </div>

      {!loading && results.length === 0 && (
        <div className="rounded-xl border border-dashed border-zinc-300 p-8 text-center text-sm text-zinc-400 dark:border-zinc-700">
          No banks match this combination of filters.
        </div>
      )}

      <div className="flex flex-col gap-6">
        {groupByEmploymentType(results).map(({ employmentType, products }) => (
          <div key={employmentType} className="flex flex-col gap-3">
            <h3 className="flex items-center gap-2 text-sm font-bold uppercase tracking-wide text-zinc-500 dark:text-zinc-400">
              {labelFor(employmentType)}
              <span className="rounded-full bg-zinc-200 px-2 py-0.5 text-xs font-bold text-zinc-600 dark:bg-zinc-700 dark:text-zinc-300">
                {products.length}
              </span>
            </h3>
            {products.map((product) => (
              <BankCard
                key={`${product.bank_name}-${product.product_name}`}
                product={product}
                requestedLoanAmount={requestedLoanAmount}
              />
            ))}
          </div>
        ))}
      </div>
    </div>
  );
}
