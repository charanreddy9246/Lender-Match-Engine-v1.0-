"use client";

import { useEffect, useState } from "react";

import { errorMessage } from "@/lib/api/client";
import { adminApi, type AdminBiasOut } from "@/lib/api/admin";

export function BiasSection({ getToken }: { getToken: () => Promise<string | null> }) {
  const [items, setItems] = useState<AdminBiasOut[] | null>(null);
  const [editingBank, setEditingBank] = useState<string | null>(null);
  const [addingNew, setAddingNew] = useState(false);
  const [form, setForm] = useState({ bank_name: "", recent_borrowers_processed: 0, relationship_note: "" });
  const [error, setError] = useState<string | null>(null);
  const [listError, setListError] = useState<string | null>(null);

  async function refresh() {
    const token = await getToken();
    if (!token) return;
    setItems(await adminApi.listBias(token));
  }

  useEffect(() => {
    let cancelled = false;
    (async () => {
      const token = await getToken();
      if (!token || cancelled) return;
      try {
        const data = await adminApi.listBias(token);
        if (!cancelled) {
          setItems(data);
          setListError(null);
        }
      } catch (err) {
        if (!cancelled) setListError(errorMessage(err));
      }
    })();
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps -- getToken is stable across renders, run once on mount
  }, []);

  function startEdit(item: AdminBiasOut) {
    setEditingBank(item.bank_name);
    setAddingNew(false);
    setForm({ ...item });
    setError(null);
  }

  function startAdd() {
    setAddingNew(true);
    setEditingBank(null);
    setForm({ bank_name: "", recent_borrowers_processed: 0, relationship_note: "" });
    setError(null);
  }

  async function save() {
    if (!form.bank_name.trim()) {
      setError("Enter a bank name.");
      return;
    }
    setError(null);
    try {
      const token = await getToken();
      if (!token) return;
      await adminApi.upsertBias(token, form.bank_name.trim(), {
        recent_borrowers_processed: form.recent_borrowers_processed,
        relationship_note: form.relationship_note,
      });
      setEditingBank(null);
      setAddingNew(false);
      await refresh();
    } catch (err) {
      setError(errorMessage(err));
    }
  }

  async function remove(bankName: string) {
    if (!confirm(`Remove relationship data for ${bankName}? It goes back to having none at all.`)) return;
    setListError(null);
    try {
      const token = await getToken();
      if (!token) return;
      await adminApi.deleteBias(token, bankName);
      await refresh();
    } catch (err) {
      setListError(errorMessage(err));
    }
  }

  const isEditingOrAdding = editingBank !== null || addingNew;

  return (
    <div className="flex flex-col gap-4">
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold text-zinc-900 dark:text-zinc-50">Relationships</h2>
        {!isEditingOrAdding && (
          <button
            onClick={startAdd}
            className="rounded-lg bg-emerald-600 px-4 py-2 text-sm font-semibold text-white hover:bg-emerald-700"
          >
            + Add relationship data
          </button>
        )}
      </div>

      {isEditingOrAdding ? (
        <div className="flex flex-col gap-3 rounded-2xl border border-zinc-200 bg-white p-6 dark:border-zinc-800 dark:bg-zinc-900">
          <div className="flex flex-col gap-1.5">
            <label className="text-sm font-medium text-zinc-700 dark:text-zinc-300">Bank name</label>
            <input
              disabled={editingBank !== null}
              value={form.bank_name}
              onChange={(e) => setForm({ ...form, bank_name: e.target.value })}
              className="rounded-lg border border-zinc-300 px-3 py-2 text-sm disabled:bg-zinc-100 dark:border-zinc-700 dark:bg-zinc-950 dark:disabled:bg-zinc-800"
            />
          </div>
          <div className="flex flex-col gap-1.5">
            <label className="text-sm font-medium text-zinc-700 dark:text-zinc-300">
              Borrowers placed recently (higher = ranked higher, always above banks with none)
            </label>
            <input
              type="number"
              min={0}
              value={form.recent_borrowers_processed}
              onChange={(e) => setForm({ ...form, recent_borrowers_processed: Number(e.target.value) })}
              className="rounded-lg border border-zinc-300 px-3 py-2 text-sm dark:border-zinc-700 dark:bg-zinc-950"
            />
          </div>
          <div className="flex flex-col gap-1.5">
            <label className="text-sm font-medium text-zinc-700 dark:text-zinc-300">Note (shown to borrowers)</label>
            <input
              value={form.relationship_note}
              onChange={(e) => setForm({ ...form, relationship_note: e.target.value })}
              className="rounded-lg border border-zinc-300 px-3 py-2 text-sm dark:border-zinc-700 dark:bg-zinc-950"
            />
          </div>
          {error && <p className="text-sm text-red-600">{error}</p>}
          <div className="flex gap-3">
            <button
              onClick={save}
              className="rounded-lg bg-emerald-600 px-5 py-2 text-sm font-semibold text-white hover:bg-emerald-700"
            >
              Save
            </button>
            <button
              onClick={() => {
                setEditingBank(null);
                setAddingNew(false);
              }}
              className="rounded-lg border border-zinc-300 px-5 py-2 text-sm font-semibold text-zinc-700 dark:border-zinc-700 dark:text-zinc-200"
            >
              Cancel
            </button>
          </div>
        </div>
      ) : (
        <>
          {listError && (
            <div className="flex items-center justify-between gap-3 rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700 dark:border-red-900 dark:bg-red-950/40 dark:text-red-300">
              <span>{listError}</span>
              <button onClick={() => setListError(null)} className="font-semibold hover:underline">
                Dismiss
              </button>
            </div>
          )}
        <div className="overflow-x-auto rounded-2xl border border-zinc-200 dark:border-zinc-800">
          <table className="w-full text-base">
            <thead className="bg-zinc-50 text-left text-sm uppercase tracking-wide text-zinc-500 dark:bg-zinc-900 dark:text-zinc-400">
              <tr>
                <th className="px-5 py-3.5">Bank name</th>
                <th className="px-5 py-3.5">Borrowers placed recently</th>
                <th className="px-5 py-3.5">Note</th>
                <th className="px-5 py-3.5" />
              </tr>
            </thead>
            <tbody>
              {items?.map((item) => (
                <tr key={item.bank_name} className="border-t border-zinc-100 dark:border-zinc-800">
                  <td className="px-5 py-3.5 font-medium text-zinc-900 dark:text-zinc-50">{item.bank_name}</td>
                  <td className="px-5 py-3.5 text-zinc-500 dark:text-zinc-400">{item.recent_borrowers_processed}</td>
                  <td className="px-5 py-3.5 text-zinc-500 dark:text-zinc-400">{item.relationship_note}</td>
                  <td className="px-5 py-3.5 text-right">
                    <div className="flex justify-end gap-3">
                      <button onClick={() => startEdit(item)} className="text-base font-medium text-emerald-600 hover:underline">
                        Edit
                      </button>
                      <button onClick={() => remove(item.bank_name)} className="text-base font-medium text-red-600 hover:underline">
                        Remove
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
              {items?.length === 0 && (
                <tr>
                  <td colSpan={4} className="px-5 py-6 text-center text-zinc-400">
                    No relationship data yet.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
        </>
      )}
    </div>
  );
}
