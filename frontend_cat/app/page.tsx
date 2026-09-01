import type { Metadata } from "next";
import Link from "next/link";

import { ExplorePage } from "@/features/explore/ExplorePage";

export const metadata: Metadata = {
  title: "Explore Lenders",
  description: "Browse the loaded bank data by employment type and property filters.",
};

export default function Home() {
  return (
    // Fixed to the viewport height on purpose — ExplorePage splits into two
    // independently scrolling panes below the header, so scrolling the
    // results never moves the filter sidebar and vice versa.
    <div className="flex h-screen flex-col overflow-hidden bg-zinc-50 dark:bg-zinc-950">
      <header className="flex shrink-0 items-center justify-between border-b border-teal-900 bg-zinc-900 px-6 py-4">
        <div>
          <div className="flex flex-wrap items-center gap-2">
            <h1 className="text-xl font-bold tracking-tight text-white">
              Explore <span className="text-teal-400">Lenders</span>
            </h1>
            <span className="rounded-full border border-teal-800 bg-teal-950/60 px-2 py-0.5 text-[10px] font-bold uppercase tracking-wide text-teal-400">
              Lender Match Engine v1.0
            </span>
          </div>
          <p className="text-xs text-zinc-400">
            Browse the loaded bank data by employment type and property filters.
          </p>
        </div>
        <Link
          href="/admin"
          aria-label="Admin"
          className="rounded-full p-2 text-zinc-400 hover:bg-zinc-800 hover:text-teal-400"
        >
          <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <rect x="3" y="11" width="18" height="11" rx="2" />
            <path d="M7 11V7a5 5 0 0 1 10 0v4" />
          </svg>
        </Link>
      </header>

      <div className="min-h-0 flex-1">
        <ExplorePage />
      </div>
    </div>
  );
}
