"use client";

import { useEffect, useState } from "react";

import { errorMessage } from "@/lib/api/client";
import { adminApi, type AdminBankSummary, type AdminProductDetail, type AdminProductOut } from "@/lib/api/admin";
import { EMPLOYMENT_TYPES } from "@/lib/api/types";

import { ProductForm } from "./ProductForm";

type View =
  | { name: "list" }
  | { name: "bank"; bankName: string }
  // isNewBank marks the case where this bank hasn't actually been created
  // yet — reached via "+ Add new bank" for a name that doesn't exist. Cancel
  // needs this to know whether there's a real "bank" screen to fall back to.
  | { name: "add-employment-type"; bankName: string; isNewBank: boolean }
  | { name: "edit"; bankName: string; product: AdminProductOut }
  | { name: "add-new-bank" };

export function BanksSection({ getToken }: { getToken: () => Promise<string | null> }) {
  const [view, setView] = useState<View>({ name: "list" });
  const [banks, setBanks] = useState<AdminBankSummary[] | null>(null);
  const [bankProducts, setBankProducts] = useState<AdminProductOut[] | null>(null);
  const [newBankName, setNewBankName] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [search, setSearch] = useState("");

  async function refreshBankProducts(bankName: string) {
    const token = await getToken();
    if (!token) return;
    setBankProducts(await adminApi.getBankProducts(token, bankName));
  }

  // Only "list" and "bank" ever need to fetch here — "add-employment-type" is
  // reached both for banks that already exist AND ones that don't exist yet
  // (mid-creation), so fetching products for it here would 404 and crash for
  // the "doesn't exist yet" case, which is a completely normal state, not an
  // error.
  useEffect(() => {
    let cancelled = false;
    async function load() {
      const token = await getToken();
      if (!token || cancelled) return;
      try {
        if (view.name === "list") {
          const data = await adminApi.listBanks(token);
          if (!cancelled) setBanks(data);
        } else if (view.name === "bank") {
          const data = await adminApi.getBankProducts(token, view.bankName);
          if (!cancelled) setBankProducts(data);
        }
        if (!cancelled) setError(null);
      } catch (err) {
        if (!cancelled) setError(errorMessage(err));
      }
    }
    load();
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps -- getToken is stable across renders
  }, [view]);

  async function handleCreate(bankName: string, detail: AdminProductDetail) {
    const token = await getToken();
    if (!token) return;
    await adminApi.createBankProduct(token, bankName, detail);
    setView({ name: "bank", bankName });
  }

  async function handleUpdate(bankName: string, employmentType: string, detail: AdminProductDetail) {
    const token = await getToken();
    if (!token) return;
    await adminApi.updateBankProduct(token, bankName, employmentType, detail);
    setView({ name: "bank", bankName });
  }

  async function handleDeleteProduct(bankName: string, employmentType: string) {
    if (!confirm(`Remove the ${employmentType} product from ${bankName}?`)) return;
    setError(null);
    try {
      const token = await getToken();
      if (!token) return;
      await adminApi.deleteBankProduct(token, bankName, employmentType);
      await refreshBankProducts(bankName);
    } catch (err) {
      setError(errorMessage(err));
    }
  }

  async function handleDeleteBank(bankName: string) {
    if (!confirm(`Delete ${bankName} entirely, including all its products?`)) return;
    setError(null);
    try {
      const token = await getToken();
      if (!token) return;
      await adminApi.deleteBank(token, bankName);
      setView({ name: "list" });
    } catch (err) {
      setError(errorMessage(err));
    }
  }

  async function handleAddNewBankSubmit() {
    setError(null);
    if (!newBankName.trim()) {
      setError("Enter a bank name.");
      return;
    }
    const token = await getToken();
    if (!token) return;
    try {
      const products = await adminApi.getBankProducts(token, newBankName.trim());
      // Bank already exists — go manage it instead of creating a duplicate.
      setBankProducts(products);
      setView({ name: "bank", bankName: newBankName.trim() });
    } catch {
      // Doesn't exist yet — go straight to the "add a product" form. This is
      // the expected, normal path for a genuinely new bank name, not a
      // failure. Reset bankProducts so the employment-type dropdown doesn't
      // accidentally inherit a stale, unrelated bank's product list.
      setBankProducts([]);
      setView({ name: "add-employment-type", bankName: newBankName.trim(), isNewBank: true });
    }
  }

  // Only meaningful once bankProducts reflects the bank currently in view —
  // true right after either the "bank" view's own fetch, or the "doesn't
  // exist yet" branch above which resets it to []. Used to keep the "add a
  // product" dropdown from offering an employment type that already exists.
  const missingTypes = EMPLOYMENT_TYPES.filter(
    (t) => !bankProducts?.some((p) => p.employment_type === t.value),
  );

  const errorBanner = error && (
    <div className="flex items-center justify-between gap-3 rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700 dark:border-red-900 dark:bg-red-950/40 dark:text-red-300">
      <span>{error}</span>
      <button onClick={() => setError(null)} className="font-semibold hover:underline">
        Dismiss
      </button>
    </div>
  );

  if (view.name === "list") {
    const filteredBanks = banks?.filter((bank) =>
      bank.bank_name.toLowerCase().includes(search.trim().toLowerCase()),
    );
    return (
      <div className="flex flex-col gap-4">
        {errorBanner}
        <div className="flex items-center justify-between">
          <h2 className="text-2xl font-semibold text-zinc-900 dark:text-zinc-50">Banks</h2>
          <button
            onClick={() => {
              setNewBankName("");
              setError(null);
              setView({ name: "add-new-bank" });
            }}
            className="rounded-lg bg-emerald-600 px-5 py-2.5 text-base font-semibold text-white hover:bg-emerald-700"
          >
            + Add new bank
          </button>
        </div>

        <div className="relative">
          <svg
            xmlns="http://www.w3.org/2000/svg"
            width="18"
            height="18"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
            className="pointer-events-none absolute left-3.5 top-1/2 -translate-y-1/2 text-zinc-400"
          >
            <circle cx="11" cy="11" r="8" />
            <path d="m21 21-4.3-4.3" />
          </svg>
          <input
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search banks by name…"
            className="w-full rounded-lg border border-zinc-300 py-2.5 pl-10 pr-3 text-base outline-none focus:border-emerald-500 dark:border-zinc-700 dark:bg-zinc-950"
          />
        </div>

        <div className="overflow-x-auto rounded-2xl border border-zinc-200 dark:border-zinc-800">
          <table className="w-full text-base">
            <thead className="bg-zinc-50 text-left text-sm uppercase tracking-wide text-zinc-500 dark:bg-zinc-900 dark:text-zinc-400">
              <tr>
                <th className="px-5 py-3.5">Bank name</th>
                <th className="px-5 py-3.5">Source</th>
                <th className="px-5 py-3.5">Employment types</th>
                <th className="px-5 py-3.5" />
              </tr>
            </thead>
            <tbody>
              {filteredBanks?.map((bank) => (
                <tr key={bank.bank_name} className="border-t border-zinc-100 dark:border-zinc-800">
                  <td className="px-5 py-3.5 font-medium text-zinc-900 dark:text-zinc-50">{bank.bank_name}</td>
                  <td className="px-5 py-3.5 text-zinc-500 dark:text-zinc-400">{bank.source}</td>
                  <td className="px-5 py-3.5 text-zinc-500 dark:text-zinc-400">
                    {bank.employment_types.join(", ") || "—"}
                  </td>
                  <td className="px-5 py-3.5 text-right">
                    <button
                      onClick={() => {
                        setError(null);
                        setView({ name: "bank", bankName: bank.bank_name });
                      }}
                      className="text-base font-medium text-emerald-600 hover:underline"
                    >
                      Manage
                    </button>
                  </td>
                </tr>
              ))}
              {filteredBanks?.length === 0 && (
                <tr>
                  <td colSpan={4} className="px-5 py-6 text-center text-zinc-400">
                    No banks match &ldquo;{search}&rdquo;.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    );
  }

  if (view.name === "add-new-bank") {
    return (
      <div className="flex flex-col gap-4">
        <button onClick={() => setView({ name: "list" })} className="w-fit text-sm text-zinc-500 hover:underline">
          ← Back to banks
        </button>
        <div className="flex flex-col gap-3 rounded-2xl border border-zinc-200 bg-white p-6 dark:border-zinc-800 dark:bg-zinc-900">
          <label className="text-sm font-medium text-zinc-700 dark:text-zinc-300">Bank name</label>
          <input
            value={newBankName}
            onChange={(e) => setNewBankName(e.target.value)}
            placeholder="e.g. SBI"
            className="rounded-lg border border-zinc-300 px-3 py-2 text-sm dark:border-zinc-700 dark:bg-zinc-950"
          />
          {error && <p className="text-sm text-red-600">{error}</p>}
          <button
            onClick={handleAddNewBankSubmit}
            className="w-fit rounded-lg bg-emerald-600 px-5 py-2 text-sm font-semibold text-white hover:bg-emerald-700"
          >
            Continue
          </button>
        </div>
      </div>
    );
  }

  if (view.name === "bank") {
    return (
      <div className="flex flex-col gap-4">
        <button onClick={() => setView({ name: "list" })} className="w-fit text-sm text-zinc-500 hover:underline">
          ← Back to banks
        </button>
        {errorBanner}
        <div className="flex items-center justify-between">
          <h3 className="text-base font-semibold text-zinc-900 dark:text-zinc-50">{view.bankName}</h3>
          <button
            onClick={() => handleDeleteBank(view.bankName)}
            className="text-sm font-medium text-red-600 hover:underline"
          >
            Delete this bank
          </button>
        </div>
        <div className="flex flex-col gap-3">
          {bankProducts?.map((product) => (
            <div
              key={product.employment_type}
              className="flex items-center justify-between rounded-xl border border-zinc-200 bg-white p-4 dark:border-zinc-800 dark:bg-zinc-900"
            >
              <div>
                <p className="text-sm font-semibold text-zinc-900 dark:text-zinc-50 capitalize">
                  {product.employment_type.replace("_", " ")}
                </p>
                <p className="text-xs text-zinc-500 dark:text-zinc-400">
                  CIBIL {product.min_cibil}-{product.max_cibil} · Rate {product.interest_rate_pct}%
                </p>
              </div>
              <div className="flex gap-3">
                <button
                  onClick={() => setView({ name: "edit", bankName: view.bankName, product })}
                  className="text-sm font-medium text-emerald-600 hover:underline"
                >
                  Edit
                </button>
                <button
                  onClick={() => handleDeleteProduct(view.bankName, product.employment_type)}
                  className="text-sm font-medium text-red-600 hover:underline"
                >
                  Remove
                </button>
              </div>
            </div>
          ))}
        </div>
        {missingTypes.length > 0 && (
          <button
            onClick={() => setView({ name: "add-employment-type", bankName: view.bankName, isNewBank: false })}
            className="w-fit rounded-lg border border-emerald-600 px-4 py-2 text-sm font-semibold text-emerald-600 hover:bg-emerald-50 dark:hover:bg-emerald-950/40"
          >
            + Add another employment type
          </button>
        )}
      </div>
    );
  }

  if (view.name === "add-employment-type") {
    // A genuinely new bank doesn't exist until the first product is
    // actually submitted — "Continue" only checked the name, it never
    // created anything — so there's no real "bank" screen to go back to
    // yet. Route back to the bank list instead of a lookup that will 404.
    const goBack = () =>
      setView(view.isNewBank ? { name: "list" } : { name: "bank", bankName: view.bankName });
    return (
      <div className="flex flex-col gap-4">
        <button onClick={goBack} className="w-fit text-sm text-zinc-500 hover:underline">
          ← Back
        </button>
        {errorBanner}
        <ProductForm
          submitLabel="Add product"
          employmentTypeOptions={missingTypes}
          onCancel={goBack}
          onSubmit={(detail) => handleCreate(view.bankName, detail)}
        />
      </div>
    );
  }

  if (view.name === "edit") {
    return (
      <div className="flex flex-col gap-4">
        <button
          onClick={() => setView({ name: "bank", bankName: view.bankName })}
          className="w-fit text-sm text-zinc-500 hover:underline"
        >
          ← Back to {view.bankName}
        </button>
        {errorBanner}
        <ProductForm
          initial={view.product}
          lockEmploymentType
          submitLabel="Save changes"
          onCancel={() => setView({ name: "bank", bankName: view.bankName })}
          onSubmit={(detail) => handleUpdate(view.bankName, view.product.employment_type, detail)}
        />
      </div>
    );
  }

  return null;
}
