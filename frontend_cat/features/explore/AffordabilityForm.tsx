"use client";

import { useState } from "react";

interface ObligationRow {
  id: string;
  label: string;
  amount: number | "";
}

let nextId = 1;

// Displays with Indian comma grouping (80000 -> "80,000") while typing —
// a plain type="number" input can't show commas at all, so this is a text
// input that formats on every keystroke and reports back a plain number.
function RupeeInput({
  id,
  value,
  onChange,
  placeholder,
  className,
}: {
  id?: string;
  value: number | "";
  onChange: (value: number | "") => void;
  placeholder?: string;
  className?: string;
}) {
  const displayValue = value === "" ? "" : value.toLocaleString("en-IN");
  return (
    <input
      id={id}
      type="text"
      inputMode="numeric"
      placeholder={placeholder}
      value={displayValue}
      onChange={(e) => {
        const digitsOnly = e.target.value.replace(/[^0-9]/g, "");
        onChange(digitsOnly === "" ? "" : Number(digitsOnly));
      }}
      className={className}
    />
  );
}

interface AffordabilityFormProps {
  age: number | null;
  monthlyIncome: number | null;
  requestedLoanAmount: number | null;
  onAgeChange: (value: number | null) => void;
  onMonthlyIncomeChange: (value: number | null) => void;
  onObligationsChange: (amounts: number[]) => void;
  onRequestedLoanAmountChange: (value: number | null) => void;
}

export function AffordabilityForm({
  age,
  monthlyIncome,
  requestedLoanAmount,
  onAgeChange,
  onMonthlyIncomeChange,
  onObligationsChange,
  onRequestedLoanAmountChange,
}: AffordabilityFormProps) {
  const [rows, setRows] = useState<ObligationRow[]>([{ id: String(nextId++), label: "", amount: "" }]);

  function commit(next: ObligationRow[]) {
    setRows(next);
    onObligationsChange(next.map((r) => r.amount).filter((a): a is number => typeof a === "number" && a > 0));
  }

  function updateRow(id: string, patch: Partial<ObligationRow>) {
    commit(rows.map((r) => (r.id === id ? { ...r, ...patch } : r)));
  }

  function addRow() {
    commit([...rows, { id: String(nextId++), label: "", amount: "" }]);
  }

  function removeRow(id: string) {
    commit(rows.length === 1 ? [{ id: String(nextId++), label: "", amount: "" }] : rows.filter((r) => r.id !== id));
  }

  const total = rows.reduce((sum, r) => sum + (typeof r.amount === "number" ? r.amount : 0), 0);

  return (
    <div className="rounded-xl border border-zinc-200 bg-white p-4 shadow-sm dark:border-zinc-800 dark:bg-zinc-900">
      <h3 className="mb-3 border-l-4 border-teal-600 pl-2.5 text-base font-black uppercase tracking-wide text-zinc-900 dark:text-zinc-50">
        Affordability
      </h3>

      <div className="flex flex-col gap-3">
        <div className="grid grid-cols-2 gap-2">
          <div className="flex flex-col gap-1">
            <label htmlFor="affordability-age" className="text-sm font-bold text-zinc-700 dark:text-zinc-300">
              Age
            </label>
            <input
              id="affordability-age"
              type="number"
              min={18}
              placeholder="e.g. 35"
              value={age ?? ""}
              onChange={(e) => onAgeChange(e.target.value === "" ? null : Number(e.target.value))}
              className="rounded-lg border border-zinc-300 bg-zinc-50 px-2.5 py-2 text-sm font-semibold text-zinc-900 outline-none focus:border-teal-500 focus:bg-white focus:ring-2 focus:ring-teal-500/30 dark:border-zinc-700 dark:bg-zinc-950 dark:text-zinc-100"
            />
          </div>
          <div className="flex flex-col gap-1">
            <label htmlFor="affordability-income" className="text-sm font-bold text-zinc-700 dark:text-zinc-300">
              Monthly income (₹)
            </label>
            <RupeeInput
              id="affordability-income"
              placeholder="e.g. 80,000"
              value={monthlyIncome ?? ""}
              onChange={(v) => onMonthlyIncomeChange(v === "" ? null : v)}
              className="rounded-lg border border-zinc-300 bg-zinc-50 px-2.5 py-2 text-sm font-semibold text-zinc-900 outline-none focus:border-teal-500 focus:bg-white focus:ring-2 focus:ring-teal-500/30 dark:border-zinc-700 dark:bg-zinc-950 dark:text-zinc-100"
            />
          </div>
        </div>

        <div className="flex flex-col gap-1">
          <label
            htmlFor="affordability-requested-amount"
            className="text-sm font-bold text-zinc-700 dark:text-zinc-300"
          >
            Loan amount you&apos;re requesting (₹)
          </label>
          <RupeeInput
            id="affordability-requested-amount"
            placeholder="e.g. 50,00,000"
            value={requestedLoanAmount ?? ""}
            onChange={(v) => onRequestedLoanAmountChange(v === "" ? null : v)}
            className="rounded-lg border border-zinc-300 bg-zinc-50 px-2.5 py-2 text-sm font-semibold text-zinc-900 outline-none focus:border-teal-500 focus:bg-white focus:ring-2 focus:ring-teal-500/30 dark:border-zinc-700 dark:bg-zinc-950 dark:text-zinc-100"
          />
        </div>

        <div className="flex flex-col gap-1.5">
          <span className="text-sm font-bold text-zinc-700 dark:text-zinc-300">
            Existing obligations (home loan, education loan, etc.)
          </span>
          {rows.map((row) => (
            <div key={row.id} className="flex items-center gap-1.5">
              <input
                type="text"
                placeholder="Loan type (optional)"
                value={row.label}
                onChange={(e) => updateRow(row.id, { label: e.target.value })}
                className="min-w-0 flex-1 rounded-lg border border-zinc-300 bg-zinc-50 px-2.5 py-2 text-sm font-medium outline-none focus:border-teal-500 focus:bg-white focus:ring-2 focus:ring-teal-500/30 dark:border-zinc-700 dark:bg-zinc-950"
              />
              <RupeeInput
                placeholder="₹ amount"
                value={row.amount}
                onChange={(v) => updateRow(row.id, { amount: v })}
                className="w-28 rounded-lg border border-zinc-300 bg-zinc-50 px-2.5 py-2 text-sm font-semibold outline-none focus:border-teal-500 focus:bg-white focus:ring-2 focus:ring-teal-500/30 dark:border-zinc-700 dark:bg-zinc-950"
              />
              <button
                type="button"
                onClick={() => removeRow(row.id)}
                aria-label="Remove obligation"
                className="shrink-0 rounded-lg px-2 py-1.5 text-zinc-400 hover:bg-zinc-100 hover:text-red-600 dark:hover:bg-zinc-800"
              >
                ×
              </button>
            </div>
          ))}
          <button
            type="button"
            onClick={addRow}
            className="w-fit text-sm font-bold text-teal-700 hover:text-teal-900 dark:text-teal-400"
          >
            + Add another obligation
          </button>
        </div>

        {total > 0 && (
          <p className="text-sm text-zinc-600 dark:text-zinc-400">
            Total monthly obligations: <span className="font-bold text-zinc-900 dark:text-zinc-100">₹{total.toLocaleString("en-IN")}</span>
          </p>
        )}
      </div>
    </div>
  );
}
