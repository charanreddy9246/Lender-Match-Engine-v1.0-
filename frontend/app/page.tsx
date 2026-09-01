import type { Metadata } from "next";
import Link from "next/link";

import { LenderFinderForm } from "@/features/lender-finder/LenderFinderForm";

export const metadata: Metadata = {
  title: "Find the Best Home Loan Lender for You",
  description: "Matches your profile with lenders that can fund you, at your fair rate, in seconds.",
};

export default function Home() {
  return (
    <div className="relative flex flex-1 flex-col items-center bg-zinc-50 px-4 py-16 dark:bg-zinc-950 sm:px-6">
      <Link
        href="/admin"
        aria-label="Admin"
        className="absolute right-4 top-4 rounded-full p-2 text-zinc-400 hover:bg-zinc-200 hover:text-zinc-600 dark:hover:bg-zinc-800 dark:hover:text-zinc-300"
      >
        <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <rect x="3" y="11" width="18" height="11" rx="2" />
          <path d="M7 11V7a5 5 0 0 1 10 0v4" />
        </svg>
      </Link>
      <div className="flex w-full max-w-4xl flex-col items-center gap-2 text-center">
        <h1 className="text-3xl font-bold tracking-tight text-zinc-900 dark:text-zinc-50 sm:text-4xl">
          Find the Best Home Loan Lender for You
        </h1>
        <p className="max-w-xl text-base text-zinc-600 dark:text-zinc-400">
          We match your profile with lenders that can fund you, at your fair rate, in seconds.
        </p>
      </div>

      <div className="mt-10 w-full">
        <LenderFinderForm />
      </div>
    </div>
  );
}
