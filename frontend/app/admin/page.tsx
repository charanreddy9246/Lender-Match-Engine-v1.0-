"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { BanksSection } from "@/features/admin/BanksSection";
import { BiasSection } from "@/features/admin/BiasSection";
import { useAuth } from "@/lib/useAuth";

export default function AdminDashboardPage() {
  const { user, loading, logout, getToken } = useAuth();
  const router = useRouter();
  const [tab, setTab] = useState<"banks" | "bias">("banks");

  useEffect(() => {
    if (!loading && !user) router.push("/admin/login");
  }, [loading, user, router]);

  if (loading || !user) {
    return <div className="flex flex-1 items-center justify-center text-sm text-zinc-500">Checking login…</div>;
  }

  return (
    <div className="flex flex-1 flex-col bg-zinc-50 px-4 py-10 dark:bg-zinc-950 sm:px-8">
      <div className="mx-auto flex w-full max-w-7xl flex-col gap-6">
        <div className="flex items-center justify-between">
          <div>
            <Link
              href="/"
              className="text-sm font-medium text-zinc-500 hover:text-zinc-700 dark:text-zinc-400 dark:hover:text-zinc-200"
            >
              ← Back to the lender finder
            </Link>
            <h1 className="mt-1 text-xl font-bold text-zinc-900 dark:text-zinc-50">Admin</h1>
            <p className="text-sm text-zinc-500 dark:text-zinc-400">Logged in as {user.email}</p>
          </div>
          <button
            onClick={async () => {
              await logout();
              router.push("/admin/login");
            }}
            className="rounded-lg border border-zinc-300 px-4 py-2 text-sm font-medium text-zinc-700 dark:border-zinc-700 dark:text-zinc-200"
          >
            Log out
          </button>
        </div>

        <div className="flex gap-2 border-b border-zinc-200 dark:border-zinc-800">
          <button
            onClick={() => setTab("banks")}
            className={`px-4 py-2 text-sm font-medium ${
              tab === "banks" ? "border-b-2 border-emerald-600 text-emerald-600" : "text-zinc-500"
            }`}
          >
            Banks
          </button>
          <button
            onClick={() => setTab("bias")}
            className={`px-4 py-2 text-sm font-medium ${
              tab === "bias" ? "border-b-2 border-emerald-600 text-emerald-600" : "text-zinc-500"
            }`}
          >
            Relationships
          </button>
        </div>

        {tab === "banks" ? <BanksSection getToken={getToken} /> : <BiasSection getToken={getToken} />}
      </div>
    </div>
  );
}
