"use client";

export function EmptyState() {
  return (
    <div className="flex h-full flex-col items-center justify-center gap-7 overflow-hidden rounded-2xl border border-zinc-200 bg-gradient-to-b from-teal-50 via-white to-white px-8 py-16 text-center shadow-sm dark:border-zinc-800 dark:from-teal-950/30 dark:via-zinc-900 dark:to-zinc-900">
      <div className="relative flex h-24 w-24 items-center justify-center">
        <span className="absolute inset-0 animate-pulse rounded-full bg-teal-500/25 blur-xl" />
        <div className="relative flex h-20 w-20 items-center justify-center rounded-full bg-gradient-to-br from-teal-400 to-teal-600 shadow-lg shadow-teal-600/40 ring-4 ring-white dark:ring-zinc-900">
          <svg
            xmlns="http://www.w3.org/2000/svg"
            width="38"
            height="38"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2.5"
            strokeLinecap="round"
            strokeLinejoin="round"
            className="text-white"
          >
            <path d="M3 10.5 12 3l9 7.5" />
            <path d="M5 9.5V21h14V9.5" />
            <path d="M9 21v-6h6v6" />
          </svg>
        </div>
      </div>

      <h2 className="max-w-lg text-4xl font-black leading-[1.05] tracking-tight text-zinc-900 sm:text-5xl dark:text-zinc-50">
        Pick a filter.
        <br />
        Meet your <span className="italic text-teal-600 dark:text-teal-400">match.</span>
      </h2>

      <p className="max-w-sm text-base font-medium italic text-zinc-500 dark:text-zinc-400">
        &ldquo;The right lender isn&apos;t a guess — it&apos;s a match waiting to be found.&rdquo;
      </p>
    </div>
  );
}
