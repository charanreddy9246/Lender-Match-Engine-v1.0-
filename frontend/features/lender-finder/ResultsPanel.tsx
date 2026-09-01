import type { MatchResponse } from "@/lib/api/types";

const TIER_LABEL: Record<string, string> = {
  high: "High approval likelihood",
  medium: "Medium approval likelihood",
  low: "Low approval likelihood",
};

export function ResultsPanel({ results }: { results: MatchResponse }) {
  if (results.lenders.length === 0) {
    return (
      <div className="rounded-2xl border border-zinc-200 bg-white p-6 text-center shadow-sm dark:border-zinc-800 dark:bg-zinc-900">
        <p className="text-sm text-zinc-600 dark:text-zinc-400">
          No lenders matched your profile out of {results.meta.products_considered} considered. Try adjusting your CIBIL
          score, documents, or loan amount.
        </p>
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-4">
      <h2 className="text-lg font-semibold text-zinc-900 dark:text-zinc-50">Your top {results.lenders.length} lenders</h2>
      <div className="grid gap-4 sm:grid-cols-3">
        {results.lenders.map((lender, index) => (
          <div
            key={`${lender.bank_name}-${lender.product_name}`}
            className="flex flex-col gap-2 rounded-2xl border border-zinc-200 bg-white p-5 shadow-sm dark:border-zinc-800 dark:bg-zinc-900"
          >
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold uppercase tracking-wide text-emerald-600">#{index + 1} match</span>
              {lender.lender_type && (
                <span className="rounded-full bg-zinc-100 px-2 py-0.5 text-[10px] font-medium text-zinc-600 dark:bg-zinc-800 dark:text-zinc-300">
                  {lender.lender_type}
                </span>
              )}
            </div>
            <h3 className="text-base font-semibold text-zinc-900 dark:text-zinc-50">{lender.bank_name}</h3>
            <p className="text-sm text-zinc-500 dark:text-zinc-400">{lender.product_name}</p>

            {lender.interest_rate_pct !== null ? (
              <p className="text-2xl font-bold text-zinc-900 dark:text-zinc-50">
                {lender.interest_rate_pct}%<span className="text-sm font-normal text-zinc-400"> p.a.</span>
              </p>
            ) : (
              <p className="text-sm text-zinc-400">Rate not available yet</p>
            )}
            {lender.interest_rate_range && (
              <p className="text-xs text-zinc-500 dark:text-zinc-400">Range: {lender.interest_rate_range}</p>
            )}
            {lender.processing_fee && (
              <p className="text-xs text-zinc-500 dark:text-zinc-400">Processing fee: {lender.processing_fee}</p>
            )}
            {lender.max_eligible_amount !== null && (
              <p className="text-xs text-zinc-500 dark:text-zinc-400">
                Eligible up to ₹{lender.max_eligible_amount.toLocaleString("en-IN")}
              </p>
            )}
            {lender.approval_likelihood_tier && (
              <p className="text-xs text-zinc-500 dark:text-zinc-400">{TIER_LABEL[lender.approval_likelihood_tier]}</p>
            )}
            {lender.recent_borrowers_processed !== null && (
              <div className="mt-1 flex flex-col gap-1 rounded-lg bg-emerald-50 px-3 py-2 dark:bg-emerald-950/40">
                <span className="text-xs font-medium text-emerald-700 dark:text-emerald-400">
                  🤝 {lender.recent_borrowers_processed} of our borrower{lender.recent_borrowers_processed === 1 ? "" : "s"} placed recently
                </span>
                {lender.relationship_note && (
                  <span className="text-xs text-emerald-600/80 dark:text-emerald-400/70">{lender.relationship_note}</span>
                )}
              </div>
            )}
            <ul className="mt-1 flex flex-col gap-0.5 text-xs text-zinc-400">
              {lender.reasons
                .filter((reason) => reason !== lender.relationship_note && !reason.startsWith("processed "))
                .map((reason) => (
                  <li key={reason}>&bull; {reason}</li>
                ))}
            </ul>
          </div>
        ))}
      </div>
    </div>
  );
}
